"""Append-only snapshots and SHA-256 verification for annotation submissions.

Hashes detect accidental changes, not malicious tampering by someone who can
edit the data and manifests. Use an external trusted archive for stronger audit.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat


SCHEMA_VERSION = "1.0.0"
_ALIAS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def _safe_relative(directory, value):
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("integrity path must be a relative path inside the pilot directory")
    root = Path(directory).resolve()
    resolved = (root / relative).resolve()
    if os.path.commonpath((str(root), str(resolved))) != str(root):
        raise ValueError("integrity path escapes the pilot directory")
    return resolved


def _check_snapshot_records(directory, alias, snapshot_records, claims_by_id):
    from evaluation.annotation.validate_pilot import _validate_schema, _validate_unique

    if not isinstance(snapshot_records, list):
        raise ValueError("snapshot must contain a JSON array")
    for index, record in enumerate(snapshot_records):
        _validate_schema(record, "annotator_record.schema.json",
                         "{0} snapshot record {1}".format(alias, index))
        if record["annotator_id"] != alias:
            raise ValueError("snapshot annotator identity does not match " + alias)
        claim_id = record["claim_id"]
        if claim_id not in claims_by_id:
            raise ValueError("snapshot refers to unknown claim_id: " + claim_id)
        expected_evidence = {item["evidence_id"] for item in claims_by_id[claim_id]["evidence"]}
        annotations = record["evidence_annotations"]
        _validate_unique(annotations, lambda item: item["evidence_id"],
                         "snapshot evidence_id in " + claim_id)
        if {item["evidence_id"] for item in annotations} != expected_evidence:
            raise ValueError("snapshot evidence IDs do not match the claim manifest for " + claim_id)
    _validate_unique(snapshot_records, lambda item: item["claim_id"],
                     "snapshot claim_id for " + alias)
    if {record["claim_id"] for record in snapshot_records} != set(claims_by_id):
        raise ValueError("snapshot claim IDs do not match the complete pilot manifest for " + alias)


def verify_submission_integrity(directory, pilot_manifest, claims_by_id,
                                working_submission_ids, *, check_working_sources=True):
    """Verify integrity manifests, source copies, snapshots, and revision chains."""
    from evaluation.annotation.validate_pilot import _validate_schema

    directory = Path(directory)
    integrity_root = directory / "submissions" / "integrity"
    aliases = pilot_manifest["annotator_submission_files"]
    result = {"annotators": {}, "latest_manifest_paths": {}, "latest_manifests": {},
              "latest_snapshot_records": {}, "errors": []}
    discovered = []
    if integrity_root.exists():
        discovered = sorted(integrity_root.rglob("*.json"))

    records_by_alias = {alias: [] for alias in aliases}
    manifest_objects = {}
    for path in discovered:
        relative_path = path.relative_to(directory).as_posix()
        try:
            integrity_record = _load_json(path)
            _validate_schema(integrity_record, "submission_integrity.schema.json",
                             "integrity manifest " + relative_path)
            alias = integrity_record["annotator_identifier"]
            if alias not in aliases:
                raise ValueError("unknown annotator identifier: " + alias)
            if integrity_record["source_submission_file"] != aliases[alias]:
                raise ValueError("integrity source submission path does not match pilot manifest")
            if path.parent.name != alias:
                raise ValueError("integrity manifest is stored under the wrong annotator folder")
            snapshot_path = _safe_relative(directory, integrity_record["snapshot_file"])
            if snapshot_path.parent.name != alias or "snapshots" not in snapshot_path.parts:
                raise ValueError("snapshot is stored outside the annotator snapshot folder")
            snapshot_hash = sha256_file(snapshot_path)
            if snapshot_hash != integrity_record["snapshot_sha256"]:
                raise ValueError("snapshot SHA-256 mismatch: " + relative_path)
            if snapshot_hash != integrity_record["submission_file_sha256"]:
                raise ValueError("submission file SHA-256 mismatch: " + relative_path)
            if snapshot_hash != integrity_record["source_submission_sha256"]:
                raise ValueError("source and snapshot checksums differ: " + relative_path)
            if integrity_record["claim_manifest_sha256"] != sha256_file(directory / "manifest.json"):
                raise ValueError("claim manifest SHA-256 mismatch: " + relative_path)
            if integrity_record["claim_records_sha256"] != sha256_file(
                    directory / pilot_manifest["claim_records_file"]):
                raise ValueError("claim/evidence records SHA-256 mismatch: " + relative_path)
            snapshot_records = _load_json(snapshot_path)
            _check_snapshot_records(directory, alias, snapshot_records, claims_by_id)
            manifest_objects[relative_path] = integrity_record
            records_by_alias[alias].append((relative_path, integrity_record, snapshot_records))
        except (OSError, json.JSONDecodeError, ValueError, KeyError) as error:
            result["errors"].append("{0}: {1}".format(relative_path, error))

    superseded = set()
    superseded_by = {}
    for relative_path, integrity_record in manifest_objects.items():
        previous = integrity_record.get("supersedes")
        if previous is None:
            continue
        try:
            previous_path = Path(previous)
            if previous_path.is_absolute() or ".." in previous_path.parts:
                raise ValueError("supersedes path must be relative")
            previous_key = previous_path.as_posix()
            if previous_key not in manifest_objects:
                raise ValueError("superseded integrity manifest does not exist")
            if manifest_objects[previous_key]["annotator_identifier"] != integrity_record["annotator_identifier"]:
                raise ValueError("cannot supersede another annotator's submission")
            if previous_key in superseded_by:
                raise ValueError("conflicting revision chain: manifest superseded more than once")
            superseded.add(previous_key)
            superseded_by[previous_key] = relative_path
        except ValueError as error:
            result["errors"].append("{0}: {1}".format(relative_path, error))

    for alias, submission_path in aliases.items():
        alias_records = records_by_alias[alias]
        current_ids = working_submission_ids.get(alias, set())
        if not alias_records:
            snapshot_dir = directory / "submissions" / "snapshots" / alias
            has_orphan_snapshot = snapshot_dir.exists() and any(snapshot_dir.iterdir())
            status = "missing_manifest" if has_orphan_snapshot else (
                "unsealed" if current_ids else "not_submitted")
            result["annotators"][alias] = {"status": status, "manifest_count": 0,
                                         "errors": []}
            if has_orphan_snapshot:
                result["errors"].append("orphan snapshot exists without an integrity manifest for " + alias)
            continue
        possible_latest = [entry for entry in alias_records if entry[0] not in superseded]
        if len(possible_latest) != 1:
            result["annotators"][alias] = {
                "status": "invalid_revision_chain", "manifest_count": len(alias_records),
                "errors": ["expected exactly one latest integrity manifest"],
            }
            result["errors"].append("invalid revision chain for " + alias)
            continue
        latest_path, latest_record, latest_snapshot = possible_latest[0]
        alias_errors = []
        source_path = _safe_relative(directory, latest_record["source_submission_file"])
        if check_working_sources and sha256_file(source_path) != latest_record["source_submission_sha256"]:
            alias_errors.append("working submission SHA-256 mismatch")
        if latest_record.get("supersedes") is not None:
            parent = latest_record["supersedes"]
            if parent not in manifest_objects:
                alias_errors.append("latest revision references a missing prior manifest")
        if alias_errors:
            result["errors"].extend("{0}: {1}".format(alias, message) for message in alias_errors)
        result["annotators"][alias] = {
            "status": "mismatch" if alias_errors else "verified",
            "manifest_count": len(alias_records),
            "latest_manifest": latest_path,
            "latest_snapshot": latest_record["snapshot_file"],
            "errors": alias_errors,
        }
        result["latest_manifest_paths"][alias] = latest_path
        result["latest_manifests"][alias] = latest_record
        result["latest_snapshot_records"][alias] = latest_snapshot
    return result


def record_submission(directory, annotator_identifier, *, supersedes=None):
    """Snapshot one complete submission without modifying its working file."""
    from evaluation.annotation.validate_pilot import _load_json, validate_pilot

    directory = Path(directory)
    if not _ALIAS_RE.fullmatch(annotator_identifier):
        raise ValueError("annotator identifier must be a non-personal alias")
    report = validate_pilot(directory, verify_checksums=False)
    pilot_manifest = _load_json(directory / "manifest.json")
    submission_paths = pilot_manifest["annotator_submission_files"]
    if annotator_identifier not in submission_paths:
        raise ValueError("annotator is not assigned in the pilot manifest")
    if pilot_manifest["status"] != "ready" or report["claim_count"] != pilot_manifest["target_claim_count"]:
        raise ValueError("pilot manifest and all 90 claim records must be ready before submission")
    if report["annotator_submission_counts"].get(annotator_identifier, 0) != report["claim_count"]:
        raise ValueError("annotator submission must contain exactly one record for every claim")
    source_path = directory / submission_paths[annotator_identifier]
    source_bytes = source_path.read_bytes()
    source_records = json.loads(source_bytes.decode("utf-8"))
    claims = _load_json(directory / pilot_manifest["claim_records_file"])
    evidence_by_claim = {
        claim["claim_id"]: {entry["evidence_id"] for entry in claim["evidence"]}
        for claim in claims
    }
    for record in source_records:
        if {entry["evidence_id"] for entry in record["evidence_annotations"]} != evidence_by_claim[record["claim_id"]]:
            raise ValueError("annotator submission is missing or has extra evidence annotations")

    prior_integrity = verify_submission_integrity(
        directory, pilot_manifest,
        {claim["claim_id"]: claim for claim in claims},
        {annotator_identifier: {record["claim_id"] for record in source_records}},
        check_working_sources=False)
    if prior_integrity["errors"]:
        raise ValueError("existing integrity record is invalid: " + "; ".join(prior_integrity["errors"]))
    latest_path = prior_integrity["latest_manifest_paths"].get(annotator_identifier)
    if latest_path and supersedes != latest_path:
        raise ValueError("an existing submission is protected; pass --supersedes with the latest manifest path for an explicit revision")
    if not latest_path and supersedes is not None:
        raise ValueError("--supersedes does not refer to an existing submission")

    source_sha = sha256_bytes(source_bytes)
    timestamp = datetime.now(timezone.utc)
    iso_timestamp = timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z")
    file_stamp = timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    basename = "{0}_{1}_{2}".format(annotator_identifier, file_stamp, source_sha[:12])
    snapshot_relative = Path("submissions") / "snapshots" / annotator_identifier / (basename + ".json")
    integrity_relative = Path("submissions") / "integrity" / annotator_identifier / (basename + ".integrity.json")
    snapshot_path = directory / snapshot_relative
    integrity_path = directory / integrity_relative
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    integrity_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with snapshot_path.open("xb") as stream:
            stream.write(source_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            snapshot_path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        except OSError:
            pass  # Advisory only; checksums provide accidental-change detection.
        snapshot_sha = sha256_file(snapshot_path)
        record = {
            "pilot_version": pilot_manifest["pilot_id"],
            "claim_manifest_sha256": sha256_file(directory / "manifest.json"),
            "claim_records_sha256": sha256_file(directory / pilot_manifest["claim_records_file"]),
            "annotator_identifier": annotator_identifier,
            "submission_timestamp": iso_timestamp,
            "source_submission_file": submission_paths[annotator_identifier],
            "source_submission_sha256": source_sha,
            "snapshot_file": snapshot_relative.as_posix(),
            "submission_file_sha256": snapshot_sha,
            "snapshot_sha256": snapshot_sha,
            "schema_version": SCHEMA_VERSION,
            "validation_status": "valid",
            "supersedes": supersedes,
        }
        from evaluation.annotation.validate_pilot import _validate_schema
        _validate_schema(record, "submission_integrity.schema.json", "submission integrity manifest")
        with integrity_path.open("xb") as stream:
            stream.write((json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        # Never remove an already written snapshot: it may be the only copy.
        raise
    return {"snapshot_file": snapshot_relative.as_posix(),
            "integrity_manifest": integrity_relative.as_posix(),
            "sha256": snapshot_sha, "submission_timestamp": iso_timestamp,
            "annotator_identifier": annotator_identifier}
