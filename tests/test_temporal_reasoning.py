"""Synthetic temporal diagnostics: no model, real source claims or network."""
from copy import deepcopy
from datetime import date

import pytest

from explainability import build_explanation
from temporal_reasoning import (classify_temporal_context, extract_temporal_expressions,
                                parse_temporal_date, temporal_evidence_analysis)


REFERENCE = "2026-11-02"


def analyze(claim, text, **metadata):
    return temporal_evidence_analysis(claim, [{"content": text, **metadata}], REFERENCE)


def codes(analysis):
    return {warning["code"] for warning in analysis["warnings"]}


def test_historical_event_has_precise_date_and_matching_event_context():
    result = analyze("Demo Lab opened on 30 April 1993.", "Demo Lab opened on 30 April 1993.",
                     published_date="2026-01-01", event_date="1993-04-30")
    assert result["claim"]["classification"] == "historical"
    assert result["claim"]["expressions"][0]["start_date"] == "1993-04-30"
    assert "different_time_period" not in codes(result)


def test_old_current_status_evidence_has_cautious_warning():
    result = analyze("Ari is currently the director.", "Ari was the director in 2019.", published_date="2019-06-01")
    assert result["claim"]["classification"] == "current_status"
    assert "historical_evidence_for_current" in codes(result)


@pytest.mark.parametrize("claim", ["The Earth revolves around the Sun.", "A triangle has three sides.",
                                   "Electric current flows through a conductor."])
def test_present_tense_alone_does_not_make_science_time_sensitive(claim):
    result = analyze(claim, claim, published_date="2001-01-01")
    assert result["claim"]["classification"] == "timeless_candidate"
    assert not any(warning["severity"] == "warning" for warning in result["warnings"])


def test_future_plan_does_not_confirm_an_outcome():
    result = analyze("Demo Lab will launch a probe in 2030.", "Demo Lab plans to launch a probe in 2030.", published_date="2025-01-01")
    assert result["claim"]["classification"] == "future"
    assert "prediction_not_confirmed_outcome" in codes(result)
    assert "publication_predates_claim_period" in codes(result)


@pytest.mark.parametrize("phrase, reference, start, end", [
    ("today", REFERENCE, "2026-11-02", "2026-11-02"),
    ("last year", REFERENCE, "2025-01-01", "2025-12-31"),
    ("next year", REFERENCE, "2027-01-01", "2027-12-31"),
    ("last month", "2024-03-01", "2024-02-01", "2024-02-29"),
    ("next month", "2026-12-30", "2027-01-01", "2027-01-31"),
    ("last week", REFERENCE, "2026-10-26", "2026-11-01"),
    ("yesterday", "2026-01-01", "2025-12-31", "2025-12-31"),
])
def test_relative_calendar_intervals_require_supplied_reference(phrase, reference, start, end):
    row = extract_temporal_expressions(phrase, reference)[0]
    assert (row["start_date"], row["end_date"]) == (start, end)
    assert extract_temporal_expressions(phrase)[0]["status"] == "unresolved"


@pytest.mark.parametrize("phrase", ["recently", "soon", "last winter", "a while ago"])
def test_vague_or_hemisphere_dependent_expressions_remain_unresolved(phrase):
    row = extract_temporal_expressions(phrase, REFERENCE)[0]
    assert row["status"] == "unresolved" and row["start_date"] is None


def test_unknown_publication_does_not_become_event_date_or_mismatch():
    result = analyze("Demo Lab opened in 2018.", "Demo Lab opened in 2018.")
    dates = result["sources"][0]["metadata"]
    assert dates["publication_date"]["status"] == "missing"
    assert dates["event_date"]["status"] == "missing"
    assert "publication_date_missing" in codes(result)
    assert "different_time_period" not in codes(result)


def test_publication_and_update_mentions_do_not_mask_old_event_year():
    result = analyze("Demo Lab opened in 2025.", "Published 2025; updated 2026; Demo Lab opened in 2019.",
                     published_date="2025-01-01", updated_date="2026-01-01")
    assert "different_time_period" in codes(result)
    assert result["sources"][0]["comparison_periods"] == [("2019-01-01", "2019-12-31")]
    roles = [row["role"] for row in result["sources"][0]["context"]["expressions"]]
    assert roles == ["publication_mention", "update_mention", "date_mention"]


def test_updated_page_does_not_make_underlying_evidence_current():
    result = analyze("Demo Lab currently employs 100 researchers.", "Demo Lab employed 100 researchers in 2019.",
                     published_date="2019-06-01", updated_date="2026-10-01")
    assert "historical_evidence_for_current" in codes(result)
    assert result["sources"][0]["metadata"]["updated_date"]["start_date"] == "2026-10-01"


def test_different_source_years_are_reported_as_possible_period_conflict():
    result = temporal_evidence_analysis("Demo Lab opened in 2020.", [
        {"content": "Demo Lab opened in 2019."}, {"content": "Demo Lab opened in 2020."}], REFERENCE)
    assert "mixed_evidence_periods" in codes(result)
    assert "different_time_period" in {row["code"] for row in result["sources"][0]["warnings"]}
    assert "different_time_period" not in {row["code"] for row in result["sources"][1]["warnings"]}


@pytest.mark.parametrize("value, status", [
    ("2025-02-30", "invalid"), ("2026-13-01", "invalid"),
    ("03/04/2025", "ambiguous"), ("not-a-date", "invalid"),
    ({"year": 2025}, "invalid"), (None, "missing"),
])
def test_malformed_and_ambiguous_dates_are_not_repaired(value, status):
    row = parse_temporal_date(value)
    assert row["status"] == status
    assert row["start_date"] is None


def test_invalid_full_date_is_not_reextracted_as_a_valid_year():
    rows = extract_temporal_expressions("Opened on 2025-02-30.", REFERENCE)
    assert len(rows) == 1
    assert rows[0]["text"] == "2025-02-30" and rows[0]["status"] == "invalid"


@pytest.mark.parametrize("value, precision, start, end", [
    ("June 2022", "month", "2022-06-01", "2022-06-30"),
    ("2024-02", "month", "2024-02-01", "2024-02-29"),
    ("2025", "year", "2025-01-01", "2025-12-31"),
    ("2010–2012", "year_range", "2010-01-01", "2012-12-31"),
    ("April 30, 1993", "day", "1993-04-30", "1993-04-30"),
    ("2026-11-02T08:30:00Z", "day", "2026-11-02", "2026-11-02"),
])
def test_partial_dates_keep_precision_and_timestamps_keep_their_date(value, precision, start, end):
    result = parse_temporal_date(value)
    assert result["precision"] == precision
    assert (result["start_date"], result["end_date"]) == (start, end)


def test_source_relative_expression_is_not_anchored_by_retrieval_or_publication():
    result = analyze("Demo Lab is open today.", "Demo Lab opened today.",
                     published_date=REFERENCE, retrieved_at=REFERENCE + "T10:00:00Z")
    source_expression = result["sources"][0]["context"]["expressions"][0]
    assert source_expression["status"] == "unresolved"
    assert result["claim"]["expressions"][0]["status"] == "resolved"
    anchored = analyze("Demo Lab is open today.", "Demo Lab opened today.", temporal_reference_date=REFERENCE)
    assert anchored["sources"][0]["context"]["expressions"][0]["start_date"] == REFERENCE


def test_current_context_without_reference_stays_unresolved():
    result = classify_temporal_context("Ari is the CEO of Demo Lab.")
    assert result["classification"] == "current_status" and result["unresolved"]
    assert classify_temporal_context("It happened last year.", "2026")["unresolved"] == ["last year"]


def test_current_assertion_with_historical_background_is_not_automatically_stale():
    result = analyze("Ari is the CEO of Demo Lab.", "In 2026, Ari is the CEO; Ari was appointed in 2020.")
    assert "historical_evidence_for_current" not in codes(result)


def test_temporal_integration_preserves_assessment_and_original_evidence():
    assessment = {"original_claim": "Demo Lab currently employs 100 researchers.",
                  "verdict": "Supported", "reasoning": "Existing recorded aggregation reason"}
    results = [{"content": "Demo Lab employed 100 researchers in 2019.", "published_date": "2026-01-01"}]
    before = deepcopy((results, assessment))
    explanation = build_explanation(assessment["original_claim"], results, assessment, reference_date=date(2026, 11, 2))
    assert explanation["verdict"] == "Supported"
    assert explanation["reasoning"] == assessment["reasoning"]
    assert "historical_evidence_for_current" in codes(explanation["temporal"])
    assert (results, assessment) == before
