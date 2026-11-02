"""Comparison accounting tests; only explicit permitted fixtures, no held-out data."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from evaluation import compare_systems as comparison
from explainability import build_explanation
from verifier import assess_evidence


def synthetic_case(label="INCONCLUSIVE"):
    return {"case_id": "unit-only", "split": "diagnostics", "claim": "Demo Lab has 10 instruments.",
            "expected_final_verdict": label, "tags": ["synthetic_unit_test"],
            "evidence": [{"evidence_id": "unit-e1", "passage": "Demo Lab has 10 instruments.",
                          "source": {"kind": "synthetic_fixture", "title": "Constructed unit fixture", "url": None}}]}


def metric_row(gold, prediction):
    return {"gold_verdict": gold, "prediction": prediction}


def test_reuses_confusion_macro_and_selective_metrics_with_correct_denominators():
    rows = [metric_row("SUPPORTED", "SUPPORTED"), metric_row("CONTRADICTED", "INCONCLUSIVE"),
            metric_row("INCONCLUSIVE", "INCONCLUSIVE"), metric_row("SUPPORTED", "CONTRADICTED")]
    result = comparison.verdict_metrics(rows, "prediction")
    scores = result["classification"]
    assert scores["accuracy"] == 0.5
    assert scores["per_class"]["SUPPORTED"]["precision"] == 1
    assert scores["per_class"]["SUPPORTED"]["recall"] == 0.5
    assert scores["macro_f1"] == pytest.approx(4 / 9)
    assert scores["confusion_matrix"]["CONTRADICTED"]["INCONCLUSIVE"] == 1
    assert result["selective_on_labeled"]["coverage"] == 0.5
    assert result["selective_on_labeled"]["selective_accuracy"] == 0.5


def test_missing_labels_are_not_silently_replaced_or_scored():
    rows = [metric_row(None, "SUPPORTED"), metric_row("INCONCLUSIVE", None),
            metric_row("INCONCLUSIVE", "INCONCLUSIVE")]
    result = comparison.verdict_metrics(rows, "prediction")
    assert result["records"] == 3 and result["classification"]["count"] == 1
    assert result["missing_gold"] == 1 and result["missing_prediction"] == 1
    assert result["all_available_predictions"]["coverage"] == 0.5
    assert result["selective_on_labeled"]["coverage"] == 0
    assert result["selective_on_labeled"]["selective_accuracy"] is None
    assert result["classification"]["macro_f1_labels"] == ["INCONCLUSIVE"]


def test_no_gold_labels_means_not_measured_not_zero_accuracy():
    result = comparison.verdict_metrics([metric_row(None, "SUPPORTED")], "prediction")
    assert result["status"] == "NOT MEASURED"
    assert result["classification"]["accuracy"] is None
    assert result["classification"]["per_class"]["SUPPORTED"]["recall"] is None
    assert result["all_available_predictions"]["coverage"] == 1


@pytest.mark.parametrize("gold,prediction", [("true", "SUPPORTED"), ("SUPPORTED", "true")])
def test_invalid_metric_labels_are_rejected(gold, prediction):
    with pytest.raises(ValueError, match="Unknown"):
        comparison.verdict_metrics([metric_row(gold, prediction)], "prediction")


def test_empty_comparison_does_not_claim_perfect_equality_or_coverage():
    report = comparison.compare_cases([], [], "2026-11-02")
    assert report["baseline"]["status"] == "NOT MEASURED"
    assert report["verdict_pairing"]["identical"] is None
    assert report["explanation_coverage"]["excerpt_containment_rate"] is None
    assert report["explanation_coverage"]["enhanced_excerpt_coverage_over_claims_with_sources"] is None
    assert report["ablations"]["baseline"]["verdicts_changed"] is None


def test_unrecorded_explanation_fields_remain_unknown_not_zero_coverage():
    report = comparison.compare_cases([synthetic_case()], [{"verdict": "Inconclusive"}], "2026-11-02")
    coverage = report["explanation_coverage"]
    assert coverage["field_availability"]["baseline_method"] == {"observed_records": 0, "unrecorded": 1}
    assert coverage["rates_over_observed_claims"]["baseline_method"] is None


def test_changed_paired_verdict_is_reported_not_hidden():
    report = comparison.paired_verdicts([{"case_id": "changed", "baseline_verdict": "SUPPORTED", "enhanced_verdict": "CONTRADICTED"}])
    assert report["identical"] is False and report["mismatches"] == ["changed"]


def test_paired_pipeline_preserves_evidence_assessment_and_existing_reasons():
    case = synthetic_case()
    results = [comparison._result_item(case, evidence) for evidence in case["evidence"]]
    assessment = assess_evidence(case["claim"], results)
    before = deepcopy((case, assessment))
    report = comparison.compare_cases([case], [assessment], "2026-11-02")
    assert (case, assessment) == before
    assert report["baseline"] == report["enhanced"]
    assert report["verdict_pairing"]["identical"] is True
    assert report["explanation_coverage"]["counts"]["baseline_reasoning"] == 1
    assert report["explanation_coverage"]["contained_excerpt_entries"] == 1
    assert report["cases"][0]["source_kinds"] == {"synthetic_fixture": 1}


@pytest.mark.parametrize("mutation", ["verdict", "input"])
def test_accidental_diagnostic_mutation_fails_closed(monkeypatch, mutation):
    def corrupt(claim, results, assessment, **kwargs):
        output = build_explanation(claim, results, assessment, **kwargs)
        if mutation == "verdict":
            output["verdict"] = "Supported" if assessment["verdict"] != "Supported" else "Contradicted"
        else:
            results[0]["content"] = "Unjustified mutation"
        return output
    monkeypatch.setattr(comparison, "build_explanation", corrupt)
    with pytest.raises(ValueError, match="changed"):
        comparison.compare_cases([synthetic_case()], [{"verdict": "Inconclusive"}], "2026-11-02")


def test_ablation_is_explicit_about_uncertainty_dependencies():
    case = synthetic_case()
    report = comparison.compare_cases([case], [{"verdict": "Inconclusive"}], "2026-11-02")
    ablations = report["ablations"]
    assert len(ablations) == 6
    assert ablations["baseline"]["module_outputs"] == {}
    assert ablations["temporal_only"]["required_modules"] == ["temporal"]
    uncertainty = ablations["uncertainty_only"]
    assert uncertainty["visible_modules"] == ["uncertainty"]
    assert uncertainty["required_modules"] == ["temporal", "independence", "numerical", "uncertainty"]
    assert set(ablations["enhanced"]["module_outputs"]) == set(comparison.CONDITIONS["enhanced"])
    assert all(row["verdicts_changed"] == 0 for row in ablations.values())


def test_singleton_sources_are_not_counted_as_dependency_findings():
    case = synthetic_case()
    report = comparison.compare_cases([case], [{"verdict": "Inconclusive"}], "2026-11-02")
    counts = report["cases"][0]["module_counts"]["independence"]
    assert counts["findings"] == 0 and counts["unresolved"] == 1


def test_inference_raw_and_effective_labels_remain_separate():
    case = synthetic_case()
    url = comparison._result_item(case, case["evidence"][0])["url"]
    assessment = {"verdict": "Inconclusive", "per_source": [{"url": url, "part_assessments": [
        {"claim_part": case["claim"], "label": "UNCERTAIN", "model_label": "SUPPORTS", "contributed": False,
         "passage": case["evidence"][0]["passage"], "confidence": 0.65, "status": "Below threshold"}]}]}
    row = comparison.compare_cases([case], [assessment], "2026-11-02")["cases"][0]
    entry = row["enhanced_diagnostics"]["entries"][0]
    assert entry["model_label"] == "SUPPORTS" and entry["label"] == "UNCERTAIN"
    assert entry["contributed"] is False and row["enhanced_verdict"] == "INCONCLUSIVE"


def test_gold_label_cannot_change_diagnostics():
    first = synthetic_case("SUPPORTED")
    second = synthetic_case("CONTRADICTED")
    assessment = {"verdict": "Inconclusive", "reasoning": "No sufficient directional evidence"}
    left = comparison.compare_cases([first], [assessment], "2026-11-02")["cases"][0]
    right = comparison.compare_cases([second], [assessment], "2026-11-02")["cases"][0]
    assert left["enhanced_diagnostics"] == right["enhanced_diagnostics"]
    assert left["assessment_fingerprint"] == right["assessment_fingerprint"]


@pytest.mark.parametrize("operation", ["network", "model", "assessment"])
def test_offline_guard_blocks_network_and_inference(operation):
    import requests
    import nli_assessor
    with comparison.offline_only(), pytest.raises(RuntimeError, match="forbids"):
        if operation == "network":
            requests.get("https://must-not-connect.invalid", timeout=1)
        elif operation == "model":
            nli_assessor.load_local_nli_model()
        else:
            nli_assessor.assess_evidence_nli("claim", [], None)


def test_protocol_provenance_and_allowed_paths_are_exact():
    protocol = comparison.read_protocol()
    assert len(protocol["datasets"]) == 6
    assert not any("independent_human" in row["provenance"] for row in protocol["datasets"])
    assert protocol["datasets"][-1]["provenance"] == "developer_authored_synthetic_snapshots"


@pytest.mark.parametrize("field,value", [("path", "data/forbidden.jsonl"), ("provenance", "independent_human_annotated")])
def test_changed_allowlist_or_fabricated_provenance_is_rejected(tmp_path, monkeypatch, field, value):
    protocol = comparison.read_protocol()
    protocol["datasets"][0][field] = value
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(protocol))
    monkeypatch.setattr(comparison, "PROTOCOL", path)
    with pytest.raises(ValueError, match="allowlist/provenance"):
        comparison.read_protocol()


def archive_fixture():
    case = synthetic_case()
    item = case["evidence"][0]
    report = {"status": "MEASURED", "network_search_used": False, "split": "diagnostics",
              "dataset_sha256": {"diagnostics.jsonl": "expected-hash"}, "model": comparison.MODEL_ID,
              "model_revision": comparison.MODEL_REVISION, "assessment_thresholds": comparison.thresholds(),
              "case_count": 1, "passage_count": 1,
              "cases": [{"case_id": case["case_id"], "claim": case["claim"], "expected_final_verdict": "INCONCLUSIVE",
                         "actual_final_verdict": "INCONCLUSIVE", "evidence": [{"evidence_id": item["evidence_id"], "title": item["source"]["title"], "url": None}]}]}
    return case, report


def test_matching_archive_can_be_replayed_without_inference_or_invented_trace():
    case, archive = archive_fixture()
    assert comparison.validate_archive(archive, [case], "diagnostics", "expected-hash") == []
    assessment = comparison.archived_assessments(archive, [case])[0]
    assert "limitations" not in assessment and "method" not in assessment
    assert "relevance" not in assessment["per_source"][0]
    assert assessment["per_source"][0]["part_assessments"] == []


@pytest.mark.parametrize("change", ["hash", "revision", "threshold", "source", "claim", "count"])
def test_stale_or_misaligned_archives_are_rejected(change):
    case, archive = archive_fixture()
    if change == "hash":
        archive["dataset_sha256"]["diagnostics.jsonl"] = "stale"
    elif change == "revision":
        archive["model_revision"] = "different-model"
    elif change == "threshold":
        archive["assessment_thresholds"]["confidence"] = 0.5
    elif change == "source":
        archive["cases"][0]["evidence"][0]["title"] = "Different evidence"
    elif change == "claim":
        archive["cases"][0]["claim"] = "Different claim"
    else:
        archive["case_count"] = 99
    assert comparison.validate_archive(archive, [case], "diagnostics", "expected-hash")


def test_positive_metric_calculation_retains_false_positives():
    metrics = comparison.classification_metrics(["yes", "no", "yes", "no"], ["yes", "yes", "no", "no"], ("yes", "no"))
    result = comparison._binary_metrics(metrics, "yes")
    assert (result["tp"], result["fp"], result["fn"], result["tn"]) == (1, 1, 1, 1)
    assert result["precision"] == result["recall"] == result["f1"] == result["false_positive_rate"] == 0.5


def test_report_is_deterministic_and_preserves_provenance_and_pairing():
    first = comparison.run_comparison()
    second = comparison.run_comparison()
    assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(second, sort_keys=True, allow_nan=False)
    assert comparison.render_report(first) == comparison.render_report(second)
    assert first["execution"]["model_inference_used"] is False
    assert first["human_validated_findings"]["status"] == "NOT MEASURED"
    assert first["verdict_tracks"]["archived_nli_diagnostics"]["status"] == "NOT MEASURED"
    for track in first["verdict_tracks"].values():
        if track["status"] == "MEASURED":
            assert track["baseline"] == track["enhanced"]
            assert track["verdict_pairing"]["identical"] is True
    assert first["component_quality"]["numerical"]["unresolved_count"] > 0


def test_report_cli_refuses_overwrite(tmp_path):
    path = tmp_path / "existing"
    path.mkdir()
    marker = path / "original.txt"
    marker.write_text("Preserve me")
    with pytest.raises(SystemExit):
        comparison.main(["--output-dir", str(path)])
    assert marker.read_text() == "Preserve me" and not (path / "comparison.json").exists()
