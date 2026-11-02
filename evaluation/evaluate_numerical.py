"""Offline evaluation of separate synthetic numerical/quantifier diagnostics."""
import argparse
from collections import Counter
import json
from pathlib import Path

from evaluation.metrics import classification_metrics
from numerical_reasoning import STATUSES, analyze_numerical_evidence


CHALLENGE = Path(__file__).with_name("numerical_challenge.json")


def validate_challenge(cases):
    if not isinstance(cases, list):
        raise ValueError("Challenge cases must be an array")
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or not {"id", "category", "claim", "evidence", "claim_quantities", "evidence_quantities", "expected_statuses", "rationale"}.issubset(case):
            raise ValueError("Missing numerical challenge fields")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in seen:
            raise ValueError("Missing or duplicate case ID")
        seen.add(case["id"])
        if not isinstance(case["claim"], str) or not isinstance(case["evidence"], dict) or not isinstance(case["evidence"].get("content"), str):
            raise ValueError("Missing claim/evidence text")
        if case["evidence"].get("url"):
            raise ValueError("Synthetic numerical cases must not invent public citations")
        for key, text in (("claim_quantities", case["claim"]), ("evidence_quantities", case["evidence"]["content"])):
            if not isinstance(case[key], list) or any(not isinstance(span, str) or not span or span not in text for span in case[key]):
                raise ValueError("Expected quantity strings must occur verbatim in their text")
        if not isinstance(case["expected_statuses"], list) or any(status not in STATUSES for status in case["expected_statuses"]):
            raise ValueError("Invalid expected comparison labels")
        if case["claim_quantities"] and len(case["expected_statuses"]) != len(case["claim_quantities"]):
            raise ValueError("One expected comparison is needed for each claim quantity")
        if not case["claim_quantities"] and len(case["expected_statuses"]) > 1:
            raise ValueError("Non-numeric scope cases have at most one comparison")
    return cases


def evaluate_numerical_cases(cases, reference_date=None):
    validate_challenge(cases)
    expected, predicted, outputs = [], [], []
    tp = fp = fn = 0
    for case in cases:
        analysis = analyze_numerical_evidence(case["claim"], [case["evidence"]], reference_date)
        source = analysis["sources"][0]
        for spans, extraction in ((case["claim_quantities"], analysis["claim"]), (case["evidence_quantities"], source["extracted"])):
            gold = Counter(spans)
            actual = Counter(row["text"] for row in extraction["quantities"])
            matched = sum((gold & actual).values())
            tp += matched
            fp += sum(actual.values()) - matched
            fn += sum(gold.values()) - matched
        actual_statuses, missing = [], []
        for index, status in enumerate(case["expected_statuses"]):
            target = index if case["claim_quantities"] else None
            comparisons = [row for row in source["comparisons"] if row["claim_quantity"] == target]
            mapped_missing = len(comparisons) != 1
            actual = "comparison_unresolved" if mapped_missing else comparisons[0]["status"]
            expected.append(status)
            predicted.append(actual)
            actual_statuses.append(actual)
            missing.append(mapped_missing)
        outputs.append({"id": case["id"], "category": case["category"],
                        "expected_statuses": case["expected_statuses"], "actual_statuses": actual_statuses,
                        "missing_comparison_mapped_to_abstention": missing,
                        "claim_quantities": analysis["claim"]["quantities"], "claim_dates": analysis["claim"]["dates"],
                        "claim_quantifiers": analysis["claim"]["quantifiers"],
                        "evidence_quantities": source["extracted"]["quantities"],
                        "comparisons": source["comparisons"], "quantifier_warnings": source["quantifier_warnings"]})
    total = len(expected)
    resolved = [(gold, actual) for gold, actual in zip(expected, predicted) if actual != "comparison_unresolved"]
    negatives = sum(label != "potential_mismatch" for label in expected)
    false_flags = sum(gold != "potential_mismatch" and actual == "potential_mismatch" for gold, actual in zip(expected, predicted))
    return {"scope": "Preliminary developer-authored synthetic diagnostics, not independent benchmark results or factual verification",
            "network_used": False, "model_used": False, "case_count": len(cases), "evidence_count": len(cases),
            "comparison_count": total, "reference_date": reference_date,
            "comparison_metrics": classification_metrics(expected, predicted, STATUSES),
            "quantity_extraction": {"scope": "Exact quantity text/occurrence counts on claims and evidence separately; interval correctness is tested separately",
                                    "tp": tp, "fp": fp, "fn": fn, "precision": tp / (tp + fp) if tp + fp else None,
                                    "recall": tp / (tp + fn) if tp + fn else None,
                                    "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None},
            "false_positive_mismatch_rate": {"false_flags": false_flags, "gold_non_mismatches": negatives,
                                             "rate": false_flags / negatives if negatives else None},
            "resolved_coverage": len(resolved) / total if total else None,
            "unresolved_count": total - len(resolved), "unresolved_rate": (total - len(resolved)) / total if total else None,
            "resolved_only_accuracy": sum(gold == actual for gold, actual in resolved) / len(resolved) if resolved else None,
            "cases": outputs,
            "limitations": "Small synthetic convenience sample authored alongside code. Context frames are deliberately conservative. No model truth/stance accuracy or independent human validation is measured. Undefined metrics are null; unresolved outcomes remain in full comparison metrics."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Create a new JSON report; refuse overwrite")
    args = parser.parse_args(argv)
    bundle = json.loads(CHALLENGE.read_text(encoding="utf-8"))
    report = evaluate_numerical_cases(bundle["cases"], bundle["reference_date"])
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({key: value for key, value in report.items() if key != "cases"}, indent=2))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
