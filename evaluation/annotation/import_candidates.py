"""Explicit approved-candidate import. Dry-run by default; no annotation creation."""
import argparse
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import uuid

from evaluation.annotation.candidate_review import (
    DEFAULT_REVIEWS, _write_new, approval_report, candidate_checksum,
    file_checksum, load_candidates, validate_candidate_mapping, verify_reviews,
    review_write_lock, _validate_review,
)
from evaluation.annotation.validate_pilot import DEFAULT_PILOT, _load_json, _validate_schema, validate_pilot


def _pilot_state(pilot_dir):
    pilot_dir = Path(pilot_dir)
    if pilot_dir.is_symlink():
        raise ValueError("Pilot folder must not be a symlink")
    for name in ("manifest.json", "claim_records.json"):
        if (pilot_dir / name).is_symlink():
            raise ValueError("Pilot input must not be a symlink")
    manifest = _load_json(pilot_dir / "manifest.json")
    _validate_schema(manifest, "pilot_manifest.schema.json", "pilot manifest")
    fixed_inputs = list(manifest["annotator_submission_files"].values()) + [manifest["adjudications_file"]]
    for relative in fixed_inputs:
        path = pilot_dir / relative
        # Reject links in any path component before invoking the existing validator.
        for component in [path] + list(path.parents):
            if component == pilot_dir:
                break
            if component.is_symlink():
                raise ValueError("Pilot input must not be a symlink")
    for relative in ("submissions/integrity", "submissions/snapshots"):
        path = pilot_dir / relative
        if path.is_symlink() or (path.exists() and any(item.is_symlink() for item in path.rglob("*"))):
            raise ValueError("Pilot submission history must not contain symlinks")
    rows = _load_json(pilot_dir / "claim_records.json")
    validate_pilot(pilot_dir)
    issues = []
    if manifest["status"] == "ready":
        issues.append("Pilot is ready/frozen; imports are closed")
    if any(row["annotation_status"] != "unannotated" or row["split"] != "pilot" for row in rows):
        issues.append("Pilot contains annotation work or non-pilot records")
    paths = list(manifest["annotator_submission_files"].values()) + [manifest["adjudications_file"]]
    for relative in paths:
        path = pilot_dir / relative
        if path.is_symlink() or _load_json(path):
            issues.append("Pilot contains annotator submissions/adjudications or redirected files")
    for relative in ("submissions/integrity", "submissions/snapshots"):
        path = pilot_dir / relative
        if path.is_symlink() or (path.exists() and any(item.is_file() for item in path.rglob("*"))):
            issues.append("Pilot has sealed or incomplete submission snapshots")
    imports = pilot_dir / "imports"
    if imports.is_symlink():
        issues.append("Import history folder must not be a symlink")
    elif imports.exists():
        completed = []
        for transaction in sorted(imports.iterdir()):
            if transaction.is_symlink():
                raise ValueError("Import transaction must not be a symlink")
            if not transaction.is_dir() or not (transaction / "receipt.json").is_file():
                issues.append("An incomplete import transaction requires manual recovery")
                continue
            if (transaction / "receipt.json").is_symlink():
                raise ValueError("Import receipt must not be a symlink")
            receipt = _load_json(transaction / "receipt.json")
            preserved_names = {"before_claim_records.json", "before_manifest.json", "plan.json"}
            if (not isinstance(receipt, dict) or receipt.get("transaction_id") != transaction.name
                    or not isinstance(receipt.get("preserved_files_sha256"), dict)
                    or set(receipt["preserved_files_sha256"]) != preserved_names):
                raise ValueError("Invalid import receipt structure")
            digests = list(receipt["preserved_files_sha256"].values()) + [
                receipt.get("after_claim_records_sha256"), receipt.get("after_manifest_sha256")]
            if any(not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value) for value in digests):
                raise ValueError("Invalid import receipt checksums")
            for name, expected in receipt.get("preserved_files_sha256", {}).items():
                if name not in {"before_claim_records.json", "before_manifest.json", "plan.json"}:
                    raise ValueError("Unexpected import history reference")
                if (transaction / name).is_symlink() or file_checksum(transaction / name) != expected:
                    issues.append("Import history checksum mismatch")
            if completed:
                previous = completed[-1]
                if (file_checksum(transaction / "before_claim_records.json") != previous["after_claim_records_sha256"]
                        or file_checksum(transaction / "before_manifest.json") != previous["after_manifest_sha256"]):
                    issues.append("Import history chain is inconsistent")
            completed.append(receipt)
        if completed and (file_checksum(pilot_dir / "claim_records.json") != completed[-1]["after_claim_records_sha256"]
                          or file_checksum(pilot_dir / "manifest.json") != completed[-1]["after_manifest_sha256"]):
            issues.append("Current pilot checksum differs from latest completed import")
    ids, evidence_ids = set(), set()
    for row in rows:
        if row["claim_id"] in ids:
            raise ValueError("Duplicate claim IDs already exist in pilot")
        ids.add(row["claim_id"])
        for evidence in row["evidence"]:
            if evidence["evidence_id"] in evidence_ids:
                raise ValueError("Duplicate evidence IDs already exist in pilot")
            evidence_ids.add(evidence["evidence_id"])
    return manifest, rows, ids, evidence_ids, issues


def import_candidates(candidates, review_root, pilot_dir, candidate_ids=None, *, apply=False):
    """Plan an all-or-nothing append; apply requires current human approvals."""
    candidates = deepcopy(candidates)
    validate_candidate_mapping(candidates)
    selected = list(candidates) if candidate_ids is None else list(candidate_ids)
    if len(set(selected)) != len(selected):
        raise ValueError("Duplicate candidate IDs requested")
    if any(candidate_id not in candidates for candidate_id in selected):
        raise ValueError("Unknown candidate ID requested")
    manifest, existing, existing_ids, existing_evidence, pilot_issues = _pilot_state(pilot_dir)
    report = approval_report(candidates, review_root)
    by_id = {row["candidate_id"]: row for row in report["candidates"]}
    blocked, eligible = {}, []
    for candidate_id in selected:
        reasons = list(by_id[candidate_id]["blocked_reasons"]) + list(pilot_issues)
        if not set(candidates[candidate_id]["claim_category"]).issubset(manifest["challenge_categories"]):
            reasons.append("Candidate challenge tags are outside the pilot sampling plan")
        if candidate_id in existing_ids:
            reasons.append("Claim ID already exists in pilot; no overwrite permitted")
        if any(item["evidence_id"] in existing_evidence for item in candidates[candidate_id]["evidence"]):
            reasons.append("Evidence ID already exists in pilot")
        if reasons:
            blocked[candidate_id] = reasons
        else:
            eligible.append(candidate_id)
    if len(existing) + len(selected) > manifest["target_claim_count"]:
        for candidate_id in selected:
            blocked.setdefault(candidate_id, []).append("Import would exceed pilot capacity of 90 claims")
        eligible = []
    result = {"dry_run": not apply, "eligible_candidate_ids": eligible, "blocked": blocked,
              "applied": False, "existing_claim_count": len(existing),
              "requested_candidate_ids": selected, "imported_candidate_ids": [],
              "note": "All requested candidates must be eligible; no labels or adjudications are created."}
    if not apply or blocked or not selected:
        return result

    pilot_dir = Path(pilot_dir)
    lock = pilot_dir / ".candidate_import.lock"
    try:
        descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError("Another import or stale import lock requires coordinator review") from error
    os.close(descriptor)
    transaction = None
    guards = ExitStack()
    try:
        guards.enter_context(review_write_lock(review_root))
        # Recheck after locking; another cooperating importer may have finished.
        current = import_candidates(candidates, review_root, pilot_dir, selected, apply=False)
        if current["blocked"]:
            return {**current, "dry_run": False}
        manifest, existing, _, _, issues = _pilot_state(pilot_dir)
        if issues:
            raise ValueError("Pilot state changed during import")
        before_claims = (pilot_dir / "claim_records.json").read_bytes()
        before_manifest = (pilot_dir / "manifest.json").read_bytes()
        latest = verify_reviews(review_root)
        for key in selected:
            _validate_review(latest[key]["review"], candidates[key])
            if latest[key]["review"]["decision"] != "approved":
                raise ValueError("Latest decision changed; current human approval is required")
        combined = existing + [deepcopy(candidates[key]) for key in selected]
        next_manifest = deepcopy(manifest)
        next_manifest["status"] = "collecting"
        transaction_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:12]
        transaction = pilot_dir / "imports" / transaction_id
        transaction.mkdir(parents=True)
        for name, raw in (("before_claim_records.json", before_claims), ("before_manifest.json", before_manifest)):
            with (transaction / name).open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            (transaction / name).chmod(0o444)
        plan = {"transaction_id": transaction_id, "candidate_ids": selected,
                "candidate_sha256": {key: candidate_checksum(candidates[key]) for key in selected},
                "review_references": {key: {
                    "review_id": latest[key]["review"]["review_id"],
                    "integrity_sha256": latest[key]["integrity_sha256"]} for key in selected}}
        _write_new(transaction / "plan.json", plan, readonly=True)
        _write_new(transaction / "next_claim_records.json", combined)
        _write_new(transaction / "next_manifest.json", next_manifest)
        if ((pilot_dir / "claim_records.json").read_bytes() != before_claims
                or (pilot_dir / "manifest.json").read_bytes() != before_manifest):
            raise ValueError("Pilot changed outside the import lock; import aborted")
        # A final review verification prevents a changed decision from being ignored.
        final_reviews = verify_reviews(review_root)
        if any(final_reviews[key]["integrity_sha256"] != latest[key]["integrity_sha256"] for key in selected):
            raise ValueError("Human review changed during import; rerun dry-run")
        for key in selected:
            _validate_review(final_reviews[key]["review"], candidates[key])
            if final_reviews[key]["review"]["decision"] != "approved":
                raise ValueError("Latest decision is not approval")
        os.replace(str(transaction / "next_claim_records.json"), str(pilot_dir / "claim_records.json"))
        os.replace(str(transaction / "next_manifest.json"), str(pilot_dir / "manifest.json"))
        validate_pilot(pilot_dir)
        receipt = {**plan, "completed_at": datetime.now(timezone.utc).isoformat(),
                   "before_claim_count": len(existing), "after_claim_count": len(combined),
                   "after_claim_records_sha256": file_checksum(pilot_dir / "claim_records.json"),
                   "after_manifest_sha256": file_checksum(pilot_dir / "manifest.json"),
                   "preserved_files_sha256": {name: file_checksum(transaction / name) for name in
                       ("before_claim_records.json", "before_manifest.json", "plan.json")}}
        _write_new(transaction / "receipt.json", receipt, readonly=True)
        result.update(applied=True, imported_candidate_ids=selected,
                      receipt=str(transaction / "receipt.json"))
        return result
    except Exception as error:
        location = str(transaction) if transaction else "no transaction written"
        raise RuntimeError("Import did not complete cleanly; preserved transaction requires review: " + location) from error
    finally:
        try:
            guards.close()
        finally:
            lock.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", action="append", type=Path)
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument("--pilot-directory", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--candidate", action="append", help="Explicit candidate IDs; default checks all candidates")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Explicitly append eligible candidates; default writes no pilot files")
    mode.add_argument("--dry-run", action="store_false", dest="apply", help="Plan only; never write pilot files (default)")
    parser.set_defaults(apply=False)
    args = parser.parse_args(argv)
    try:
        result = import_candidates(load_candidates(args.collection), args.review_root,
                                   args.pilot_directory, args.candidate, apply=args.apply)
        print(json.dumps(result, indent=2))
        return 1 if result["blocked"] else 0
    except (ValueError, OSError, RuntimeError) as error:
        parser.exit(1, "Import blocked: {0}\n".format(error))


if __name__ == "__main__":
    raise SystemExit(main())
