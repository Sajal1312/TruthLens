"""Offline contracts for the staged source collection; no network or model use."""
import json
from pathlib import Path
import shutil

import pytest

from evaluation.annotation.review_candidates import (
    DEFAULT_CANDIDATES, review_candidates, review_collections, render_review,
)
from evaluation.annotation.validate_pilot import DEFAULT_PILOT


def test_candidate_batch_has_15_traceable_unannotated_records_and_balanced_topics():
    report = review_candidates()
    assert report["claim_count"] == 15
    assert report["evidence_count"] > report["claim_count"]
    assert report["topic_distribution"] == {
        "sustainability_environment": 5, "cybersecurity_technology": 5, "general_factual": 5}
    assert report["finding_counts"]["error"] == 0
    assert report["duplicate_flags"] == []
    assert len(report["candidates_requiring_human_review"]) == 15
    assert report["candidates_without_collector_located_passages"] == []
    assert report["human_review_status"] == "pending_for_all_candidates"


def test_review_does_not_change_real_pilot_or_generate_submissions():
    before = {path: path.read_bytes() for path in DEFAULT_PILOT.rglob("*.json")}
    review_candidates()
    assert {path: path.read_bytes() for path in DEFAULT_PILOT.rglob("*.json")} == before


def test_changed_excerpt_requires_new_source_check(tmp_path):
    directory = tmp_path / "candidates"
    shutil.copytree(DEFAULT_CANDIDATES, directory)
    path = directory / "claim_records.json"
    records = json.loads(path.read_text())
    records[0]["evidence"][0]["passage"] += " altered"
    path.write_text(json.dumps(records))
    with pytest.raises(ValueError, match="source check must be repeated"):
        review_candidates(directory)


def test_missing_source_check_reference_is_rejected(tmp_path):
    directory = tmp_path / "candidates"
    shutil.copytree(DEFAULT_CANDIDATES, directory)
    path = directory / "collection_manifest.json"
    manifest = json.loads(path.read_text())
    manifest["source_checks"].pop(next(iter(manifest["source_checks"])))
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="references must match"):
        review_candidates(directory)


def test_gold_label_or_human_approval_cannot_be_injected_into_staged_records(tmp_path):
    directory = tmp_path / "candidates"
    shutil.copytree(DEFAULT_CANDIDATES, directory)
    path = directory / "claim_records.json"
    records = json.loads(path.read_text())
    records[0]["gold_verdict"] = "SUPPORTED"
    path.write_text(json.dumps(records))
    with pytest.raises(ValueError, match="Additional properties"):
        review_candidates(directory)


def test_combined_candidates_cover_30_claims_and_all_planned_tags_without_labels():
    report = review_collections([DEFAULT_CANDIDATES, DEFAULT_CANDIDATES.parent / "phase2_15"])
    assert report["claim_count"] == 30
    assert set(report["topic_distribution"].values()) == {10}
    assert report["finding_counts"]["error"] == 0
    assert all(count > 0 for count in report["challenge_category_distribution"].values())
    assert len(report["candidates_requiring_human_review"]) == 30
    assert report["collector_source_review"]["independent_human_review_completed"] is False
    assert report["shared_source_references"]  # Same NIST document used in two collections.
    assert report["unique_source_url_count"] < report["evidence_count"]


def test_combining_batches_rejects_cross_batch_identifier_collisions():
    with pytest.raises(ValueError, match="IDs across candidate collections"):
        review_collections([DEFAULT_CANDIDATES, DEFAULT_CANDIDATES])


def test_phase1_review_preserves_original_claims_and_excerpts_and_unknown_dates():
    current = json.loads((DEFAULT_CANDIDATES / "claim_records.json").read_text())
    before = json.loads((DEFAULT_CANDIDATES / "history" / "before_phase2_claim_records.json").read_text())
    for original, revised in zip(before, current):
        assert revised["claim_id"] == original["claim_id"]
        assert revised["claim_text"] == original["claim_text"]
        assert revised["evidence"][0]["passage"] == original["evidence"][0]["passage"]
        assert revised["evidence"][0]["publication_date"] == original["evidence"][0]["publication_date"]


def test_rendered_report_lists_supplementary_passages_and_source_limits():
    records = json.loads((DEFAULT_CANDIDATES / "claim_records.json").read_text())
    manifest = json.loads((DEFAULT_CANDIDATES / "collection_manifest.json").read_text())
    rendered = render_review(review_candidates(), records, manifest)
    for record in records:
        for evidence in record["evidence"]:
            assert evidence["source_url"] in rendered
    assert "Partial coverage only" in rendered
    assert "Publication date: unknown" in rendered
