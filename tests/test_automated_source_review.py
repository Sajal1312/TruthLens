"""Offline assistance safeguards; synthetic records never enter the real pilot."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from evaluation.annotation.automated_source_review import (
    render_report, summarize, validate_assessments, write_reports,
)
from evaluation.annotation.candidate_review import candidate_checksum, load_candidates
from evaluation.annotation.validate_pilot import _validate_schema


def fixture():
    candidate = {"claim_id": "synthetic-assistance-001", "claim_text": "Synthetic claim, not real evidence.",
                 "evidence": [{"evidence_id": "synthetic-e01", "source_url": "https://example.test/source",
                               "publication_date": None}]}
    row = {
        "schema_version": "1.0.0", "record_type": "automated_preliminary_assessment",
        "automated_checked_on": "2026-11-01", "method": "web_tool_rendered_source_inspection",
        "candidate_id": candidate["claim_id"], "candidate_sha256": candidate_checksum(candidate),
        "claim": candidate["claim_text"], "human_review_priority": "routine",
        "claim_clarity_assessment": "Synthetic scope note.",
        "claim_evidence_interpretation": "Synthetic fixture; no real web check.",
        "date_assessment": "Unknown synthetic date.", "provenance_assessment": "Unknown synthetic origin.",
        "research_concerns": ["Synthetic workflow fixture only."],
        "recommended_action": "suitable for human approval", "recommendation_reason": "Synthetic recommendation.",
        "evidence_checks": [{"evidence_id": "synthetic-e01", "source_url": "https://example.test/source",
            "access_status": "opened", "excerpt_match": "exact_fragment", "observed_title": "Synthetic source",
            "observed_publisher": "Synthetic publisher", "source_role": "Synthetic fixture",
            "locator": "Synthetic paragraph", "publication_date_status": "publication_day_not_established",
            "observed_publication_date": None, "other_date_notes": "No original day in fixture.",
            "context_notes": "Not an actual source verification."}],
    }
    return [row], {candidate["claim_id"]: candidate}


def test_assistance_is_not_a_submittable_human_review():
    rows, candidates = fixture()
    validate_assessments(rows, candidates)
    with pytest.raises(ValueError):
        _validate_schema(rows[0], "candidate_review.schema.json", "not a human decision")
    for field in ("decision", "reviewer_alias", "review_timestamp", "gold_verdict"):
        invalid = deepcopy(rows)
        invalid[0][field] = "not permitted"
        with pytest.raises(ValueError):
            validate_assessments(invalid, candidates)


@pytest.mark.parametrize("change", ["claim", "evidence", "url"])
def test_stale_candidate_versions_fail(change):
    rows, candidates = fixture()
    candidate = next(iter(candidates.values()))
    if change == "claim":
        candidate["claim_text"] += " revised"
    elif change == "evidence":
        candidate["evidence"][0]["passage"] = "Changed synthetic passage"
    else:
        candidate["evidence"][0]["source_url"] += "/revised"
    with pytest.raises(ValueError, match="Stale"):
        validate_assessments(rows, candidates)


def test_missing_duplicate_and_unknown_coverage_rejected():
    rows, candidates = fixture()
    for invalid in ([], rows + rows):
        with pytest.raises(ValueError):
            validate_assessments(invalid, candidates)
    for mode in ("missing", "duplicate", "unknown"):
        invalid = deepcopy(rows)
        if mode == "missing":
            invalid[0]["evidence_checks"] = []
        elif mode == "duplicate":
            invalid[0]["evidence_checks"] *= 2
        else:
            invalid[0]["evidence_checks"][0]["evidence_id"] = "unknown-evidence"
        with pytest.raises(ValueError):
            validate_assessments(invalid, candidates)


def test_inaccessible_source_cannot_be_counted_as_verified():
    rows, candidates = fixture()
    check = rows[0]["evidence_checks"][0]
    check["access_status"] = "inaccessible"
    with pytest.raises(ValueError, match="Inaccessible"):
        validate_assessments(rows, candidates)
    check.update(excerpt_match="incomplete", observed_title=None, observed_publisher=None,
                 publication_date_status="incomplete")
    with pytest.raises(ValueError, match="requires human attention"):
        validate_assessments(rows, candidates)
    rows[0]["recommended_action"] = "needs revision"
    result = summarize(rows, candidates)
    assert result["passages_located"] == result["distinct_sources_opened"] == 0
    assert result["candidates_with_inaccessible_sources"] == [rows[0]["candidate_id"]]


def test_url_and_publication_date_cannot_be_silently_repaired():
    rows, candidates = fixture()
    invalid = deepcopy(rows)
    invalid[0]["evidence_checks"][0]["source_url"] += "/different"
    with pytest.raises(ValueError, match="Source URL"):
        validate_assessments(invalid, candidates)
    check = rows[0]["evidence_checks"][0]
    check.update(publication_date_status="matched_existing_date", observed_publication_date="2025-01-01")
    with pytest.raises(ValueError, match="Publication date"):
        validate_assessments(rows, candidates)
    next(iter(candidates.values()))["evidence"][0]["publication_date"] = "2025-01-01"
    rows[0]["candidate_sha256"] = candidate_checksum(next(iter(candidates.values())))
    validate_assessments(rows, candidates)


def test_exclusive_outputs_preserve_inputs_and_existing_files(tmp_path):
    rows, candidates = fixture()
    before = deepcopy((rows, candidates))
    output = tmp_path / "assistance"
    write_reports(rows, candidates, output)
    original = {str(p): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    with pytest.raises(FileExistsError):
        write_reports(rows, candidates, output)
    assert original == {str(p): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert (rows, candidates) == before
    assert "not independent human review" in render_report(rows, candidates)


def test_saved_assistance_covers_current_candidates_without_approving_them():
    root = Path(__file__).parents[1] / "evaluation/annotation"
    rows = json.loads((root / "candidate_reviews/automated_assistance/2026-11-01/assessments.json").read_text())
    result = summarize(rows, load_candidates())
    assert result["candidate_count"] == 30
    assert result["evidence_count"] == 38
    assert result["distinct_sources_opened"] == 36
    assert result["passages_located"] == 37
    assert all("decision" not in row and "gold_verdict" not in row for row in rows)
