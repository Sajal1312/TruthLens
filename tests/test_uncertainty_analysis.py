"""Synthetic uncertainty contracts and actual offline pipeline regressions."""
from copy import deepcopy
import json
from unittest.mock import Mock

import pytest

from evaluation.evaluate_uncertainty import CHALLENGE, materialize_fixture
from explainability import build_explanation
from nli_assessor import assess_evidence_nli, assess_with_optional_nli
from uncertainty_analysis import BASES, CATEGORIES, analyze_uncertainty
from verifier import assess_evidence


CASES = json.loads(CHALLENGE.read_text())["cases"]


def fixture(case_id):
    return materialize_fixture(next(case for case in CASES if case["id"] == case_id))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_authored_categories_and_primary_attribution_contract(case):
    assessment, sources, views = materialize_fixture(case)
    before = deepcopy((assessment, sources, views))
    report = analyze_uncertainty(assessment, sources, **views)
    assert set(report["categories"]) == set(case["expected_categories"])
    assert report["categories"] == [label for label in CATEGORIES if label in report["categories"]]
    assert all(finding["basis"] in BASES for finding in report["findings"])
    assert all(finding["verdict_relation"] == "additional_diagnostic_only" for finding in report["findings"])
    assert report["primary_reason"]["text"] == (assessment["reasoning"] if assessment["verdict"] == "Inconclusive" and assessment["reasoning"] else None)
    assert (assessment, sources, views) == before


@pytest.mark.parametrize("case_id, state", [
    ("u01", "no_directional_evidence_as_recorded"), ("u04", "mixed_within_component"),
    ("u07", "supporting_only_as_recorded"), ("u13", "direction_unknown"),
    ("u16", "conflict_recorded"), ("u17", "contradicting_only_as_recorded"),
])
def test_agreement_uses_effective_contributions_not_raw_labels(case_id, state):
    assessment, sources, views = fixture(case_id)
    report = analyze_uncertainty(assessment, sources, **views)
    assert report["agreement"] == state


def test_no_identified_issue_is_scoped_and_never_proves_independence():
    assessment, sources, views = fixture("u07")
    report = analyze_uncertainty(assessment, sources, **views)
    assert report["dimensions"]["numerical"] == "No identified diagnostic issue"
    assert report["dimensions"]["temporal"] == "No identified diagnostic issue"
    assert report["categories"] == ["Uncertain provenance"]
    assert "independence_not_established" in report["unknown_information"]


def test_different_component_directions_are_not_called_same_proposition_conflict():
    assessment, sources, views = fixture("u04")
    assessment["per_source"][0]["claim_part"] = "Component A"
    assessment["per_source"][1]["claim_part"] = "Component B"
    report = analyze_uncertainty(assessment, sources, **views)
    assert report["agreement"] == "mixed_across_components"
    message = next(row["message"] for row in report["findings"] if row["code"] == "directional_conflict")
    assert "not necessarily contradictions about one proposition" in message


def test_excluded_internal_conflict_does_not_become_an_accepted_vote_or_inconsistent_verdict():
    assessment, sources, views = fixture("u16")
    report = analyze_uncertainty(assessment, sources, **views)
    assert report["counts"]["supporting_records"] == 2
    assert report["counts"]["contradicting_records"] == 0
    assert report["counts"]["conflicting_records"] == 1
    assert "trace_tension" not in [finding["code"] for finding in report["findings"]]
    assert report["verdict"] == "Supported"


def test_threshold_shortfall_is_not_invented_from_a_record_count():
    assessment, sources, views = fixture("u03")
    assessment["reasoning"] = "Another unspecified issue prevented a decision."
    report = analyze_uncertainty(assessment, sources, **views)
    assert report["counts"]["supporting_records"] == 1
    assert "minimum_requirement_reported" not in [finding["code"] for finding in report["findings"]]
    assert report["primary_reason"]["text"] == assessment["reasoning"]


@pytest.mark.parametrize("missing", [None, {}, {"claim": None, "sources": None}])
def test_missing_or_malformed_diagnostic_information_is_unknown_not_clear(missing):
    assessment, sources, views = fixture("u07")
    views["numerical"] = missing
    report = analyze_uncertainty(assessment, sources, **views)
    assert report["dimensions"]["numerical"] == "Unavailable"
    assert report["counts"]["numerical_mismatch_records"] is None
    assert "diagnostic_views_unavailable" in report["unknown_information"]


def test_malformed_nested_records_are_not_silently_used():
    assessment, sources, views = fixture("u07")
    assessment["per_source"][0]["part_assessments"] = [None]
    views["numerical"]["sources"] = [None, {}]
    views["temporal"]["warnings"] = [None]
    report = analyze_uncertainty(assessment, sources, **views)
    assert not report["trace_complete"]
    assert report["dimensions"]["numerical"] == "Unavailable"
    assert report["dimensions"]["temporal"] == "Unavailable"


def test_misaligned_views_are_not_repaired_or_reported_clear():
    assessment, sources, views = fixture("u07")
    views["temporal"]["sources"] = []
    report = analyze_uncertainty(assessment, sources, **views)
    assert report["dimensions"]["temporal"] == "Unavailable"
    assert "diagnostic_views_misaligned" in report["unknown_information"]


def test_misaligned_numeric_warning_is_not_associated_with_the_current_claim():
    assessment, sources, views = fixture("u07")
    views["numerical"]["sources"] = [{"comparisons": [{"status": "potential_mismatch"}], "quantifier_warnings": []}]
    report = analyze_uncertainty(assessment, sources, **views)
    assert "Numerical ambiguity" not in report["categories"]
    assert report["counts"]["numerical_mismatch_records"] is None
    assert report["dimensions"]["numerical"] == "Unavailable"


def test_finding_and_suggestion_order_are_stable_and_input_order_of_counts_is_irrelevant():
    assessment, sources, views = fixture("u12")
    before = analyze_uncertainty(assessment, sources, **views)
    views["independence"]["counts"] = dict(reversed(list(views["independence"]["counts"].items())))
    assert analyze_uncertainty(assessment, sources, **views) == before
    assert len(before["suggestions"]) == len(set(before["suggestions"]))
    assert {row["basis"] for row in before["findings"]} == set(BASES)


def test_explanation_reuses_diagnostic_objects_once_without_search_or_model_calls(monkeypatch):
    import explainability
    import requests

    claim = "The Eiffel Tower is located in Paris."
    sources = [{"url": "https://one.example/a", "content": "The Eiffel Tower is located in Paris, France."},
               {"url": "https://two.example/b", "content": "The Eiffel Tower is located in Paris near the Champ de Mars."}]
    assessment = assess_evidence(claim, sources)
    saved = build_explanation(claim, sources, assessment)
    mocks = {}
    for name, key in (("temporal_evidence_analysis", "temporal"), ("analyze_evidence_independence", "independence"), ("analyze_numerical_evidence", "numerical")):
        mocks[name] = Mock(return_value=saved[key])
        monkeypatch.setattr(explainability, name, mocks[name])
    monkeypatch.setattr(requests, "post", lambda *_a, **_k: pytest.fail("Network forbidden"))
    before = deepcopy((assessment, sources))
    output = build_explanation(claim, sources, assessment)
    assert all(mock.call_count == 1 for mock in mocks.values())
    assert all(output[key] is saved[key] for key in ("temporal", "independence", "numerical"))
    assert output["uncertainty"]["verdict"] == "Supported"
    assert (assessment, sources) == before


@pytest.mark.parametrize("mode", ["rule", "nli", "fallback"])
def test_production_verdict_and_original_trace_are_preserved(mode):
    claim = "The Eiffel Tower is located in Paris."
    sources = [{"url": "https://one.example/a", "content": "The Eiffel Tower is located in Paris, France."},
               {"url": "https://two.example/b", "content": "The Eiffel Tower is located in Paris near the Champ de Mars."}]
    predictor = Mock(return_value={"label": "SUPPORTS", "confidence": .92, "margin": .60})
    assessment = (assess_evidence(claim, sources) if mode == "rule" else
                  assess_evidence_nli(claim, sources, predictor) if mode == "nli" else
                  assess_with_optional_nli(claim, sources, model_loader=Mock(side_effect=RuntimeError)))
    before = deepcopy((sources, assessment))
    output = build_explanation(claim, sources, assessment)
    assert output["uncertainty"]["verdict"] == assessment["verdict"] == "Supported"
    assert output["uncertainty"]["primary_reason"]["text"] is None
    assert predictor.call_count == (2 if mode == "nli" else 0)
    assert (sources, assessment) == before
    if mode == "fallback":
        assert output["uncertainty"]["agreement"] == "direction_unknown"
        assert output["uncertainty"]["counts"]["unknown_contribution_records"] == 2
        assert "Insufficient evidence" not in output["uncertainty"]["categories"]


def test_real_empty_result_path_does_not_demand_nonexistent_source_traces():
    assessment = assess_evidence("The Eiffel Tower is located in Paris.", [])
    output = build_explanation("The Eiffel Tower is located in Paris.", [], assessment)["uncertainty"]
    assert output["categories"] == ["Insufficient evidence"]
    assert output["primary_reason"]["text"] == assessment["reasoning"]
    assert output["counts"]["retrieved_entries"] == 0
