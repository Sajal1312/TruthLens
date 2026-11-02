"""Check internal preparation artifacts, not human verification or participant data."""
import hashlib
import json
from pathlib import Path
import pytest

from evaluation.compare_systems import fingerprint
from evaluation.explanation_study.analyze import read_bundle


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "evaluation/explanation_study/runs/study_v1"
INTERNAL = ROOT / "evaluation/explanation_study/runs/remediation_2026-11-02_internal"
pytestmark = pytest.mark.skipif(not INTERNAL.exists() or not STUDY.exists(),
                                reason="Local private preparation artifacts are intentionally excluded from Git")


def test_review_packet_matches_exact_existing_materials_and_keys():
    manifest = json.loads((INTERNAL / "PREPARATION_MANIFEST.json").read_text())
    bundle, _assignments = read_bundle(STUDY)
    assert manifest["source_bundle_id"] == bundle["bundle_id"]
    for name, digest in manifest["source_files_sha256"].items():
        assert hashlib.sha256((STUDY / "private" / name).read_bytes()).hexdigest() == digest
    items = {item["item_id"]: item for item in json.loads((STUDY / "private/materials.json").read_text())}
    questions = json.loads((STUDY / "private/questionnaire.json").read_text())
    keys = json.loads((STUDY / "private/answer_keys.json").read_text())["items"]
    text = (INTERNAL / "KEY_REVIEW_PACKET.md").read_text()
    assert len(manifest["items"]) == 24
    for row in manifest["items"]:
        item, name = items[row["item_id"]], row["question_id"]
        assert row["item_sha256"] == fingerprint(item)
        assert row["question_sha256"] == fingerprint(questions[row["item_id"]][name])
        assert row["key_sha256"] == fingerprint(keys[row["item_id"]][name])
        assert item["claim"] in text
        assert questions[row["item_id"]][name]["prompt"] in text
        assert all(evidence["passage"] in text for evidence in item["evidence"])


def test_prepared_worksheets_are_blank_and_not_submittable_records():
    text = (INTERNAL / "KEY_REVIEW_PACKET.md").read_text()
    assert text.count("Independent decision (verified / revision_required): __________") == 24
    assert text.count("Independent rationale: __________") == 24
    manifest = json.loads((INTERNAL / "PREPARATION_MANIFEST.json").read_text())
    assert manifest["status"] == "INTERNAL_DRAFT_NOT_FOR_RECRUITMENT"
    assert manifest["participant_bundle_created"] is False
    assert manifest["participant_responses_created"] == manifest["human_key_approvals"] == 0
    assert not list(INTERNAL.glob("*.html"))


def test_internal_artifact_checksums_match():
    manifest = json.loads((INTERNAL / "PREPARATION_MANIFEST.json").read_text())
    for name, digest in manifest["artifacts_sha256"].items():
        assert hashlib.sha256((INTERNAL / name).read_bytes()).hexdigest() == digest


def test_investigator_decisions_and_preflight_are_unfilled():
    text = (INTERNAL / "INVESTIGATOR_INFORMATION_WORKSHEET.md").read_text()
    assert sum(line.startswith("| C") for line in text.splitlines()) == 20
    assert "Not a participant information sheet" in text
    assert "Academic supervisor" in text
    checklist = (INTERNAL / "BROWSER_ACCESSIBILITY_PREFLIGHT.md").read_text()
    for phrase in ("Safari/macOS result", "Chrome/macOS result", "VoiceOver", "UTF-8", "null", "consent unchecked"):
        assert phrase in checklist


def test_proposals_retain_all_twelve_claims_as_proposals_only():
    text = (INTERNAL / "PROPOSED_MATERIAL_REVISIONS.md").read_text()
    items = json.loads((STUDY / "private/materials.json").read_text())
    assert len(items) == 12
    assert all(item["claim"] in text for item in items)
    assert "not applied" in text and "not new keys" in text
