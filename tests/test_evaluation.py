"""Offline tests for the evaluation data contract, metrics, and no-search adapter."""
import json
from pathlib import Path

import pytest

from evaluation.metrics import classification_metrics, selective_metrics
from evaluation.run_evaluation import DATA_DIR, evaluate_cases, load_cases, validate_cases


def test_metrics_report_fixed_confusion_matrix_and_macro_f1():
    result = classification_metrics(["yes", "no", "no"], ["yes", "yes", "no"], ("yes", "no"))
    assert result["confusion_matrix"] == {"yes": {"yes": 1, "no": 0}, "no": {"yes": 1, "no": 1}}
    assert result["per_class"]["yes"]["precision"] == 0.5
    assert result["per_class"]["no"]["recall"] == 0.5
    assert result["macro_f1"] == pytest.approx(2 / 3)


def test_selective_metrics_make_abstention_denominator_explicit():
    result = selective_metrics(["SUPPORTED", "CONTRADICTED", "INCONCLUSIVE"],
                               ["SUPPORTED", "INCONCLUSIVE", "INCONCLUSIVE"])
    assert result == {"count": 3, "selective_count": 1, "selective_accuracy": 1.0,
                      "coverage": pytest.approx(1 / 3), "abstention_rate": pytest.approx(2 / 3)}


@pytest.mark.parametrize("filename, expected_count", [("development.jsonl", 9), ("diagnostics.jsonl", 16), ("held_out.jsonl", 3)])
def test_dataset_loads_and_declares_expected_counts(filename, expected_count):
    cases = load_cases(DATA_DIR / filename)
    assert len(cases) == expected_count
    assert all(case["split"] == filename.removesuffix(".jsonl") for case in cases)


def test_directional_gold_case_requires_two_urls_but_not_assumed_independence():
    case = load_cases(DATA_DIR / "held_out.jsonl")[0]
    case["evidence"][1]["source"]["publisher_id"] = case["evidence"][0]["source"]["publisher_id"]
    validate_cases([case])
    case["evidence"][1]["source"]["url"] = case["evidence"][0]["source"]["url"]
    with pytest.raises(ValueError, match="two distinct public URLs"):
        validate_cases([case])


def test_evaluator_uses_fixed_evidence_and_never_calls_search(monkeypatch):
    import requests

    def forbidden(*_args, **_kwargs):
        raise AssertionError("offline evaluation must not invoke Tavily")

    monkeypatch.setattr(requests, "post", forbidden)
    cases = load_cases(DATA_DIR / "development.jsonl")[:1]
    report = evaluate_cases(cases, lambda premise, hypothesis: {
        "label": "SUPPORTS", "confidence": 0.95, "margin": 0.60,
        "scores": {"SUPPORTS": 0.95, "CONTRADICTS": 0.02, "NOT ENOUGH INFORMATION": 0.03}})
    assert report["network_search_used"] is False
    assert report["case_count"] == 1
    assert report["cases"][0]["actual_final_verdict"] == "SUPPORTED"
    assert report["semantic_interpretation_comparison"]["experimental_semantic"]["verdict_metrics"]["count"] == 1


def test_evaluation_report_is_reproducible_for_fixed_predictor():
    cases = load_cases(DATA_DIR / "development.jsonl")[:2]
    predictor = lambda _premise, _hypothesis: {
        "label": "SUPPORTS", "confidence": 0.95, "margin": 0.60}
    first = evaluate_cases(cases, predictor)
    second = evaluate_cases(cases, predictor)
    assert first["metrics"] == second["metrics"]
    assert first["aggregation_comparison"] == second["aggregation_comparison"]
    assert first["cases"] == second["cases"]
    assert first["assessment_thresholds"] == {
        "confidence": 0.70, "margin": 0.15, "directional_sources": 2}


def test_same_publisher_concentration_is_reported_without_changing_verdict():
    cases = load_cases(DATA_DIR / "development.jsonl")[:1]
    case = cases[0]
    case["evidence"][1]["source"]["publisher_id"] = case["evidence"][0]["source"]["publisher_id"]
    report = evaluate_cases(cases, lambda _premise, _hypothesis: {
        "label": "SUPPORTS", "confidence": 0.95, "margin": 0.60})

    assert report["cases"][0]["actual_final_verdict"] == "SUPPORTED"
    diversity = report["cases"][0]["source_diversity"]
    assert diversity["distinct_declared_publishers"] == 1
    assert diversity["largest_publisher_share"] == 1.0
    assert diversity["independence_verified"] is False
    comparison = report["cases"][0]["experimental_verdicts"]
    assert comparison["publisher_cap"]["verdict"] == "INCONCLUSIVE"
    assert comparison["distinct_publishers"]["verdict"] == "INCONCLUSIVE"
    assert report["aggregation_comparison"]["production_default"]["verdict_metrics"]["accuracy"] == 1.0


def test_missing_or_malformed_publisher_metadata_is_conservative():
    case = load_cases(DATA_DIR / "development.jsonl")[0]
    for evidence in case["evidence"]:
        evidence["source"]["publisher_id"] = {"unexpected": "shape"}
    report = evaluate_cases([case], lambda _premise, _hypothesis: {
        "label": "SUPPORTS", "confidence": 0.95, "margin": 0.60})
    experimental = report["cases"][0]["experimental_verdicts"]
    assert experimental["publisher_cap"]["verdict"] == "INCONCLUSIVE"
    assert experimental["distinct_publishers"]["verdict"] == "INCONCLUSIVE"
    assert "independence" in experimental["publisher_cap"]["note"]


def test_duplicate_urls_keep_passage_diagnostics_aligned_by_input_order():
    case = load_cases(DATA_DIR / "development.jsonl")[0]
    case["evidence"][1]["source"]["url"] = case["evidence"][0]["source"]["url"]

    report = evaluate_cases([case], lambda _premise, _hypothesis: {
        "label": "SUPPORTS", "confidence": 0.96, "margin": 0.70})
    rows = report["cases"][0]["evidence"]
    for annotated, output in zip(case["evidence"], rows):
        assert output["passage_normalized"] == annotated["passage"].casefold()


def test_metrics_exclude_absent_gold_classes_and_expose_undefined_values():
    result = classification_metrics(["yes"], ["yes"], ("yes", "no"))
    assert result["macro_f1"] == 1.0
    assert result["macro_f1_class_count"] == 1
    assert result["macro_f1_labels"] == ["yes"]
    assert result["per_class"]["no"] == {
        "support": 0, "precision": None, "recall": None, "f1": None}


def test_metrics_report_unavailable_macro_for_empty_data():
    result = classification_metrics([], [], ("yes", "no"))
    assert result["accuracy"] is None
    assert result["macro_f1"] is None
    assert result["macro_f1_class_count"] == 0


def test_synthetic_sources_have_no_public_citation_url():
    for file in ("development.jsonl", "diagnostics.jsonl", "held_out.jsonl"):
        for case in load_cases(DATA_DIR / file):
            for evidence in case["evidence"]:
                if evidence["source"]["kind"] == "synthetic_fixture":
                    assert evidence["source"]["url"] is None
