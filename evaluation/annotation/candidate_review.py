"""Version-bound human inclusion reviews, separate from annotation gold labels."""
import argparse
from collections import Counter
from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

from evaluation.annotation.quality_control import _valid_date, _valid_https_url
from evaluation.annotation.validate_pilot import ROOT, _load_json, _validate_schema


DEFAULT_COLLECTIONS = [ROOT / "candidates" / "phase1_15", ROOT / "candidates" / "phase2_15"]
DEFAULT_REVIEWS = ROOT / "candidate_reviews"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def candidate_checksum(record):
    """Hash the full claim/evidence record; key order/whitespace are immaterial."""
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def file_checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_new(path, value, *, readonly=False):
    payload = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    with Path(path).open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    if readonly:
        Path(path).chmod(0o444)  # Advisory; hashes are not signatures or access control.


@contextmanager
def review_write_lock(review_root):
    """Coordinate review sealing and import; a crash leaves an explicit stale lock."""
    root = Path(review_root)
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".review_submission.lock"
    try:
        descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError("Review submission/import lock exists; coordinator review required") from error
    os.close(descriptor)
    try:
        yield
    finally:
        lock.unlink()


def validate_candidate_mapping(candidates):
    seen_evidence = set()
    for candidate_id, record in candidates.items():
        _validate_schema(record, "claim_record.schema.json", "candidate " + str(candidate_id))
        if candidate_id != record["claim_id"]:
            raise ValueError("Candidate mapping key does not match claim_id")
        for evidence in record["evidence"]:
            if evidence["evidence_id"] in seen_evidence:
                raise ValueError("Duplicate evidence IDs across candidates")
            seen_evidence.add(evidence["evidence_id"])


def load_candidates(collections=None):
    candidates = {}
    for directory in DEFAULT_COLLECTIONS if collections is None else collections:
        rows = _load_json(Path(directory) / "claim_records.json")
        if not isinstance(rows, list):
            raise ValueError("Candidate records must be an array")
        for record in rows:
            _validate_schema(record, "claim_record.schema.json", "candidate record")
            if record["claim_id"] in candidates:
                raise ValueError("Duplicate candidate IDs across collections")
            candidates[record["claim_id"]] = record
    validate_candidate_mapping(candidates)
    return candidates


def candidate_issues(record):
    """Structural import blockers, not an evidence sufficiency or truth policy."""
    _validate_schema(record, "claim_record.schema.json", "candidate")
    issues = []
    if record["split"] != "pilot" or record["annotation_status"] != "unannotated":
        issues.append("Candidate must be an unannotated pilot record")
    if not record["claim_text"].strip():
        issues.append("Claim text is empty")
    if not record["claim_category"]:
        issues.append("Candidate is missing challenge tags")
    if not record["evidence"]:
        issues.append("Candidate is missing evidence")
    for evidence in record["evidence"]:
        prefix = evidence["evidence_id"] + ": "
        if not evidence["passage"].strip():
            issues.append(prefix + "evidence passage is empty")
        identifier = evidence["source_identifier"]
        if identifier is not None and (not identifier.strip() or any(char.isspace() for char in identifier)):
            issues.append(prefix + "invalid source identifier")
        if not (identifier and identifier.strip()) and not evidence["source_url"]:
            issues.append(prefix + "source is not traceable")
        if evidence["source_url"] is not None and not _valid_https_url(evidence["source_url"]):
            issues.append(prefix + "source URL is invalid")
        for field in ("publication_date", "event_date", "checked_on"):
            value = evidence[field]
            if value is not None and not _valid_date(value):
                issues.append(prefix + "invalid " + field)
        group = evidence["provenance_group_id"]
        if group is not None and not _ID.fullmatch(group):
            issues.append(prefix + "invalid provenance group")
    return issues


def _approval_conditions(review, candidate):
    reasons = candidate_issues(candidate)
    if review["source_verification_status"] != "verified":
        reasons.append("Source verification is incomplete")
    if review["claim_scope_assessment"]["status"] != "clear":
        reasons.append("Claim clarity/scope requires revision")
    if review["evidence_context_assessment"]["status"] != "adequate":
        reasons.append("Evidence context requires revision")
    evidence_by_id = {item["evidence_id"]: item for item in candidate["evidence"]}
    for assessment in review["evidence_reviews"]:
        evidence = evidence_by_id[assessment["evidence_id"]]
        prefix = evidence["evidence_id"] + ": "
        if assessment["source_status"] != "verified":
            reasons.append(prefix + "source not verified")
        status = assessment["publication_date_status"]
        if status == "conflicting_date_metadata":
            reasons.append(prefix + "conflicting date metadata requires resolution")
        elif status == "verified_publication_date":
            if (not _valid_date(assessment["verified_publication_date"])
                    or assessment["verified_publication_date"] != evidence["publication_date"]):
                reasons.append(prefix + "verified publication date differs from candidate; revise the candidate")
        elif evidence["publication_date"] is not None or assessment["verified_publication_date"] is not None:
            reasons.append(prefix + "undated/unknown status must agree with null candidate publication date")
        if assessment["provenance_assessment"] == "conflicting":
            reasons.append(prefix + "conflicting provenance requires resolution")
    return reasons


def _validate_review(review, candidate):
    _validate_schema(review, "candidate_review.schema.json", "human review")
    if review["candidate_id"] != candidate["claim_id"] or review["candidate_sha256"] != candidate_checksum(candidate):
        raise ValueError("Review candidate checksum is stale or candidate ID does not match")
    expected = {item["evidence_id"] for item in candidate["evidence"]}
    actual = [item["evidence_id"] for item in review["evidence_reviews"]]
    if len(set(actual)) != len(actual) or set(actual) != expected:
        raise ValueError("Review evidence IDs must cover the exact candidate evidence set once")
    if review["decision"] == "approved":
        issues = _approval_conditions(review, candidate)
        if issues:
            raise ValueError("Approval has unresolved blockers: " + "; ".join(issues))


def verify_reviews(review_root=DEFAULT_REVIEWS):
    """Verify all preserved snapshots and require one explicit linear chain per candidate."""
    root = Path(review_root) / "submitted"
    stored = {}
    if not root.exists():
        return {}
    for folder in sorted(root.iterdir()):
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError("Unexpected item in submitted reviews")
        paths = [folder / name for name in ("review.json", "candidate.json", "integrity.json")]
        if any(path.is_symlink() or not path.is_file() for path in paths):
            raise ValueError("Incomplete review snapshot: " + folder.name)
        review, candidate, integrity = map(_load_json, paths)
        _validate_schema(review, "candidate_review.schema.json", "human review snapshot")
        _validate_schema(integrity, "candidate_review_integrity.schema.json", "review integrity")
        _validate_schema(candidate, "claim_record.schema.json", "reviewed candidate snapshot")
        if folder.name != review["review_id"] or integrity["review_id"] != folder.name:
            raise ValueError("Review ID does not match snapshot folder")
        if (file_checksum(paths[0]) != integrity["review_file_sha256"]
                or file_checksum(paths[1]) != integrity["snapshot_file_sha256"]):
            raise ValueError("Review snapshot checksum mismatch: " + folder.name)
        _validate_review(review, candidate)
        if (integrity["candidate_sha256"] != candidate_checksum(candidate)
                or integrity["candidate_id"] != candidate["claim_id"]):
            raise ValueError("Review integrity candidate checksum/ID mismatch")
        stored[folder.name] = {"review": review, "candidate": candidate, "integrity": integrity,
                               "integrity_sha256": file_checksum(paths[2])}
    children, by_candidate = {}, {}
    for review_id, item in stored.items():
        record = item["review"]
        by_candidate.setdefault(record["candidate_id"], set()).add(review_id)
        previous = record["supersedes"]
        if previous is not None:
            if (previous not in stored or previous == review_id
                    or stored[previous]["review"]["candidate_id"] != record["candidate_id"]):
                raise ValueError("Invalid supersedes reference in review chain")
            if previous in children:
                raise ValueError("Conflicting review revision branches")
            children[previous] = review_id
    latest = {}
    for candidate_id, ids in by_candidate.items():
        roots = [key for key in ids if stored[key]["review"]["supersedes"] is None]
        if len(roots) != 1:
            raise ValueError("Ambiguous review history for " + candidate_id)
        visited, current = set(), roots[0]
        while True:
            if current in visited:
                raise ValueError("Cyclic review history")
            visited.add(current)
            if current not in children:
                break
            current = children[current]
        if visited != ids:
            raise ValueError("Disconnected review revision history")
        latest[candidate_id] = stored[current]
    return latest


def submit_review(review, candidates, review_root=DEFAULT_REVIEWS):
    """Seal a human-authored review; never infer a decision or replace an old review."""
    validate_candidate_mapping(candidates)
    review = deepcopy(review)
    _validate_schema(review, "candidate_review.schema.json", "human review")
    candidate_id = review["candidate_id"]
    if candidate_id not in candidates:
        raise ValueError("Unknown candidate ID")
    candidate = deepcopy(candidates[candidate_id])
    _validate_review(review, candidate)
    with review_write_lock(review_root):
        return _seal_review(review, candidate, review_root)


def _seal_review(review, candidate, review_root):
    candidate_id = review["candidate_id"]
    latest = verify_reviews(review_root)
    previous = latest.get(candidate_id, {}).get("review", {}).get("review_id")
    if review["supersedes"] != previous:
        raise ValueError("Review must explicitly supersede the latest review ID")
    folder = Path(review_root) / "submitted" / review["review_id"]
    folder.parent.mkdir(parents=True, exist_ok=True)
    try:
        folder.mkdir()  # Exclusive creation; an ID can never be silently reused.
    except FileExistsError as error:
        raise ValueError("Review ID already exists; no overwrite permitted") from error
    _write_new(folder / "candidate.json", candidate, readonly=True)
    _write_new(folder / "review.json", review, readonly=True)
    integrity = {
        "schema_version": "1.0.0", "review_id": review["review_id"], "candidate_id": candidate_id,
        "candidate_sha256": candidate_checksum(candidate),
        "review_file_sha256": file_checksum(folder / "review.json"),
        "snapshot_file_sha256": file_checksum(folder / "candidate.json"),
        "sealed_at": datetime.now(timezone.utc).isoformat(),
    }
    _validate_schema(integrity, "candidate_review_integrity.schema.json", "review integrity")
    _write_new(folder / "integrity.json", integrity, readonly=True)
    return review["review_id"]


def prepare_review_packets(candidates, packets_dir):
    validate_candidate_mapping(candidates)
    packets_dir = Path(packets_dir)
    if any((packets_dir / key).exists() for key in candidates):
        raise ValueError("Review packet already exists; no overwrite permitted; use a new packet folder")
    created = []
    for candidate_id, candidate in candidates.items():
        folder = packets_dir / candidate_id
        folder.mkdir(parents=True)
        draft = {
            "schema_version": "1.0.0", "review_id": None, "candidate_id": candidate_id,
            "candidate_sha256": candidate_checksum(candidate), "reviewer_alias": None, "review_timestamp": None,
            "source_verification_status": None,
            "claim_scope_assessment": {"status": None, "rationale": ""},
            "evidence_context_assessment": {"status": None, "rationale": ""},
            "evidence_reviews": [{"evidence_id": item["evidence_id"], "source_status": None,
                                  "source_verification_basis": "", "publication_date_status": None,
                                  "verified_publication_date": None, "date_rationale": "",
                                  "provenance_assessment": None, "provenance_rationale": ""}
                                 for item in candidate["evidence"]],
            "decision": None, "review_rationale": "", "supersedes": None,
        }
        _validate_schema(draft, "candidate_review_draft.schema.json", "blank review packet")
        _write_new(folder / "candidate.json", candidate, readonly=True)
        _write_new(folder / "review.json", draft)
        created.append(str(folder / "review.json"))
    return created


def approval_report(candidates, review_root=DEFAULT_REVIEWS):
    validate_candidate_mapping(candidates)
    latest = verify_reviews(review_root)
    rows = []
    for candidate_id, candidate in candidates.items():
        review = latest.get(candidate_id, {}).get("review")
        concerns = []
        reasons = candidate_issues(candidate)
        status = "pending"
        if review is None:
            reasons.append("Human approval is missing")
        elif review["candidate_sha256"] != candidate_checksum(candidate):
            status = "stale"
            reasons.append("Latest review checksum does not match the current candidate")
        else:
            status = review["decision"]
            if status != "approved":
                reasons.append("Latest human decision is " + status)
            else:
                reasons.extend(_approval_conditions(review, candidate))
        for evidence in candidate["evidence"]:
            if evidence["publication_date"] is None:
                concerns.append(evidence["evidence_id"] + ": publication date not recorded")
            if evidence["provenance_relation"] in {"unknown", "related_suspected"}:
                concerns.append(evidence["evidence_id"] + ": provenance independence not established")
        rows.append({"candidate_id": candidate_id, "candidate_sha256": candidate_checksum(candidate),
                     "review_status": status, "latest_decision": review["decision"] if review else None,
                     "latest_review_id": review["review_id"] if review else None,
                     "reviewer_alias": review["reviewer_alias"] if review else None,
                     "review_timestamp": review["review_timestamp"] if review else None,
                     "metadata_review": [{key: assessment[key] for key in (
                         "evidence_id", "publication_date_status", "verified_publication_date",
                         "date_rationale", "provenance_assessment", "provenance_rationale")}
                         for assessment in review["evidence_reviews"]] if review else [],
                     "import_eligible": status == "approved" and not reasons,
                     "blocked_reasons": reasons, "metadata_concerns": concerns})
    counts = Counter(row["review_status"] for row in rows)
    return {"candidates": rows, "counts": {status: counts[status] for status in
            ("approved", "revision_required", "rejected", "pending", "stale")},
            "eligible_count": sum(row["import_eligible"] for row in rows),
            "orphan_review_candidate_ids": sorted(set(latest) - set(candidates)),
            "note": "Inclusion approval is not a gold verdict, source credibility score or independent annotation."}


def render_approval_report(report):
    lines = ["# Candidate inclusion review status", "", report["note"], "",
             "Counts: " + json.dumps(report["counts"]),
             "Import eligible: " + str(report["eligible_count"]), ""]
    for row in report["candidates"]:
        lines.extend(["## " + row["candidate_id"], "", "Review status: " + row["review_status"],
                      "Import eligible: " + str(row["import_eligible"]), ""])
        lines.extend("- Blocked: " + reason for reason in row["blocked_reasons"])
        lines.extend("- Metadata concern: " + concern for concern in row["metadata_concerns"])
        for assessment in row["metadata_review"]:
            lines.append("- Reviewed date status for {0}: {1}; provenance: {2}.".format(
                assessment["evidence_id"], assessment["publication_date_status"], assessment["provenance_assessment"]))
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "submit", "report"])
    parser.add_argument("--collection", action="append", type=Path, help="Explicit candidate collection folders")
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument("--packets-dir", type=Path, default=DEFAULT_REVIEWS / "drafts")
    parser.add_argument("--file", type=Path, help="Completed human review JSON to submit")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REVIEWS / "reports")
    args = parser.parse_args(argv)
    try:
        candidates = load_candidates(args.collection)
        if args.command == "prepare":
            print("Created {0} blank review packets".format(len(prepare_review_packets(candidates, args.packets_dir))))
        elif args.command == "submit":
            if args.file is None:
                parser.error("submit requires --file")
            print("Preserved human review: " + submit_review(_load_json(args.file), candidates, args.review_root))
        else:
            report = approval_report(candidates, args.review_root)
            args.output_dir.mkdir(parents=True, exist_ok=True)
            (args.output_dir / "approval_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            (args.output_dir / "approval_report.md").write_text(render_approval_report(report), encoding="utf-8")
            print(json.dumps({"counts": report["counts"], "eligible_count": report["eligible_count"]}, indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, "Review workflow blocked: {0}\n".format(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
