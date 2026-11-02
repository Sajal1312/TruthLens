"""Accounting and validation for the separate synthetic provenance challenge."""
from copy import deepcopy
import json

import pytest

from evaluation.evaluate_independence import (CHALLENGE, evaluate_independence_cases,
                                              main, validate_challenge)


def cases():
    return json.loads(CHALLENGE.read_text())["cases"]


def test_challenge_covers_all_categories_without_network_or_models(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "post", lambda *_a, **_k: pytest.fail("Network forbidden"))
    data = validate_challenge(cases())
    assert len(data) == 19
    report = evaluate_independence_cases(data)
    assert report["source_count"] == 40 and report["pair_count"] == 23
    assert report["network_used"] is False and report["model_used"] is False
    assert report["metrics"]["exact"]["count"] == 23
    assert "synthetic" in report["scope"]


def test_metric_denominators_include_negatives_and_empty_metrics_are_undefined():
    data = cases()[:1]
    report = evaluate_independence_cases(data)
    assert report["metrics"]["exact"]["per_class"]["detected"]["recall"] == 1.0
    assert report["metrics"]["near"]["per_class"]["detected"]["recall"] is None
    assert report["false_positive_grouping"]["rate"] is None
    assert evaluate_independence_cases([])["metrics"]["exact"]["accuracy"] is None


def test_bad_ids_missing_pair_labels_and_public_fixture_urls_are_rejected():
    data = cases()[:1]
    with pytest.raises(ValueError, match="duplicate"):
        validate_challenge(data + data)
    missing = deepcopy(data)
    missing[0]["pairs"] = []
    with pytest.raises(ValueError, match="Every source pair"):
        validate_challenge(missing)
    missing = deepcopy(data)
    missing[0]["pairs"][0]["near"] = None
    with pytest.raises(ValueError, match="booleans"):
        validate_challenge(missing)
    data[0]["sources"][0]["url"] = "https://realpublisher.com/fabricated-article"
    with pytest.raises(ValueError, match="reserved"):
        validate_challenge(data)


def test_false_positive_grouping_is_counted_without_hiding_errors(monkeypatch):
    import evaluation.evaluate_independence as runner
    data = [cases()[6]]  # Unknown provenance, expected no grouping.
    monkeypatch.setattr(runner, "analyze_evidence_independence", lambda _sources: {
        "relationships": [{"left": 0, "right": 1, "exact_duplicate": False,
                           "near_duplicate": False, "explicit_dependency": False,
                           "category": "Possible dependency", "signals": []}],
        "groups": [{"members": [0, 1], "reason": "Deliberately wrong test grouping"}]})
    report = evaluate_independence_cases(data)
    assert report["false_positive_grouping"] == {"false_grouped_pairs": 1, "gold_ungrouped_pairs": 1, "rate": 1.0}


def test_report_refuses_overwrite(tmp_path):
    path = tmp_path / "original.json"
    path.write_text("Preserve original")
    with pytest.raises(FileExistsError):
        main(["--output", str(path)])
    assert path.read_text() == "Preserve original"
