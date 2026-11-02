"""Evaluation accounting for synthetic uncertainty snapshots, not human labels."""
from copy import deepcopy
import json

import pytest

from evaluation.evaluate_uncertainty import (CHALLENGE, attribution_contract_violations,
                                            evaluate_uncertainty_cases, main, materialize_fixture, validate_challenge)
from uncertainty_analysis import analyze_uncertainty


def cases():
    return json.loads(CHALLENGE.read_text())["cases"]


def test_snapshot_evaluation_is_offline_and_reports_absent_labels(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "post", lambda *_a, **_k: pytest.fail("Network forbidden"))
    report = evaluate_uncertainty_cases(cases())
    assert report["case_count"] == 24 and report["source_count"] == 37
    assert report["network_used"] is False and report["upstream_diagnostics_recomputed"] is False
    assert report["absent_gold_categories"] == ["No identified diagnostic issue"]
    assert report["category_metrics"]["No identified diagnostic issue"]["recall"] is None
    assert len(report["macro_labels"]) == 6
    assert report["missing_information_detection"]["support"] == 5


def test_empty_metrics_and_missing_case_support_are_undefined():
    report = evaluate_uncertainty_cases([])
    assert report["macro_f1"] is None
    assert report["exact_label_set_accuracy"] is None
    assert report["incorrect_attribution_contract"]["rate"] is None


def test_false_positive_categories_are_counted_not_hidden(monkeypatch):
    import evaluation.evaluate_uncertainty as runner
    original = runner.analyze_uncertainty

    def extra_warning(*args, **kwargs):
        report = original(*args, **kwargs)
        report["categories"].append("Numerical ambiguity")
        return report

    monkeypatch.setattr(runner, "analyze_uncertainty", extra_warning)
    report = evaluate_uncertainty_cases(cases()[:1])
    assert report["category_metrics"]["Numerical ambiguity"]["fp"] == 1
    assert report["micro_all_categories"]["fp"] == 1
    assert report["exact_label_set_accuracy"] == 0


def test_invented_primary_causes_are_detected_even_when_categories_match():
    assessment, sources, views = materialize_fixture(cases()[9])  # Supported plus numerical warning.
    report = analyze_uncertainty(assessment, sources, **views)
    report["primary_reason"] = {"text": "The numerical warning caused the verdict", "origin": "recorded_explanation"}
    assert attribution_contract_violations(report, assessment)
    report["primary_reason"]["text"] = None
    report["findings"][0]["verdict_relation"] = "caused_verdict"
    assert attribution_contract_violations(report, assessment)


def test_duplicate_ids_invalid_labels_and_missing_required_fields_rejected():
    data = cases()[:1]
    with pytest.raises(ValueError, match="duplicate"):
        validate_challenge(data + data)
    malformed = deepcopy(data)
    malformed[0]["expected_categories"] = ["Proven true"]
    with pytest.raises(ValueError, match="category labels"):
        validate_challenge(malformed)
    del malformed[0]["expected_information_gap"]
    with pytest.raises(ValueError, match="Missing"):
        validate_challenge(malformed)


def test_report_refuses_overwrite(tmp_path):
    path = tmp_path / "report.json"
    path.write_text("Preserve existing report")
    with pytest.raises(FileExistsError):
        main(["--output", str(path)])
    assert path.read_text() == "Preserve existing report"
