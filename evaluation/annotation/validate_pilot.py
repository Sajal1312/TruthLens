"""Validate the 90-claim annotation pilot files without touching TruthLens runtime data."""
import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parent
DEFAULT_PILOT = ROOT / "pilot_90"
SCHEMAS = ROOT / "schemas"


def _load_json(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _validate_schema(record, schema_name, label):
    schema = _load_json(SCHEMAS / schema_name)
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record),
                    key=lambda error: list(error.absolute_path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<record>"
        raise ValueError("{0} at {1}: {2}".format(label, location, error.message))


def _validate_unique(items, key_function, label):
    seen = set()
    for item in items:
        key = key_function(item)
        if key in seen:
            raise ValueError("duplicate {0}: {1}".format(label, key))
        seen.add(key)


def validate_pilot(directory=DEFAULT_PILOT, require_complete=False, *, verify_checksums=True):
    """Validate schemas, identifiers, paired coverage, snapshots, and adjudications."""
    directory = Path(directory)
    manifest = _load_json(directory / "manifest.json")
    _validate_schema(manifest, "pilot_manifest.schema.json", "pilot manifest")

    claim_records = _load_json(directory / manifest["claim_records_file"])
    if not isinstance(claim_records, list):
        raise ValueError("claim_records_file must contain a JSON array")
    for index, record in enumerate(claim_records):
        _validate_schema(record, "claim_record.schema.json", "claim record {0}".format(index))
        _validate_unique(record["evidence"], lambda item: item["evidence_id"],
                         "evidence_id in " + record["claim_id"])
    _validate_unique(claim_records, lambda item: item["claim_id"], "claim_id")
    claims_by_id = {record["claim_id"]: record for record in claim_records}

    submission_ids = {}
    for annotator_alias, relative_path in manifest["annotator_submission_files"].items():
        records = _load_json(directory / relative_path)
        if not isinstance(records, list):
            raise ValueError("{0} must contain a JSON array".format(relative_path))
        for index, record in enumerate(records):
            _validate_schema(record, "annotator_record.schema.json",
                             "{0} submission {1}".format(annotator_alias, index))
            if record["annotator_id"] != annotator_alias:
                raise ValueError("annotator_id in {0} must match manifest alias {1}".format(
                    relative_path, annotator_alias))
            claim_id = record["claim_id"]
            if claim_id not in claims_by_id:
                raise ValueError("unknown claim_id in {0}: {1}".format(relative_path, claim_id))
            known_evidence = {item["evidence_id"] for item in claims_by_id[claim_id]["evidence"]}
            evidence_annotations = record["evidence_annotations"]
            _validate_unique(evidence_annotations, lambda item: item["evidence_id"],
                             "annotated evidence_id in " + claim_id)
            annotated_evidence = {item["evidence_id"] for item in evidence_annotations}
            if require_complete and annotated_evidence != known_evidence:
                raise ValueError("incomplete evidence annotations for {0} by {1}".format(
                    claim_id, annotator_alias))
            for annotation in evidence_annotations:
                if annotation["evidence_id"] not in known_evidence:
                    raise ValueError("unknown evidence_id for claim {0}: {1}".format(
                        claim_id, annotation["evidence_id"]))
        _validate_unique(records, lambda item: item["claim_id"],
                         "claim_id for " + annotator_alias)
        submission_ids[annotator_alias] = {record["claim_id"] for record in records}

    submission_sets_match = len(submission_ids) == 2 and len(set(
        frozenset(ids) for ids in submission_ids.values())) == 1
    annotation_records_complete = (
        manifest["status"] == "ready"
        and len(claim_records) == manifest["target_claim_count"]
        and all(ids == set(claims_by_id) for ids in submission_ids.values())
    )
    if manifest["status"] == "ready" and len(claim_records) != manifest["target_claim_count"]:
        raise ValueError("ready manifest must contain exactly 90 claim records")

    from evaluation.annotation.submission_integrity import verify_submission_integrity
    integrity = verify_submission_integrity(
        directory, manifest, claims_by_id, submission_ids,
        check_working_sources=verify_checksums)
    if integrity["errors"]:
        raise ValueError("submission integrity validation failed: " + "; ".join(integrity["errors"]))
    integrity_complete = all(
        integrity["annotators"].get(alias, {}).get("status") == "verified"
        for alias in manifest["annotator_submission_files"])
    complete = annotation_records_complete and integrity_complete
    if require_complete and not annotation_records_complete:
        raise ValueError("pilot is incomplete: require 90 claims and matching complete submissions from both annotators")
    if require_complete and not integrity_complete:
        raise ValueError("pilot submissions are incomplete: verified integrity manifests and snapshots are required")

    adjudications = _load_json(directory / manifest["adjudications_file"])
    if not isinstance(adjudications, list):
        raise ValueError("adjudications_file must contain a JSON array")
    for index, record in enumerate(adjudications):
        _validate_schema(record, "adjudication_record.schema.json",
                         "adjudication record {0}".format(index))
        claim_id = record["claim_id"]
        if claim_id not in claims_by_id:
            raise ValueError("unknown adjudicated claim_id: " + claim_id)
        known_evidence = {item["evidence_id"] for item in claims_by_id[claim_id]["evidence"]}
        labels = record["evidence_labels"]
        _validate_unique(labels, lambda item: item["evidence_id"],
                         "adjudicated evidence_id in " + claim_id)
        for label in labels:
            if label["evidence_id"] not in known_evidence:
                raise ValueError("unknown adjudicated evidence_id for claim {0}: {1}".format(
                    claim_id, label["evidence_id"]))
        if {label["evidence_id"] for label in labels} != known_evidence:
            raise ValueError("adjudication evidence IDs do not match the claim record: " + claim_id)
        references = record["annotator_submission_manifests"]
        for alias in manifest["annotator_submission_files"]:
            referenced_path = references[alias]
            latest_path = integrity["latest_manifest_paths"].get(alias)
            if latest_path is None or referenced_path != latest_path:
                raise ValueError("adjudication must reference the latest verified submission for " + alias)
            snapshot_records = integrity["latest_snapshot_records"].get(alias, [])
            if claim_id not in {item["claim_id"] for item in snapshot_records}:
                raise ValueError("adjudication claim is absent from original submission for " + alias)
    _validate_unique(adjudications, lambda item: item["claim_id"], "adjudicated claim_id")

    return {
        "status": "valid",
        "pilot_status": manifest["status"],
        "claim_count": len(claim_records),
        "target_claim_count": manifest["target_claim_count"],
        "annotator_submission_counts": {key: len(value) for key, value in submission_ids.items()},
        "annotator_claim_sets_match": submission_sets_match,
        "annotation_records_complete": annotation_records_complete,
        "integrity": integrity["annotators"],
        "adjudication_count": len(adjudications),
        "adjudication_status_counts": {
            status: sum(record["adjudication_status"] == status for record in adjudications)
            for status in ("pending", "adjudicated")
        },
        "complete": complete,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default=str(DEFAULT_PILOT), help="Pilot folder containing manifest and records")
    parser.add_argument("--require-complete", action="store_true", help="Require 90 claims and both full submissions")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(validate_pilot(args.directory, args.require_complete), indent=2))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print("Invalid pilot: {0}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
