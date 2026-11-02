"""Dependency-free contract tests for the independent annotation templates."""
import json
from datetime import datetime
import hashlib
from pathlib import Path

import pytest

from evaluation.annotation.validate_pilot import (
    SCHEMAS, _validate_schema, validate_pilot,
)
from evaluation.annotation.readiness_report import build_readiness_report
from evaluation.annotation.submission_integrity import (
    record_submission, sha256_file, verify_submission_integrity,
)

ANNOTATION_DIR = Path(__file__).parents[1] / "evaluation" / "annotation"
SCHEMA_DIR = ANNOTATION_DIR / "schemas"
TEMPLATE_DIR = ANNOTATION_DIR / "templates"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_annotation_schemas_are_valid_json_and_have_expected_identity():
    expected = {
        "claim_record.schema.json": "TruthLens claim and evidence record",
        "annotator_record.schema.json": "TruthLens independent annotator record",
        "adjudication_record.schema.json": "TruthLens adjudication record",
        "pilot_manifest.schema.json": "TruthLens 90-claim pilot manifest",
        "submission_integrity.schema.json": "TruthLens annotator submission integrity manifest",
    }
    for filename, title in expected.items():
        schema = load_json(SCHEMA_DIR / filename)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["title"] == title
        assert schema["type"] == "object"


def test_claim_schema_keeps_event_and_publication_dates_separate_and_unlabeled():
    schema = load_json(SCHEMA_DIR / "claim_record.schema.json")
    properties = schema["properties"]
    assert {"claim_id", "claim_text", "claim_category", "split", "annotation_status", "evidence"} <= set(properties)
    evidence_properties = properties["evidence"]["items"]["properties"]
    assert {"evidence_id", "passage", "source_title", "source_identifier", "source_url", "publisher_id"} <= set(evidence_properties)
    assert "publication_date" in evidence_properties
    assert "event_date" in evidence_properties
    assert "checked_on" in evidence_properties
    assert "gold_verdict" not in properties
    assert "gold_stance" not in evidence_properties
    assert "unannotated" in properties["annotation_status"]["enum"]


def test_annotator_and_adjudication_schemas_keep_independent_and_gold_labels_distinct():
    annotator = load_json(SCHEMA_DIR / "annotator_record.schema.json")["properties"]
    adjudication = load_json(SCHEMA_DIR / "adjudication_record.schema.json")["properties"]
    assert {"annotator_id", "claim_verdict", "annotation_confidence", "evidence_annotations"} <= set(annotator)
    evidence_annotation_fields = annotator["evidence_annotations"]["items"]["properties"]
    assert {"relevance", "stance", "stance_rationale", "confidence"} <= set(evidence_annotation_fields)
    assert "gold_verdict" not in annotator
    assert {"adjudication_status", "adjudicator_id", "gold_verdict", "evidence_labels"} <= set(adjudication)
    assert annotator["claim_verdict"]["enum"] == ["SUPPORTED", "CONTRADICTED", "INCONCLUSIVE"]
    assert "adjudicated" in adjudication["adjudication_status"]["enum"]


def test_new_annotation_templates_are_empty_not_fabricated_labels():
    for name in ("claim_records.json", "annotator_records.json", "adjudications.json"):
        assert load_json(TEMPLATE_DIR / name) == []


def _copy_empty_pilot(tmp_path):
    import shutil

    source = ANNOTATION_DIR / "pilot_90"
    target = tmp_path / "pilot_90"
    shutil.copytree(source, target)
    return target


def _claim_record(claim_id="claim-001"):
    return {
        "claim_id": claim_id,
        "claim_text": "ILLUSTRATIVE ONLY: no claim is present in the real pilot yet.",
        "claim_family_id": "family-001",
        "event_group_id": None,
        "claim_category": ["ordinary_control", "insufficient_evidence"],
        "split": "pilot",
        "annotation_status": "unannotated",
        "evidence": [{
            "evidence_id": "evidence-001",
            "passage": "ILLUSTRATIVE ONLY: no evidence passage is present in the real pilot yet.",
            "source_title": None,
            "source_identifier": None,
            "source_url": None,
            "publisher_id": None,
            "publication_date": None,
            "event_date": None,
            "checked_on": None,
            "provenance_group_id": None,
            "provenance_relation": "unknown",
            "provenance_basis": "No source provenance: illustrative schema test record only.",
        }],
    }


def _annotator_record(alias, verdict="INCONCLUSIVE"):
    return {
        "claim_id": "claim-001",
        "annotator_id": alias,
        "claim_verdict": verdict,
        "claim_rationale": "Illustrative validator test only.",
        "annotation_confidence": 3,
        "evidence_annotations": [{
            "evidence_id": "evidence-001",
            "relevance": "unrelated",
            "stance": "NOT ENOUGH INFORMATION",
            "stance_rationale": "Illustrative validator test only.",
            "confidence": 3,
            "notes": "Not a real annotation.",
        }],
        "annotation_notes": "Synthetic schema-validation fixture; not pilot data.",
    }


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def test_pilot_manifest_is_empty_and_validates_without_accessing_other_splits():
    result = validate_pilot(ANNOTATION_DIR / "pilot_90")
    manifest = load_json(ANNOTATION_DIR / "pilot_90" / "manifest.json")
    schema = load_json(SCHEMAS / "pilot_manifest.schema.json")

    assert manifest["target_claim_count"] == 90
    assert manifest["target_verdict_distribution"] == {
        "SUPPORTED": 30, "CONTRADICTED": 30, "INCONCLUSIVE": 30}
    assert len(manifest["challenge_categories"]) == 11
    claim_category_values = set(load_json(SCHEMAS / "claim_record.schema.json")
                                ["properties"]["claim_category"]["items"]["enum"])
    assert set(manifest["challenge_categories"]) <= claim_category_values
    for relative_path in manifest["annotator_submission_files"].values():
        assert (ANNOTATION_DIR / "pilot_90" / relative_path).is_file()
    assert result["status"] == "valid"
    assert result["claim_count"] == 0
    assert result["complete"] is False
    Draft202012Validator = pytest.importorskip("jsonschema").Draft202012Validator
    Draft202012Validator.check_schema(schema)


def test_pilot_validator_checks_schemas_references_and_identical_assignments(tmp_path):
    directory = _copy_empty_pilot(tmp_path)
    manifest = load_json(directory / "manifest.json")
    manifest["status"] = "collecting"
    claim = _claim_record()
    _write_json(directory / "manifest.json", manifest)
    _write_json(directory / "claim_records.json", [claim])
    _write_json(directory / "submissions" / "annotator_1.json", [_annotator_record("annotator_1")])
    _write_json(directory / "submissions" / "annotator_2.json", [_annotator_record("annotator_2")])

    result = validate_pilot(directory)

    assert result["annotator_claim_sets_match"] is True
    assert result["annotator_submission_counts"] == {"annotator_1": 1, "annotator_2": 1}
    assert result["complete"] is False  # Partial pilot; no gold/adjudications are invented.


def test_schema_validator_rejects_missing_required_fields_and_invalid_labels():
    claim = _claim_record()
    del claim["claim_text"]
    with pytest.raises(ValueError, match="claim_text"):
        _validate_schema(claim, "claim_record.schema.json", "claim")

    annotation = _annotator_record("annotator_1", verdict="SUPPORTED-ish")
    with pytest.raises(ValueError, match="SUPPORTED-ish"):
        _validate_schema(annotation, "annotator_record.schema.json", "annotation")

    with pytest.raises(ValueError, match="is not of type 'object'"):
        _validate_schema(["malformed"], "claim_record.schema.json", "claim")


def test_pilot_validator_rejects_duplicate_claim_and_evidence_ids(tmp_path):
    directory = _copy_empty_pilot(tmp_path)
    claim = _claim_record()
    duplicate_claim = _claim_record()
    _write_json(directory / "claim_records.json", [claim, duplicate_claim])
    with pytest.raises(ValueError, match="duplicate claim_id"):
        validate_pilot(directory)

    claim["evidence"].append(dict(claim["evidence"][0]))
    _write_json(directory / "claim_records.json", [claim])
    with pytest.raises(ValueError, match="duplicate evidence_id"):
        validate_pilot(directory)


def test_pilot_validator_rejects_duplicate_annotator_rows_and_unknown_evidence(tmp_path):
    directory = _copy_empty_pilot(tmp_path)
    _write_json(directory / "claim_records.json", [_claim_record()])
    duplicated = _annotator_record("annotator_1")
    _write_json(directory / "submissions" / "annotator_1.json", [duplicated, duplicated])
    with pytest.raises(ValueError, match="duplicate claim_id for annotator_1"):
        validate_pilot(directory)

    unknown = _annotator_record("annotator_1")
    unknown["evidence_annotations"][0]["evidence_id"] = "missing-evidence"
    _write_json(directory / "submissions" / "annotator_1.json", [unknown])
    with pytest.raises(ValueError, match="unknown evidence_id"):
        validate_pilot(directory)


def test_complete_pilot_requires_90_claims_and_both_matching_full_submissions(tmp_path):
    directory = _copy_empty_pilot(tmp_path)
    with pytest.raises(ValueError, match="incomplete"):
        validate_pilot(directory, require_complete=True)


def test_complete_pilot_accepts_90_double_annotated_synthetic_validator_rows(tmp_path):
    directory = _copy_empty_pilot(tmp_path)
    manifest = load_json(directory / "manifest.json")
    manifest["status"] = "ready"
    claims = []
    submissions = {"annotator_1": [], "annotator_2": []}
    for index in range(90):
        claim_id = "validator-claim-{0:03d}".format(index)
        evidence_id = "validator-evidence-{0:03d}".format(index)
        claim = _claim_record(claim_id)
        claim["evidence"][0]["evidence_id"] = evidence_id
        claims.append(claim)
        for alias in submissions:
            record = _annotator_record(alias)
            record["claim_id"] = claim_id
            record["evidence_annotations"][0]["evidence_id"] = evidence_id
            record["claim_rationale"] = "Synthetic validator coverage test; not an annotation."
            submissions[alias].append(record)
    _write_json(directory / "manifest.json", manifest)
    _write_json(directory / "claim_records.json", claims)
    for alias, records in submissions.items():
        _write_json(directory / manifest["annotator_submission_files"][alias], records)

    first_submission = record_submission(directory, "annotator_1")
    second_submission = record_submission(directory, "annotator_2")

    result = validate_pilot(directory, require_complete=True)

    assert result["complete"] is True
    assert result["claim_count"] == 90
    assert result["annotator_claim_sets_match"] is True
    assert result["integrity"]["annotator_1"]["status"] == "verified"
    assert result["integrity"]["annotator_2"]["status"] == "verified"
    assert first_submission["snapshot_file"] != second_submission["snapshot_file"]


def _ready_synthetic_pilot(tmp_path):
    directory = _copy_empty_pilot(tmp_path)
    manifest = load_json(directory / "manifest.json")
    manifest["status"] = "ready"
    claims = []
    submissions = {"annotator_1": [], "annotator_2": []}
    for index in range(90):
        claim_id = "synthetic-integrity-claim-{0:03d}".format(index)
        evidence_id = "synthetic-integrity-evidence-{0:03d}".format(index)
        claim = _claim_record(claim_id)
        claim["evidence"][0]["evidence_id"] = evidence_id
        claims.append(claim)
        for alias in submissions:
            record = _annotator_record(alias)
            record["claim_id"] = claim_id
            record["evidence_annotations"][0]["evidence_id"] = evidence_id
            submissions[alias].append(record)
    _write_json(directory / "manifest.json", manifest)
    _write_json(directory / "claim_records.json", claims)
    for alias, records in submissions.items():
        _write_json(directory / manifest["annotator_submission_files"][alias], records)
    return directory


def test_submission_integrity_manifest_records_hashes_and_iso_timestamp(tmp_path):
    directory = _ready_synthetic_pilot(tmp_path)
    result = record_submission(directory, "annotator_1")
    integrity = load_json(directory / result["integrity_manifest"])

    assert integrity["pilot_version"] == "truthlens-independent-annotation-pilot-v1"
    assert integrity["claim_manifest_sha256"] == sha256_file(directory / "manifest.json")
    assert integrity["claim_records_sha256"] == sha256_file(directory / "claim_records.json")
    assert integrity["submission_file_sha256"] == sha256_file(directory / integrity["snapshot_file"])
    assert integrity["snapshot_sha256"] == integrity["submission_file_sha256"]
    assert integrity["annotator_identifier"] == "annotator_1"
    assert integrity["schema_version"] == "1.0.0"
    assert integrity["validation_status"] == "valid"
    datetime.fromisoformat(integrity["submission_timestamp"].replace("Z", "+00:00"))
    assert hashlib.sha256((directory / integrity["snapshot_file"]).read_bytes()).hexdigest() == result["sha256"]


def test_integrity_detects_modified_working_submission_and_snapshot(tmp_path):
    directory = _ready_synthetic_pilot(tmp_path)
    result = record_submission(directory, "annotator_1")
    source = directory / "submissions" / "annotator_1.json"
    original_source = source.read_bytes()
    source.write_bytes(original_source + b" ")
    with pytest.raises(ValueError, match="working submission SHA-256 mismatch"):
        validate_pilot(directory)

    source.write_bytes(original_source)
    snapshot = directory / result["snapshot_file"]
    snapshot.chmod(0o644)
    snapshot.write_bytes(snapshot.read_bytes() + b" ")
    with pytest.raises(ValueError, match="snapshot SHA-256 mismatch"):
        validate_pilot(directory)


def test_require_complete_rejects_unsealed_submissions_missing_integrity_manifests(tmp_path):
    directory = _ready_synthetic_pilot(tmp_path)
    with pytest.raises(ValueError, match="integrity manifests and snapshots"):
        validate_pilot(directory, require_complete=True)


def test_submission_snapshot_cannot_be_overwritten_without_explicit_revision(tmp_path):
    directory = _ready_synthetic_pilot(tmp_path)
    original = record_submission(directory, "annotator_1")
    snapshot = directory / original["snapshot_file"]
    before = snapshot.read_bytes()

    with pytest.raises(ValueError, match="existing submission is protected"):
        record_submission(directory, "annotator_1")

    assert snapshot.read_bytes() == before
    assert validate_pilot(directory)["integrity"]["annotator_1"]["status"] == "verified"


def test_adjudication_must_reference_latest_verified_original_submissions(tmp_path):
    directory = _ready_synthetic_pilot(tmp_path)
    first = record_submission(directory, "annotator_1")
    second = record_submission(directory, "annotator_2")
    _write_json(directory / "adjudications.json", [{
        "claim_id": "synthetic-integrity-claim-000",
        "adjudication_status": "adjudicated",
        "adjudicator_id": "adjudicator-test",
        "annotator_submission_manifests": {
            "annotator_1": "submissions/integrity/annotator_1/forged.json",
            "annotator_2": second["integrity_manifest"],
        },
        "gold_verdict": "INCONCLUSIVE",
        "rationale": "Synthetic validator test only.",
        "evidence_labels": [{
            "evidence_id": "synthetic-integrity-evidence-000",
            "gold_relevance": "relevant",
            "gold_stance": "NOT ENOUGH INFORMATION",
            "rationale": "Synthetic validator test only.",
        }],
        "notes": "Not pilot data.",
    }])

    with pytest.raises(ValueError, match="latest verified submission"):
        validate_pilot(directory)

    assert first["integrity_manifest"] != second["integrity_manifest"]


def test_adjudication_rejects_duplicate_claim_records(tmp_path):
    directory = _ready_synthetic_pilot(tmp_path)
    first = record_submission(directory, "annotator_1")
    second = record_submission(directory, "annotator_2")
    adjudication = {
        "claim_id": "synthetic-integrity-claim-000",
        "adjudication_status": "adjudicated",
        "adjudicator_id": "adjudicator-test",
        "annotator_submission_manifests": {
            "annotator_1": first["integrity_manifest"],
            "annotator_2": second["integrity_manifest"],
        },
        "gold_verdict": "INCONCLUSIVE",
        "rationale": "Synthetic validator test only.",
        "evidence_labels": [{
            "evidence_id": "synthetic-integrity-evidence-000",
            "gold_relevance": "unrelated",
            "gold_stance": "NOT ENOUGH INFORMATION",
            "rationale": "Synthetic validator test only.",
        }],
        "notes": "Not pilot data.",
    }
    _write_json(directory / "adjudications.json", [adjudication, adjudication])
    with pytest.raises(ValueError, match="duplicate adjudicated claim_id"):
        validate_pilot(directory)


def test_readiness_report_shows_empty_pilot_as_not_ready_without_labels():
    report = build_readiness_report(ANNOTATION_DIR / "pilot_90")

    assert report["prepared_claims"] == 0
    assert report["claims_with_evidence"] == 0
    assert report["ready_for_analysis"] is False
    assert report["annotators"]["annotator_1"]["integrity_status"] == "not_submitted"
    assert report["adjudication_status"]["record_count"] == 0
    assert "gold_verdict" not in json.dumps(report)
