"""Measurement accounting and synthetic challenge validation, without holdout I/O."""
import json

import pytest

from evaluation.evaluate_temporal import CHALLENGE, evaluate_temporal_cases, main, validate_challenge


def test_temporal_evaluation_metrics_have_explicit_denominators_and_no_network(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "post", lambda *_args, **_kwargs: pytest.fail("Network forbidden"))
    cases = [{"id": "synthetic", "category": "timeless", "claim": "A triangle has three sides.",
              "reference_date": "2026-11-02", "expected_classification": "timeless_candidate",
              "expected_expressions": [], "rationale": "Constructed geometry fixture",
              "evidence": [{"content": "A triangle has three sides.", "expected_mismatch": False}]}]
    report = evaluate_temporal_cases(cases)
    assert report["classification"]["accuracy"] == 1.0
    assert report["classification"]["per_class"]["future"]["support"] == 0
    assert report["classification"]["per_class"]["future"]["recall"] is None
    assert report["expression_detection"]["precision"] is None
    assert report["expression_detection"]["recall"] is None
    assert report["mismatch_detection"]["count"] == 1
    assert report["timeless_warning_rate"]["rate"] == 0
    assert report["network_used"] is False and report["model_used"] is False


def test_temporal_expression_false_positives_are_counted_and_not_hidden(monkeypatch):
    # Inject a wrong diagnostic so the metric test does not require a particular
    # extraction failure to remain in the implementation.
    import evaluation.evaluate_temporal as runner
    monkeypatch.setattr(runner, "temporal_evidence_analysis", lambda *_args: {
        "claim": {"classification": "explicit", "expressions": [{"text": "2020"}], "unresolved": []},
        "sources": [], "warnings": []})
    case = {"id": "quantity", "category": "numeric_ambiguity", "claim": "The array contains 2020 samples.",
            "reference_date": "2026-11-02", "expected_classification": "timeless_candidate",
            "expected_expressions": [], "rationale": "Quantity, not a calendar year", "evidence": []}
    report = evaluate_temporal_cases([case])
    assert report["expression_detection"]["fp"] == 1
    assert report["classification"]["accuracy"] == 0


def test_challenge_is_separate_synthetic_data_and_validates_all_records():
    bundle = json.loads(CHALLENGE.read_text())
    assert "synthetic" in bundle["purpose"]
    cases = validate_challenge(bundle["cases"])
    assert len(cases) == 25
    assert len({case["id"] for case in cases}) == 25
    assert all(not source.get("url") for case in cases for source in case["evidence"])
    report = evaluate_temporal_cases(cases)
    assert report["claim_count"] == 25 and report["evidence_count"] == 26
    assert report["classification"]["count"] == 25
    for case in report["cases"]:
        if case["expected_global_codes"] is not None:
            assert case["global_codes"] == case["expected_global_codes"]


def test_duplicate_ids_missing_labels_and_invented_public_citations_rejected():
    cases = json.loads(CHALLENGE.read_text())["cases"][:1]
    with pytest.raises(ValueError, match="duplicate"):
        validate_challenge(cases + cases)
    del cases[0]["evidence"][0]["expected_mismatch"]
    with pytest.raises(ValueError, match="mismatch"):
        validate_challenge(cases)
    cases[0]["evidence"][0].update(expected_mismatch=False, url="https://fake.example/pretend-citation")
    with pytest.raises(ValueError, match="citation"):
        validate_challenge(cases)


def test_evaluation_report_refuses_to_overwrite_existing_file(tmp_path):
    output = tmp_path / "report.json"
    output.write_text("Keep original report")
    with pytest.raises(FileExistsError):
        main(["--output", str(output)])
    assert output.read_text() == "Keep original report"
