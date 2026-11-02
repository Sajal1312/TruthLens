"""Follow-up assistance stays separate from actual approvals and candidate data."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from evaluation.annotation.candidate_review import candidate_checksum, load_candidates
from evaluation.annotation.review_followup import render_sheet, summarize, validate_followup
from evaluation.annotation.validate_pilot import _validate_schema


ROOT = Path(__file__).parents[1]
BASE = ROOT / "evaluation/annotation/candidate_reviews/automated_assistance"


def inputs():
    # Only public staged candidates/assistance, never held-out annotations.
    candidates = load_candidates()
    previous = json.loads((BASE / "2026-11-01/assessments.json").read_text())
    bundle = json.loads((BASE / "2026-11-02/followup.json").read_text())
    return bundle, candidates, previous


def test_all_30_exact_claims_and_blank_human_decision_spaces():
    bundle, candidates, previous = inputs()
    before = deepcopy((bundle, candidates, previous))
    sheet = render_sheet(bundle, candidates, previous)
    assert sheet.count("**Human decision (leave blank until you decide):** ____________________") == 30
    assert sheet.count("**Human rationale / required revisions:**") == 30
    for cid, candidate in candidates.items():
        assert "## " + cid + "\n" in sheet
        assert "**Exact claim:** " + candidate["claim_text"] in sheet
        assert candidate_checksum(candidate) in sheet
        for evidence in candidate["evidence"]:
            assert evidence["evidence_id"] in sheet and evidence["source_url"] in sheet
    assert (bundle, candidates, previous) == before
    assert "not a submittable review packet" in sheet


def test_counts_separate_resolved_context_from_unchanged_candidates():
    bundle, candidates, previous = inputs()
    summary = summarize(bundle, candidates, previous)
    assert summary["followup_issue_counts"] == {
        "resolved_context_gap": 4, "authoritative_replacement_available": 1, "unresolved": 4}
    assert summary["unknown_publication_dates_checked"] == 27
    assert summary["new_original_publication_days_established"] == 0
    assert summary["updated_preliminary_routes"]["review_current_candidate"] == 21
    assert summary["source_access"] == {"opened": 37, "inaccessible": 4}


@pytest.mark.parametrize("mutation", ["missing_note", "duplicate_note", "duplicate_check", "wrong_reference", "missing_date", "duplicate_date", "wrong_date_source"])
def test_missing_duplicate_and_inconsistent_references_are_rejected(mutation):
    bundle, candidates, previous = inputs()
    if mutation == "missing_note":
        bundle["candidate_followups"].pop()
    elif mutation == "duplicate_note":
        bundle["candidate_followups"].append(deepcopy(bundle["candidate_followups"][0]))
    elif mutation == "duplicate_check":
        bundle["source_checks"].append(deepcopy(bundle["source_checks"][0]))
    elif mutation == "wrong_reference":
        bundle["candidate_followups"][0]["source_check_ids"] = ["unknown-source"]
    elif mutation == "missing_date":
        bundle["missing_date_checks"].pop()
    elif mutation == "duplicate_date":
        bundle["missing_date_checks"].append(deepcopy(bundle["missing_date_checks"][0]))
    else:
        bundle["missing_date_checks"][0]["source_check_id"] = bundle["source_checks"][-1]["check_id"]
    with pytest.raises(ValueError):
        validate_followup(bundle, candidates, previous)


def test_stale_context_version_and_fabricated_day_are_rejected():
    bundle, candidates, previous = inputs()
    bad = deepcopy(bundle)
    bad["candidate_followups"][0]["candidate_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Stale"):
        validate_followup(bad, candidates, previous)
    bad = deepcopy(bundle)
    month = next(row for row in bad["source_checks"] if row["publication_precision"] == "month")
    month["publication_date"] = "2026-01-01"
    with pytest.raises(ValueError, match="publication day"):
        validate_followup(bad, candidates, previous)
    bad = deepcopy(bundle)
    blocked = next(row for row in bad["source_checks"] if row["access_status"] == "inaccessible")
    blocked.update(publication_precision="day", publication_date="2026-01-01")
    with pytest.raises(ValueError, match="Inaccessible"):
        validate_followup(bad, candidates, previous)


def test_followup_cannot_contain_human_decisions_or_gold_labels():
    bundle, candidates, previous = inputs()
    for field in ("decision", "reviewer_alias", "review_timestamp", "gold_verdict"):
        bad = deepcopy(bundle)
        bad["candidate_followups"][0][field] = "not allowed"
        with pytest.raises(ValueError):
            validate_followup(bad, candidates, previous)
    with pytest.raises(ValueError):
        _validate_schema(bundle, "candidate_review.schema.json", "not a human review")


def test_cli_never_overwrites_existing_output(tmp_path):
    output = tmp_path / "prepared"
    output.mkdir()
    sentinel = output / "human_review_sheet.md"
    sentinel.write_text("Synthetic existing human scratch notes. Must not be overwritten.")
    result = subprocess.run([
        sys.executable, "-m", "evaluation.annotation.review_followup",
        "--followup", str(BASE / "2026-11-02/followup.json"),
        "--previous", str(BASE / "2026-11-01/assessments.json"),
        "--output-dir", str(output)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 1
    assert "File exists" in result.stderr
    assert sentinel.read_text() == "Synthetic existing human scratch notes. Must not be overwritten."
    assert not (output / "summary.json").exists()
