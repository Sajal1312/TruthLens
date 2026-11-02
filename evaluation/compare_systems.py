"""Offline paired diagnostic comparison; no model inference, retrieval or guards.

Run as: .venv/bin/python -m evaluation.compare_systems --output-dir NEW_DIRECTORY
Only the six explicit permitted datasets below can be read by this runner.
"""
import argparse
from collections import Counter
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
from unittest.mock import patch

from evaluation.metrics import LABELS, classification_metrics, selective_metrics
from evaluation.run_evaluation import _result_item, load_cases
from evaluation.evaluate_temporal import evaluate_temporal_cases
from evaluation.evaluate_independence import evaluate_independence_cases
from evaluation.evaluate_numerical import evaluate_numerical_cases
from evaluation.evaluate_uncertainty import evaluate_uncertainty_cases
from explainability import build_explanation
from nli_assessor import (MIN_CONFIDENCE, MIN_DIRECTIONAL_SOURCES, MIN_MARGIN,
                          MODEL_ID, MODEL_REVISION)
from verifier import assess_evidence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROTOCOL = HERE / "comparison_protocol.json"
DATASETS = {
    "development": ("data/development.jsonl", "developer_authored_development"),
    "diagnostics": ("data/diagnostics.jsonl", "developer_authored_diagnostics"),
    "temporal": ("temporal_challenge.json", "developer_authored_synthetic"),
    "independence": ("independence_challenge.json", "developer_authored_synthetic"),
    "numerical": ("numerical_challenge.json", "developer_authored_synthetic"),
    "uncertainty": ("uncertainty_challenge.json", "developer_authored_synthetic_snapshots"),
}
CONDITIONS = {
    "baseline": [], "temporal_only": ["temporal"],
    "independence_only": ["independence"], "numerical_only": ["numerical"],
    "uncertainty_only": ["uncertainty"],
    "enhanced": ["explainability", "temporal", "independence", "numerical", "uncertainty"],
}
ARCHIVES = {
    "development": HERE / "results/development_2026-10-27-final.json",
    "diagnostics": HERE / "results/semantic_diagnostics_2026-10-27.json",
}
CODE_FILES = (
    "verifier.py", "nli_assessor.py", "evidence_quality.py", "explainability.py",
    "temporal_reasoning.py", "evidence_independence.py", "numerical_reasoning.py",
    "uncertainty_analysis.py", "evaluation/compare_systems.py", "evaluation/metrics.py",
    "evaluation/run_evaluation.py", "evaluation/evaluate_temporal.py",
    "evaluation/evaluate_independence.py", "evaluation/evaluate_numerical.py",
    "evaluation/evaluate_uncertainty.py",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


@contextmanager
def offline_only():
    """Fail closed if this evaluator accidentally attempts networking or inference."""
    def forbidden(*_args, **_kwargs):
        raise RuntimeError("Comparative evaluation forbids network access and model inference")

    targets = ("socket.create_connection", "socket.socket.connect", "socket.socket.connect_ex",
               "socket.getaddrinfo", "requests.sessions.Session.request", "verifier.search_evidence",
               "nli_assessor.load_local_nli_model", "nli_assessor.assess_evidence_nli",
               "evaluation.run_evaluation.load_local_nli_model", "evaluation.run_evaluation.assess_evidence_nli")
    with ExitStack() as stack:
        for target in targets:
            stack.enter_context(patch(target, side_effect=forbidden))
        yield


def read_protocol():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    rows = protocol["datasets"]
    observed = {row["id"]: (row["path"], row["provenance"]) for row in rows}
    # Do not accept a protocol edit that points this task at a protected dataset.
    if len(rows) != len(DATASETS) or observed != DATASETS:
        raise ValueError("Protocol dataset allowlist/provenance mismatch")
    if {name: row["visible_modules"] for name, row in protocol["conditions"].items()} != CONDITIONS:
        raise ValueError("Unsupported ablation configuration")
    return protocol


def verdict_metrics(records, key):
    """Missing references stay missing; never replace them with Inconclusive."""
    gold, predicted = [], []
    missing_gold = missing_prediction = 0
    available = []
    for row in records:
        actual, guess = row.get("gold_verdict"), row.get(key)
        if actual is not None and actual not in LABELS or guess is not None and guess not in LABELS:
            raise ValueError("Unknown verdict label")
        missing_gold += actual is None
        missing_prediction += guess is None
        if guess is not None:
            available.append(guess)
        if actual is not None and guess is not None:
            gold.append(actual)
            predicted.append(guess)
    directional = sum(label != "INCONCLUSIVE" for label in available)
    return {
        "status": "MEASURED" if gold else "NOT MEASURED",
        "records": len(records), "missing_gold": missing_gold, "missing_prediction": missing_prediction,
        "classification": classification_metrics(gold, predicted, LABELS),
        "selective_on_labeled": selective_metrics(gold, predicted),
        "all_available_predictions": {"count": len(available), "directional_count": directional,
                                      "coverage": directional / len(available) if available else None,
                                      "abstention_rate": 1 - directional / len(available) if available else None},
    }


def paired_verdicts(records):
    paired = [row for row in records if row.get("baseline_verdict") is not None and row.get("enhanced_verdict") is not None]
    mismatches = [row["case_id"] for row in paired if row["baseline_verdict"] != row["enhanced_verdict"]]
    return {"paired_claims": len(paired), "mismatches": mismatches,
            "identical": not mismatches if paired else None,
            "interpretation": "Verdict invariance by design; not evidence of an accuracy improvement"}


def _coverage_record(assessment, results, enhanced):
    rows = assessment.get("per_source") or []
    aligned = [row for index, row in enumerate(rows) if index < len(results) and row.get("url") == results[index].get("url")]
    entries = enhanced["entries"]
    excerpt_entries = [entry for entry in entries if entry["excerpt"]["text"]]
    return {
        "has_sources": bool(results), "source_records": len(results),
        "nonempty_sources": sum(bool(source.get("content", "").strip()) for source in results),
        "baseline_reasoning": bool(assessment["reasoning"]) if "reasoning" in assessment else None,
        "baseline_method": bool(assessment["method"]) if "method" in assessment else None,
        "baseline_limitations": bool(assessment["limitations"]) if "limitations" in assessment else None,
        "baseline_decision_trace": bool(aligned) if "per_source" in assessment else None,
        "enhanced_excerpt": bool(excerpt_entries), "excerpt_entries": len(excerpt_entries),
        "contained_excerpts": sum(entry["excerpt"]["text"] in results[entry["source_index"]]["content"] for entry in excerpt_entries),
        "recorded_passage_entries": sum(entry["excerpt"]["recorded_passage_located"] for entry in excerpt_entries),
        "recorded_nli_entries": sum(bool(entry["model_label"]) for entry in entries),
    }


def coverage_metrics(records):
    n = len(records)
    with_sources = sum(row["has_sources"] for row in records)
    excerpts = sum(row["excerpt_entries"] for row in records)
    counts = {key: sum(bool(row[key]) for row in records) for key in
              ("baseline_reasoning", "baseline_method", "baseline_limitations", "baseline_decision_trace", "enhanced_excerpt")}
    observed = {key: sum(row[key] is not None for row in records) for key in counts}
    return {"claims": n, "claims_with_sources": with_sources, "counts": counts,
            "field_availability": {key: {"observed_records": observed[key], "unrecorded": n - observed[key]} for key in counts},
            "rates_over_observed_claims": {key: value / observed[key] if observed[key] else None for key, value in counts.items()},
            "enhanced_excerpt_coverage_over_claims_with_sources": counts["enhanced_excerpt"] / with_sources if with_sources else None,
            "excerpt_entries": excerpts, "contained_excerpt_entries": sum(row["contained_excerpts"] for row in records),
            "excerpt_containment_rate": sum(row["contained_excerpts"] for row in records) / excerpts if excerpts else None,
            "recorded_passage_entries": sum(row["recorded_passage_entries"] for row in records),
            "recorded_nli_entries": sum(row["recorded_nli_entries"] for row in records),
            "interpretation": "Structural availability/substring containment only. Unrecorded archive fields are unknown, not absent UI features. Baseline already explains decisions. No human usefulness, semantic correctness or internal-model attribution is measured."}


def module_counts(explanation):
    """Descriptive output counts; units differ and must never be pooled as quality."""
    temporal = explanation["temporal"]
    numerical = explanation["numerical"]
    comparisons = [row for source in numerical["sources"] for row in source["comparisons"]]
    provenance = explanation["independence"]
    uncertainty = explanation["uncertainty"]
    return {
        "explainability": {"findings": sum(bool(row["excerpt"]["text"]) for row in explanation["entries"]), "unresolved": 0, "unit": "nonempty excerpt entries"},
        "temporal": {"findings": len(temporal["warnings"]), "unresolved": len(temporal["claim"]["unresolved"]), "unit": "date/context notices including missing metadata; unresolved counts claim expressions only"},
        "independence": {"findings": sum(len(group["members"]) > 1 for group in provenance["groups"]), "unresolved": sum(row["independence"] == "Independence not established" for row in provenance["sources"]), "unit": "multi-source possible dependency groups (singletons excluded); unresolved source independence, not verified independence"},
        "numerical": {"findings": sum(row["status"] == "potential_mismatch" for row in comparisons) + sum(len(row["quantifier_warnings"]) for row in numerical["sources"]), "unresolved": sum(row["status"] == "comparison_unresolved" for row in comparisons), "unit": "mismatch/scope notices and unresolved quantity comparisons"},
        "uncertainty": {"findings": len(uncertainty["findings"]), "unresolved": len(uncertainty["unknown_information"]), "unit": "diagnostic findings and unknown-information codes"},
    }


def ablation_summary(records):
    output = {}
    for condition, modules in CONDITIONS.items():
        dependencies = [name for name in CONDITIONS["enhanced"] if name in modules or "uncertainty" in modules and name != "explainability"]
        output[condition] = {
            "visible_modules": list(modules), "required_modules": dependencies,
            "verdicts_changed": len(paired_verdicts(records)["mismatches"]) if records else None,
            "module_outputs": {name: {
                "cases": len(records), "cases_with_findings": sum(row["module_counts"][name]["findings"] > 0 for row in records),
                "findings": sum(row["module_counts"][name]["findings"] for row in records),
                "unresolved": sum(row["module_counts"][name]["unresolved"] for row in records),
                "unit": records[0]["module_counts"][name]["unit"] if records else None,
                "quality_reference": "component_quality." + name if name != "explainability" else "Human usefulness NOT MEASURED; structural coverage only",
            } for name in modules},
            "note": "Presentation ablation of cached views on the same evidence, not speed or independent algorithm isolation. Uncertainty consumes three upstream diagnostics even when hidden. More warnings is not better performance.",
        }
    return output


def compare_cases(cases, assessments, reference_date):
    if len(cases) != len(assessments):
        raise ValueError("Assessment count differs from case count")
    records, coverages = [], []
    for case, original in zip(cases, assessments):
        results = [_result_item(case, evidence) for evidence in case["evidence"]]
        assessment = deepcopy(original)
        before = fingerprint([results, assessment])
        enhanced = build_explanation(case["claim"], results, assessment, reference_date=reference_date)
        if fingerprint([results, assessment]) != before or enhanced["verdict"] != assessment["verdict"]:
            raise ValueError("Diagnostics changed the frozen evidence/assessment/verdict")
        coverages.append(_coverage_record(assessment, results, enhanced))
        records.append({"case_id": case["case_id"], "gold_verdict": case.get("expected_final_verdict"),
                        "baseline_verdict": assessment["verdict"].upper(), "enhanced_verdict": enhanced["verdict"].upper(),
                        "evidence_fingerprint_both_conditions": fingerprint(results),
                        "assessment_fingerprint": fingerprint(assessment),
                        "source_kinds": dict(Counter(row["source"]["kind"] for row in case["evidence"])),
                        "reasoning": assessment.get("reasoning"), "module_counts": module_counts(enhanced),
                        "production_assessment": assessment, "enhanced_diagnostics": enhanced})
    return {
        "case_count": len(cases), "passage_count": sum(len(case["evidence"]) for case in cases),
        "baseline": verdict_metrics(records, "baseline_verdict"), "enhanced": verdict_metrics(records, "enhanced_verdict"),
        "verdict_pairing": paired_verdicts(records), "explanation_coverage": coverage_metrics(coverages),
        "ablations": ablation_summary(records), "cases": records,
        "verdict_errors": [{"case_id": row["case_id"], "expected": row["gold_verdict"], "actual": row["baseline_verdict"]}
                           for row in records if row["gold_verdict"] is not None and row["gold_verdict"] != row["baseline_verdict"]],
    }


def thresholds():
    return {"confidence": MIN_CONFIDENCE, "margin": MIN_MARGIN, "directional_sources": MIN_DIRECTIONAL_SOURCES}


def validate_archive(report, cases, split, dataset_hash):
    """Strict cohort matching; never select convenient subsets from stale runs."""
    problems = []
    if report.get("status") != "MEASURED" or report.get("network_search_used") is not False:
        problems.append("Archive execution metadata is missing or unsuitable")
    if report.get("split") != split or report.get("dataset_sha256") != {split + ".jsonl": dataset_hash}:
        problems.append("Dataset split/SHA-256 differs from the current permitted dataset")
    if report.get("model") != MODEL_ID or report.get("model_revision") != MODEL_REVISION or report.get("assessment_thresholds") != thresholds():
        problems.append("Model identity/revision/threshold metadata mismatch")
    saved = report.get("cases", [])
    if report.get("case_count") != len(cases) or report.get("passage_count") != sum(len(case["evidence"]) for case in cases):
        problems.append("Claim/passage counts differ")
    if [row.get("case_id") for row in saved] != [case["case_id"] for case in cases]:
        problems.append("Claim IDs/order differ")
    if problems:
        return problems
    for case, row in zip(cases, saved):
        evidence = row.get("evidence", [])
        if row.get("claim") != case["claim"] or row.get("expected_final_verdict") != case.get("expected_final_verdict") or row.get("actual_final_verdict") not in LABELS:
            problems.append("Claim/label mismatch: " + case["case_id"])
        if len(evidence) != len(case["evidence"]):
            problems.append("Evidence count mismatch: " + case["case_id"])
            continue
        for item, stored in zip(case["evidence"], evidence):
            if stored.get("evidence_id") != item["evidence_id"] or stored.get("title") != item["source"]["title"] or stored.get("url") != item["source"].get("url"):
                problems.append("Evidence identity mismatch: " + item["evidence_id"])
    return problems


def archived_assessments(report, cases):
    """Project only saved production fields. Missing original fields stay unknown.

    Original method/limitations, component outcomes and source relevance strings
    were not retained by this archive. Never reconstruct them from gold labels
    or experimental outputs. Part-level raw/effective labels stay separate.
    """
    output = []
    for case, saved in zip(cases, report["cases"]):
        rows = []
        for item, row in zip(case["evidence"], saved["evidence"]):
            rows.append({"title": row["title"], "url": _result_item(case, item)["url"],
                         "part_assessments": deepcopy(row.get("part_assessments", [])),
                         "status": row.get("status", "Original source status unavailable")})
        output.append({"original_claim": case["claim"], "verdict": saved["actual_final_verdict"].title(),
                       "reasoning": saved.get("reasoning"), "per_source": rows})
    return output


def _binary_metrics(metrics, positive):
    matrix = metrics["confusion_matrix"]
    tp = matrix[positive][positive]
    fp = sum(matrix[gold][positive] for gold in metrics["labels"] if gold != positive)
    fn = sum(matrix[positive][guess] for guess in metrics["labels"] if guess != positive)
    tn = metrics["count"] - tp - fp - fn
    return dict(metrics["per_class"][positive], tp=tp, fp=fp, fn=fn, tn=tn,
                false_positive_rate=fp / (fp + tn) if fp + tn else None)


def component_quality(bundles):
    reports = {
        "temporal": evaluate_temporal_cases(bundles["temporal"]["cases"]),
        "independence": evaluate_independence_cases(bundles["independence"]["cases"]),
        "numerical": evaluate_numerical_cases(bundles["numerical"]["cases"], bundles["numerical"].get("reference_date")),
        "uncertainty": evaluate_uncertainty_cases(bundles["uncertainty"]["cases"]),
    }
    temporal = reports["temporal"]
    temporal["positive_mismatch_metrics"] = _binary_metrics(temporal["mismatch_detection"], "mismatch")
    temporal["unresolved_claim_rate"] = sum(bool(row["unresolved"]) for row in temporal["cases"]) / len(temporal["cases"]) if temporal["cases"] else None
    independent = reports["independence"]
    independent["positive_detection_metrics"] = {key: _binary_metrics(value, "detected") for key, value in independent["metrics"].items()}
    numerical = reports["numerical"]
    numerical["positive_mismatch_metrics"] = _binary_metrics(numerical["comparison_metrics"], "potential_mismatch")
    return reports


def run_comparison():
    with offline_only():
        protocol = read_protocol()
        datasets, cases, bundles = [], {}, {}
        for row in protocol["datasets"]:
            path = HERE / row["path"]
            descriptor = dict(row, sha256=sha256(path), dataset_version="sha256:" + sha256(path))
            if row["id"] in ("development", "diagnostics"):
                loaded = load_cases(path)
                if any(case["split"] != row["id"] for case in loaded):
                    raise ValueError("Unexpected split in permitted dataset")
                cases[row["id"]] = loaded
                descriptor.update(claim_count=len(loaded), passage_count=sum(len(case["evidence"]) for case in loaded),
                                  source_kinds=dict(Counter(item["source"]["kind"] for case in loaded for item in case["evidence"])))
            else:
                bundle = json.loads(path.read_text(encoding="utf-8"))
                bundles[row["id"]] = bundle
                descriptor.update(schema_version=bundle["schema_version"], case_count=len(bundle["cases"]))
            datasets.append(descriptor)
        tracks = {}
        for split, data in cases.items():
            assessments = [assess_evidence(case["claim"], [_result_item(case, item) for item in case["evidence"]]) for case in data]
            tracks["current_rule_" + split] = dict(compare_cases(data, assessments, protocol["reference_date"]),
                                                  status="MEASURED", execution="Fresh unmodified production rule-based mode; no NLI inference")
            path = ARCHIVES[split]
            archived = {"status": "NOT MEASURED", "archive_path": str(path.relative_to(ROOT)), "limitations":
                        "Archived production outputs only; no historical code hash, original source relevance/method/limitations or complete component trace. Current NLI behavior is not revalidated."}
            if not path.is_file():
                archived["blocked_reasons"] = ["Permitted production archive is absent"]
            else:
                report = json.loads(path.read_text(encoding="utf-8"))
                digest = next(row["sha256"] for row in datasets if row["id"] == split)
                problems = validate_archive(report, data, split, digest)
                archived.update(archive_sha256=sha256(path), blocked_reasons=problems)
                if not problems:
                    archived.update(compare_cases(data, archived_assessments(report, data), protocol["reference_date"]),
                                    status="MEASURED", execution="Archived production NLI outcome replay; current diagnostics over a partial trace projection, not model re-execution")
            tracks["archived_nli_" + split] = archived
        quality = component_quality(bundles)
        return {
            "protocol": protocol, "protocol_sha256": sha256(PROTOCOL),
            "environment": {"python": platform.python_version(), "code_sha256": {name: sha256(ROOT / name) for name in CODE_FILES}},
            "execution": {"network_used": False, "model_inference_used": False, "experimental_guards_enabled": False,
                          "production_thresholds": thresholds(), "model": MODEL_ID, "model_revision": MODEL_REVISION,
                          "reference_date_note": "Fixed analysis anchor, not an evidence/event/access date"},
            "dataset_inventory": datasets, "verdict_tracks": tracks, "component_quality": quality,
            "baseline_diagnostic_quality": {"status": "NOT MEASURED", "reason": "New views absent by condition, not zero precision/recall. Existing production safeguards remain active. No comparable labeled diagnostic trace for baseline."},
            "human_validated_findings": {"status": "NOT MEASURED", "independent_annotations_used": 0},
            "limitations": ["Developer-authored labels are not independent human annotations; fixtures were inspected during development.",
                            "All conditions inherit identical frozen production verdicts. Equality is a consistency check, not an accuracy gain.",
                            "Standalone component scores have different denominators and are not pooled or transferred to unlabeled paired cases.",
                            "Output counts and excerpt containment do not establish explanation usefulness, semantic correctness or model faithfulness.",
                            "Presentation ablation caches views; uncertainty consumes upstream diagnostics. This is not isolated algorithm or runtime ablation.",
                            "No real reporting independence is established by pair labels, domains, publisher IDs or dependency warnings.",
                            "No confidence intervals or significance claims: small, dependent convenience samples; undefined metrics are null.",
                            "Partial archived trace projection cannot reproduce every original safeguard or provenance label."] + protocol["unmeasured"],
        }


def _fmt(value):
    return "undefined / not measured" if value is None else "{:.3f}".format(value) if isinstance(value, float) else str(value)


def render_report(report):
    lines = ["# TruthLens: baseline versus enhanced diagnostics", "",
             "## Research objective and conditions", "",
             "Measure additional diagnostic information and structural explanation coverage while preserving production verdicts. Baseline includes existing reasoning and safeguards; enhanced adds five read-only views. This is not an accuracy-improvement experiment.", "",
             "Protocol version: " + report["protocol"]["protocol_version"] + "; fixed reference date: " + report["protocol"]["reference_date"] + ". Network calls: 0. Model inference calls: 0. Experimental guards: off.", "",
             "## Datasets", "", "| Dataset | Provenance | Claims/cases | Passages/targets |", "|---|---|---:|---:|"]
    for row in report["dataset_inventory"]:
        lines.append("| {id} | {provenance} | {count} | {passages} |".format(**row, count=row.get("claim_count", row.get("case_count")), passages=row.get("passage_count", "see component denominators")))
    lines += ["", "Versions are exact SHA-256 values in comparison.json. Development/diagnostic sets contain public excerpts and synthetic fixtures with developer labels. Four challenge sets are synthetic. No pilot, independent annotations or held-out data are scored.", "", "## A. Verdict-level results", "",
              "| Track | N | Baseline / enhanced accuracy | Baseline / enhanced macro-F1 | Selective accuracy | Coverage | Abstention | Equal verdicts |", "|---|---:|---|---|---:|---:|---:|---|"]
    for name, track in report["verdict_tracks"].items():
        if track["status"] != "MEASURED":
            lines.append("| " + name + " | — | NOT MEASURED: " + "; ".join(track.get("blocked_reasons", [])) + " | — | — | — | — | — |")
            continue
        metrics, selective = track["baseline"]["classification"], track["baseline"]["selective_on_labeled"]
        enhanced = track["enhanced"]["classification"]
        lines.append("| {0} | {1} | {2} / {3} | {4} / {5} | {6} | {7} | {8} | {9} |".format(name, track["case_count"], _fmt(metrics["accuracy"]), _fmt(enhanced["accuracy"]), _fmt(metrics["macro_f1"]), _fmt(enhanced["macro_f1"]), _fmt(selective["selective_accuracy"]), _fmt(selective["coverage"]), _fmt(selective["abstention_rate"]), track["verdict_pairing"]["identical"]))
    lines += ["", "Fresh rule-based runs do not measure NLI performance. Archived NLI results are historical replay only, not current inference validation. Identical predictions imply no observed verdict gain. Full per-class precision/recall/F1, gold support, confusion matrices (rows=gold) and errors are stored in JSON. Macro-F1 uses gold-present labels; empty/undefined denominators are null.", "", "## B. Diagnostic quality on existing labeled component fixtures", "",
              "| Task | Unit / N | Precision | Recall | F1 | False-positive rate |", "|---|---|---:|---:|---:|---:|"]
    quality = report["component_quality"]
    rows = [("Temporal mismatch", "evidence / " + str(quality["temporal"]["evidence_count"]), quality["temporal"]["positive_mismatch_metrics"])]
    rows += [("Dependency " + name, "pairs / " + str(quality["independence"]["pair_count"]), scores) for name, scores in quality["independence"]["positive_detection_metrics"].items()]
    rows += [("Numerical mismatch", "comparisons / " + str(quality["numerical"]["comparison_count"]), quality["numerical"]["positive_mismatch_metrics"]),
             ("Uncertainty category micro (all labels)", "label decisions / " + str(sum(quality["uncertainty"]["micro_all_categories"][key] for key in ("tp", "fp", "fn", "tn"))), quality["uncertainty"]["micro_all_categories"])]
    for task, unit, scores in rows:
        lines.append("| {0} | {1} | {2} | {3} | {4} | {5} |".format(task, unit, *[_fmt(scores[key]) for key in ("precision", "recall", "f1", "false_positive_rate")]))
    lines += ["", "Temporal classification accuracy: " + _fmt(quality["temporal"]["classification"]["accuracy"]) + "; unresolved claim-context rate: " + _fmt(quality["temporal"]["unresolved_claim_rate"]) + ".",
              "Numerical comparison macro-F1: " + _fmt(quality["numerical"]["comparison_metrics"]["macro_f1"]) + "; unresolved: " + str(quality["numerical"]["unresolved_count"]) + "/" + str(quality["numerical"]["comparison_count"]) + ".",
              "Uncertainty exact category-set accuracy: " + _fmt(quality["uncertainty"]["exact_label_set_accuracy"]) + "; macro-F1 (gold-present categories): " + _fmt(quality["uncertainty"]["macro_f1"]) + ". Absent gold categories: " + ", ".join(quality["uncertainty"]["absent_gold_categories"]) + ".",
              "Baseline new-view quality is NOT MEASURED, not zero. Component labels cannot score the unlabeled paired-case diagnostics. Uncertainty scores test declared snapshot mapping only, not detector accuracy or causal faithfulness.", "", "## C. Explanation coverage and ablations", "",
              "| Track | Existing reasons / claims | Enhanced excerpts / claims with sources | Exact substring containment | Recorded NLI entries |", "|---|---|---|---|---:|"]
    for name, track in report["verdict_tracks"].items():
        if track["status"] != "MEASURED":
            continue
        cov = track["explanation_coverage"]
        lines.append("| {0} | {1}/{2} | {3}/{4} | {5}/{6} | {7} |".format(name, cov["counts"]["baseline_reasoning"], cov["claims"], cov["counts"]["enhanced_excerpt"], cov["claims_with_sources"], cov["contained_excerpt_entries"], cov["excerpt_entries"], cov["recorded_nli_entries"]))
    lines += ["", "A selected excerpt is a reading aid, not the model's causal rationale. Missing archived method/limitations are not counted as a baseline defect.", "",
              "Each measured track has six presentation ablations in JSON. Counts below use the current diagnostic split only; counts are descriptive and overlapping, not accuracy or benefit scores.", "",
              "| Condition | Visible modules | Required modules | Findings by module | Unresolved by module |", "|---|---|---|---|---|"]
    for name, ablation in report["verdict_tracks"]["current_rule_diagnostics"]["ablations"].items():
        lines.append("| {0} | {1} | {2} | {3} | {4} |".format(name, ", ".join(ablation["visible_modules"]) or "none", ", ".join(ablation["required_modules"]) or "none", "; ".join(key + ": " + str(row["findings"]) for key, row in ablation["module_outputs"].items()) or "none", "; ".join(key + ": " + str(row["unresolved"]) for key, row in ablation["module_outputs"].items()) or "none"))
    lines += ["", "Uncertainty-only consumes hidden temporal, independence and numerical views; ablation is presentation-level, not independent algorithm isolation. All conditions use identical cached assessments and stored evidence. More warnings is not automatically better.", "", "## Error analysis", ""]
    for row in quality["temporal"]["cases"]:
        if row["expected_classification"] != row["actual_classification"]:
            lines.append("- Temporal " + row["id"] + ": " + row["expected_classification"] + " → " + row["actual_classification"])
    for row in quality["independence"]["cases"]:
        for pair in row["pairs"]:
            if pair["expected"] != pair["actual"]:
                lines.append("- Dependency " + row["id"] + ": expected " + json.dumps(pair["expected"], sort_keys=True) + "; actual " + json.dumps(pair["actual"], sort_keys=True))
    for row in quality["numerical"]["cases"]:
        if row["expected_statuses"] != row["actual_statuses"]:
            lines.append("- Numerical " + row["id"] + ": " + ", ".join(row["expected_statuses"]) + " → " + ", ".join(row["actual_statuses"]))
    lines += ["", "Rule-based abstentions reflect conservative exact-proposition matching; they are retained as errors when directional developer labels differ. Archived NLI trace gaps remain unknown, not reconstructed from references. Per-case verdict errors and all component outputs are in JSON.", "", "## D. Threats to validity, limitations and next experiment", ""]
    lines += ["- " + item for item in report["limitations"]]
    lines += ["", "Human-validated findings: NOT MEASURED. Next: complete independent annotations and randomized, counterbalanced baseline/enhanced explanation ratings (usefulness, correct attribution, warning relevance, comprehension and review time), with adjudication and blinded model output. Freeze the protocol before final testing. Do not tune against protected test data.", "",
              "Reproduce: `.venv/bin/python -m evaluation.compare_systems --output-dir evaluation/results/comparison_NEW_RUN`. The destination must not exist. JSON is deterministic for identical inputs/code/Python; no wall-clock timing is scored.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Create a new directory; refuse overwrite")
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        parser.error("Output directory already exists; use a new directory to preserve results")
    report = run_comparison()
    markdown = render_report(report)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "comparison.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    (args.output_dir / "REPORT.md").write_text(markdown, encoding="utf-8")
    print("Created " + str(args.output_dir / "REPORT.md") + " and comparison.json; no network or model inference")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
