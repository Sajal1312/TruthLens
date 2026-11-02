"""Report 90-claim pilot preparation status without printing annotation content."""
import argparse
import json
from collections import Counter
from pathlib import Path
import sys

from evaluation.annotation.validate_pilot import DEFAULT_PILOT, SCHEMAS, _load_json, validate_pilot


def _read_array(path, missing_ok=False):
    path = Path(path)
    if missing_ok and not path.exists():
        return []
    value = _load_json(path)
    if not isinstance(value, list):
        raise ValueError("{0} must contain a JSON array".format(path.name))
    return value


def _missing_fields(record, schema, prefix):
    missing = []
    for field in schema.get("required", []):
        if field not in record:
            missing.append(prefix + "." + field)
    properties = schema.get("properties", {})
    evidence_schema = properties.get("evidence", {}).get("items", {})
    for index, evidence in enumerate(record.get("evidence", []) or []):
        if not isinstance(evidence, dict):
            missing.append("{0}.evidence[{1}] (must be an object)".format(prefix, index))
            continue
        for field in evidence_schema.get("required", []):
            if field not in evidence:
                missing.append("{0}.evidence[{1}].{2}".format(prefix, index, field))
    return missing


def build_readiness_report(directory=DEFAULT_PILOT):
    directory = Path(directory)
    errors = []
    try:
        manifest = _load_json(directory / "manifest.json")
        claim_records = _read_array(directory / manifest["claim_records_file"])
        claim_schema = _load_json(SCHEMAS / "claim_record.schema.json")
        annotator_schema = _load_json(SCHEMAS / "annotator_record.schema.json")
        adjudication_schema = _load_json(SCHEMAS / "adjudication_record.schema.json")
        missing = []
        for index, record in enumerate(claim_records):
            if isinstance(record, dict):
                missing.extend(_missing_fields(record, claim_schema, "claim[{0}]".format(index)))
        category_counts = Counter({category: 0 for category in manifest.get("challenge_categories", [])})
        category_counts.update(
            category for record in claim_records if isinstance(record, dict)
            for category in record.get("claim_category", [])
        )
        claims_with_evidence = sum(
            bool(record.get("evidence")) for record in claim_records if isinstance(record, dict))
        evidence_count = sum(
            len(record.get("evidence", [])) for record in claim_records if isinstance(record, dict))
        missing_evidence_fields = [field for field in missing if ".evidence[" in field]

        validation = None
        try:
            validation = validate_pilot(directory)
        except (OSError, json.JSONDecodeError, ValueError, KeyError) as error:
            errors.append(str(error))

        annotators = {}
        missing_submission_fields = []
        for alias, relative_path in manifest.get("annotator_submission_files", {}).items():
            try:
                records = _read_array(directory / relative_path, missing_ok=True)
                for index, record in enumerate(records):
                    if isinstance(record, dict):
                        missing_submission_fields.extend(_missing_fields(
                            record, annotator_schema, "{0}[{1}]".format(alias, index)))
                        annotation_schema = annotator_schema["properties"]["evidence_annotations"]["items"]
                        for evidence_index, annotation in enumerate(record.get("evidence_annotations", []) or []):
                            if isinstance(annotation, dict):
                                for field in annotation_schema.get("required", []):
                                    if field not in annotation:
                                        missing_submission_fields.append(
                                            "{0}[{1}].evidence_annotations[{2}].{3}".format(
                                                alias, index, evidence_index, field))
                covered_claims = {record.get("claim_id") for record in records if isinstance(record, dict)}
                evidence_annotated = sum(
                    len(record.get("evidence_annotations", []))
                    for record in records if isinstance(record, dict))
                integrity = (validation or {}).get("integrity", {}).get(alias, {}).get("status", "unknown")
                if not records:
                    submission_status = "not_started"
                elif (len(covered_claims) == len(claim_records)
                      and len(covered_claims) == manifest.get("target_claim_count")):
                    submission_status = "complete_sealed" if integrity == "verified" else "complete_unsealed"
                else:
                    submission_status = "partial"
                annotators[alias] = {
                    "submission_status": submission_status,
                    "claim_records": len(records),
                    "distinct_claims_covered": len(covered_claims),
                    "evidence_annotations": evidence_annotated,
                    "integrity_status": integrity,
                }
            except (OSError, json.JSONDecodeError, ValueError) as error:
                annotators[alias] = {"submission_status": "invalid", "integrity_status": "unknown"}
                errors.append("{0}: {1}".format(alias, error))

        adjudications = _read_array(directory / manifest.get("adjudications_file", "adjudications.json"), missing_ok=True)
        missing_adjudication_fields = []
        for index, record in enumerate(adjudications):
            if isinstance(record, dict):
                missing_adjudication_fields.extend(_missing_fields(
                    record, adjudication_schema, "adjudication[{0}]".format(index)))
                labels_schema = adjudication_schema["properties"]["evidence_labels"]["items"]
                for label_index, label in enumerate(record.get("evidence_labels", []) or []):
                    if isinstance(label, dict):
                        for field in labels_schema.get("required", []):
                            if field not in label:
                                missing_adjudication_fields.append(
                                    "adjudication[{0}].evidence_labels[{1}].{2}".format(
                                        index, label_index, field))
        adjudication_counts = Counter(
            record.get("adjudication_status", "missing")
            for record in adjudications if isinstance(record, dict))
        all_adjudicated = (
            len(adjudications) == manifest.get("target_claim_count")
            and all(record.get("adjudication_status") == "adjudicated"
                    for record in adjudications if isinstance(record, dict))
        )
        analysis_ready = bool(validation and validation.get("complete") and all_adjudicated)
        return {
            "pilot_id": manifest.get("pilot_id"),
            "validation_status": "valid" if validation else "invalid",
            "prepared_claims": len(claim_records),
            "target_claims": manifest.get("target_claim_count"),
            "claims_with_evidence": claims_with_evidence,
            "evidence_records": evidence_count,
            "evidence_field_completeness": {
                "missing_required_field_count": len(missing_evidence_fields),
                "complete": None if evidence_count == 0 else len(missing_evidence_fields) == 0,
                "status": "not_applicable" if evidence_count == 0 else (
                    "complete" if not missing_evidence_fields else "incomplete"),
            },
            "challenge_category_distribution": dict(sorted(category_counts.items())),
            "missing_required_fields": {
                "claims_and_evidence": missing,
                "annotator_submissions": missing_submission_fields,
                "adjudications": missing_adjudication_fields,
            },
            "annotators": annotators,
            "adjudication_status": {
                "record_count": len(adjudications),
                "counts": dict(sorted(adjudication_counts.items())),
            },
            "ready_for_analysis": analysis_ready,
            "note": "Readiness is a structural check. It cannot prove that records were produced by humans or that access controls were followed.",
            "errors": errors,
        }
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        return {"validation_status": "invalid", "ready_for_analysis": False,
                "errors": [str(error)]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default=str(DEFAULT_PILOT), help="Pilot folder")
    args = parser.parse_args(argv)
    print(json.dumps(build_readiness_report(args.directory), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
