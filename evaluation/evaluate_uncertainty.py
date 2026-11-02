"""Evaluate aggregation of declared synthetic trace/diagnostic snapshots only."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from uncertainty_analysis import CATEGORIES, analyze_uncertainty


CHALLENGE = Path(__file__).with_name("uncertainty_challenge.json")
_GAP_CODES = {"decision_trace_unavailable", "diagnostic_views_unavailable",
              "diagnostic_views_misaligned", "diagnostic_count_mismatch"}


def validate_challenge(cases):
    if not isinstance(cases, list):
        raise ValueError("Challenge cases must be an array")
    seen = set()
    for case in cases:
        required = {"id", "category", "source_count", "verdict", "reasoning", "trace",
                    "expected_categories", "expected_information_gap", "rationale"}
        if not isinstance(case, dict) or not required.issubset(case):
            raise ValueError("Missing uncertainty challenge fields")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in seen:
            raise ValueError("Missing or duplicate case ID")
        seen.add(case["id"])
        if type(case["source_count"]) is not int or not 0 <= case["source_count"] <= 8:
            raise ValueError("Invalid synthetic source count")
        if case["verdict"] not in {"Supported", "Contradicted", "Inconclusive"} or not isinstance(case["reasoning"], str):
            raise ValueError("Invalid saved verdict/explanation")
        if case["trace"] is not None and (not isinstance(case["trace"], list) or any(not isinstance(row, dict) for row in case["trace"])):
            raise ValueError("Trace must be an array of projected records or null")
        labels = case["expected_categories"]
        if not isinstance(labels, list) or len(set(labels)) != len(labels) or any(label not in CATEGORIES for label in labels):
            raise ValueError("Invalid or duplicate category labels")
        if type(case["expected_information_gap"]) is not bool:
            raise ValueError("Information-gap annotation must be boolean")
        if any(name not in {"independence", "temporal", "numerical"} for name in case.get("unavailable_views", [])):
            raise ValueError("Unknown diagnostic view")
    return cases


def materialize_fixture(case):
    """Expand explicitly declared synthetic projections; run no upstream analysis.

    Boilerplate gives each fixture aligned source identifiers and quiet metadata.
    All non-default signals/expected labels are authored in the JSON dataset.
    These snapshots are not actual model/search outputs or real annotations.
    """
    count = case["source_count"]
    results = [{"title": "Synthetic " + case["id"] + " source " + str(index + 1),
                "url": "https://fixture-{0}.example/{1}".format(index, case["id"]),
                "content": "Constructed snapshot passage {0} for {1}. No factual source is represented.".format(index, case["id"]),
                "published_date": "2026-10-01"} for index in range(count)]
    assessment = {"verdict": case["verdict"], "reasoning": case["reasoning"],
                  "method": "Synthetic saved-assessment snapshot", "part_outcomes": deepcopy(case.get("part_outcomes", [])),
                  "fallback_used": case.get("fallback_used", False)}
    if case["trace"] is not None:
        assessment["per_source"] = deepcopy(case["trace"])
        for index, row in enumerate(assessment["per_source"]):
            if index < len(results):
                row.setdefault("url", results[index]["url"])
    independence = {"counts": {"retrieved_passages": count, "distinct_source_urls": count,
                                "exact_duplicate_pairs": 0, "near_duplicate_pairs": 0,
                                "explicit_dependency_pairs": 0, "possible_dependency_pairs": 0},
                    "sources": [{"independence": "Independence not established"} for _ in results], "relationships": []}
    independence["counts"].update(case.get("provenance_counts", {}))
    if case.get("provenance_counts", {}).get("exact_duplicate_pairs") and results:
        for source in results:
            source["content"] = results[0]["content"]
    temporal = {"claim": {"classification": "timeless_candidate", "unresolved": list(case.get("temporal_claim_unresolved", []))},
                "sources": [{"metadata": {"publication_date": {"status": "resolved", "raw": "2026-10-01"}}} for _ in results],
                "warnings": deepcopy(case.get("temporal_warnings", []))}
    for warning in temporal["warnings"]:
        index = warning.get("source_index")
        if type(index) is int and 0 <= index < count and warning["code"].startswith("publication_date_"):
            status = warning["code"].removeprefix("publication_date_")
            temporal["sources"][index]["metadata"]["publication_date"] = {"status": status, "raw": None}
            results[index]["published_date"] = ""
    numerical = {"claim": {}, "sources": [{"source_index": index, "comparisons": [], "quantifier_warnings": []} for index in range(count)]}
    if count:
        numerical["sources"][0]["comparisons"] = deepcopy(case.get("numerical_comparisons", []))
        numerical["sources"][0]["quantifier_warnings"] = list(case.get("quantifier_warnings", []))
    views = {"independence": independence, "temporal": temporal, "numerical": numerical}
    for name in case.get("unavailable_views", []):
        views[name] = None
    return assessment, results, views


def _scores(tp, fp, fn, tn):
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "support": tp + fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
            "false_positive_rate": fp / (fp + tn) if fp + tn else None}


def attribution_contract_violations(report, assessment):
    violations = []
    primary = report["primary_reason"]
    if primary["text"] is not None and (assessment.get("verdict") != "Inconclusive" or not assessment.get("reasoning") or primary["text"] != assessment["reasoning"] or primary["origin"] != "recorded_explanation"):
        violations.append("Primary reason was not a verbatim Inconclusive decision explanation")
    if any(finding.get("verdict_relation") != "additional_diagnostic_only" for finding in report["findings"]):
        violations.append("Additional diagnostic finding was promoted to a verdict cause")
    return violations


def evaluate_uncertainty_cases(cases):
    validate_challenge(cases)
    per_label = {category: [0, 0, 0, 0] for category in CATEGORIES}
    gap_counts = [0, 0, 0, 0]
    outputs = []
    exact = unsafe = source_count = 0
    for case in cases:
        assessment, results, views = materialize_fixture(case)
        report = analyze_uncertainty(assessment, results, **views)
        expected, actual = set(case["expected_categories"]), set(report["categories"])
        exact += expected == actual
        for category in CATEGORIES:
            position = 0 if category in expected and category in actual else 1 if category in actual else 2 if category in expected else 3
            per_label[category][position] += 1
        gap = any(finding["code"] in _GAP_CODES for finding in report["findings"])
        gap_counts[0 if case["expected_information_gap"] and gap else 1 if gap else 2 if case["expected_information_gap"] else 3] += 1
        violations = attribution_contract_violations(report, assessment)
        unsafe += bool(violations)
        source_count += len(results)
        outputs.append({"id": case["id"], "category": case["category"], "expected_categories": case["expected_categories"],
                        "actual_categories": report["categories"], "expected_information_gap": case["expected_information_gap"],
                        "actual_information_gap": gap, "attribution_contract_violations": violations,
                        "primary_reason": report["primary_reason"], "availability": report["availability"], "agreement": report["agreement"],
                        "finding_codes": [finding["code"] for finding in report["findings"]]})
    metrics = {category: _scores(*values) for category, values in per_label.items()}
    present = [category for category in CATEGORIES if metrics[category]["support"]]
    totals = [sum(per_label[category][index] for category in present) for index in range(4)]
    all_totals = [sum(values[index] for values in per_label.values()) for index in range(4)]
    return {"scope": "Preliminary developer-authored synthetic snapshot mapping; not independent evaluation, upstream accuracy or causal-model faithfulness",
            "network_used": False, "model_used": False, "upstream_diagnostics_recomputed": False,
            "case_count": len(cases), "source_count": source_count, "category_metrics": metrics,
            "micro_all_categories": _scores(*all_totals), "present_category_micro": _scores(*totals),
            "macro_f1": sum(metrics[category]["f1"] or 0 for category in present) / len(present) if present else None,
            "macro_labels": present, "absent_gold_categories": [category for category in CATEGORIES if category not in present],
            "exact_label_set_accuracy": exact / len(cases) if cases else None,
            "missing_information_detection": _scores(*gap_counts),
            "missing_information_definition": "Decision/view trace availability or alignment gaps; unknown dates and provenance are scored separately as categories",
            "incorrect_attribution_contract": {"violating_cases": unsafe, "cases": len(cases), "rate": unsafe / len(cases) if cases else None,
                                                "note": "Structural attribution contract only, not independently annotated causal correctness"},
            "cases": outputs, "limitations": "Snapshots and labels were authored alongside code. Categories can overlap and provenance uncertainty is common. No identified diagnostic issue is not evidence certification. Undefined metrics are null; absent gold labels are excluded from macro-F1."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Create a new JSON report; refuse overwrite")
    args = parser.parse_args(argv)
    cases = json.loads(CHALLENGE.read_text(encoding="utf-8"))["cases"]
    report = evaluate_uncertainty_cases(cases)
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({key: value for key, value in report.items() if key != "cases"}, indent=2))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
