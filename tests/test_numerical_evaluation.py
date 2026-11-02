"""Numerical challenge accounting, not an independent accuracy benchmark."""
from copy import deepcopy
import json

import pytest

from evaluation.evaluate_numerical import CHALLENGE, evaluate_numerical_cases, main, validate_challenge


def bundle():
    return json.loads(CHALLENGE.read_text())


def test_separate_synthetic_challenge_has_explicit_comparison_counts_and_no_network(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "post", lambda *_a, **_k: pytest.fail("Network forbidden"))
    data = bundle()
    validate_challenge(data["cases"])
    report = evaluate_numerical_cases(data["cases"], data["reference_date"])
    assert report["case_count"] == 36 and report["comparison_count"] == 38
    assert report["network_used"] is False and report["model_used"] is False
    assert report["comparison_metrics"]["count"] == 38
    assert report["unresolved_count"] > 0
    assert report["resolved_coverage"] + report["unresolved_rate"] == 1.0


def test_undefined_metrics_and_single_class_support_are_explicit():
    case = bundle()["cases"][:1]
    report = evaluate_numerical_cases(case)
    assert report["comparison_metrics"]["per_class"]["potential_mismatch"]["recall"] is None
    assert evaluate_numerical_cases([])["resolved_coverage"] is None
    assert evaluate_numerical_cases([])["quantity_extraction"]["precision"] is None


def test_unresolved_predictions_are_retained_in_mismatch_recall_denominator(monkeypatch):
    import evaluation.evaluate_numerical as runner
    data = bundle()["cases"][1:2]
    monkeypatch.setattr(runner, "analyze_numerical_evidence", lambda *_a: {
        "claim": {"quantities": [], "dates": [], "quantifiers": []},
        "sources": [{"extracted": {"quantities": []}, "comparisons": [], "quantifier_warnings": []}]})
    report = evaluate_numerical_cases(data)
    assert report["comparison_metrics"]["per_class"]["potential_mismatch"]["recall"] == 0
    assert report["unresolved_count"] == 1
    assert report["cases"][0]["missing_comparison_mapped_to_abstention"] == [True]


def test_bad_ids_labels_and_public_citations_rejected():
    data = bundle()["cases"][:1]
    with pytest.raises(ValueError, match="duplicate"):
        validate_challenge(data + data)
    bad = deepcopy(data)
    bad[0]["expected_statuses"] = ["Supported"]
    with pytest.raises(ValueError, match="comparison labels"):
        validate_challenge(bad)
    data[0]["evidence"]["url"] = "https://publisher.example/pretend-citation"
    with pytest.raises(ValueError, match="citations"):
        validate_challenge(data)


def test_report_refuses_overwrite(tmp_path):
    path = tmp_path / "original.json"
    path.write_text("Original report")
    with pytest.raises(FileExistsError):
        main(["--output", str(path)])
    assert path.read_text() == "Original report"
