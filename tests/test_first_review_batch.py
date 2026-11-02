"""Offline version/source-record integrity of the first unsubmitted review batch."""
import json
from pathlib import Path

from evaluation.annotation.candidate_review import candidate_checksum, file_checksum, load_candidates
from evaluation.annotation.validate_pilot import _validate_schema


ROOT = Path(__file__).parents[1]
BATCH = ROOT / "evaluation/annotation/candidate_reviews/first_batch_2026-11-02"


def inputs():
    manifest = json.loads((BATCH / "manifest.json").read_text())
    paths = list(manifest["inputs_sha256"])
    prior = json.loads((ROOT / next(p for p in paths if p.endswith("assessments.json"))).read_text())
    followup = json.loads((ROOT / next(p for p in paths if p.endswith("followup.json"))).read_text())
    return manifest, load_candidates(), prior, followup


def test_batch_selects_five_current_version_routine_candidates_only():
    manifest, candidates, prior, followup = inputs()
    selected = [row["candidate_id"] for row in manifest["candidates"]]
    assert len(selected) == len(set(selected)) == 5
    excluded = {row["candidate_id"] for row in followup["candidate_followups"]}
    eligible = {row["candidate_id"] for row in prior
                if row["candidate_id"] not in excluded
                and row["recommended_action"] == "suitable for human approval"}
    assert len(eligible) == 21
    assert set(selected).issubset(eligible)
    assert all(next(row for row in prior if row["candidate_id"] == cid)["human_review_priority"] == "routine"
               for cid in selected)
    assert all(cid in candidates for cid in selected)


def test_batch_document_sources_and_packets_match_current_versions():
    manifest, candidates, _, _ = inputs()
    document = ROOT / manifest["document"]["path"]
    assert file_checksum(document) == manifest["document"]["sha256"]
    sheet = document.read_text()
    for path, expected in manifest["inputs_sha256"].items():
        assert file_checksum(ROOT / path) == expected
    for row in manifest["candidates"]:
        candidate = candidates[row["candidate_id"]]
        assert row["candidate_sha256"] == candidate_checksum(candidate)
        assert "**Exact claim:** " + candidate["claim_text"] in sheet
        assert row["candidate_sha256"] in sheet
        assert row["evidence_sha256"] == {
            e["evidence_id"]: candidate_checksum(e) for e in candidate["evidence"]}
        for evidence in candidate["evidence"]:
            assert evidence["evidence_id"] in sheet
            assert evidence["source_url"] in sheet
            assert "> " + evidence["passage"].replace("\n", "\n> ") in sheet
        for path, expected in row["packet_files_sha256"].items():
            assert file_checksum(ROOT / path) == expected
            saved = json.loads((ROOT / path).read_text())
            if path.endswith("candidate.json"):
                assert saved == candidate
            else:
                _validate_schema(saved, "candidate_review_draft.schema.json", "unchanged blank packet")


def test_batch_leaves_all_human_fields_blank_and_does_not_claim_fresh_checks():
    manifest, _, _, _ = inputs()
    sheet = (ROOT / manifest["document"]["path"]).read_text()
    for field in ("Reviewer identity/alias", "Review ID", "Actual review timestamp with timezone", "Human decision"):
        assert sheet.count("**" + field + ":** ____________________") == 5
    assert sheet.count("**Human rationale / requested changes:** ________________________________________") == 5
    assert sheet.count("— none selected.") == 5
    assert "No websites were reopened" in sheet
    assert "not a checksum of live webpages" in sheet
    assert "not human approval or gold labels" in sheet
    assert "decision" not in manifest and "reviewer_alias" not in manifest
