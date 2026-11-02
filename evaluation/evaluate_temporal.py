"""Evaluate only the separate, developer-authored synthetic temporal challenge."""
import argparse
from collections import Counter
import json
from pathlib import Path

from evaluation.metrics import classification_metrics
from temporal_reasoning import CLASSIFICATIONS, MISMATCH_CODES, temporal_evidence_analysis


CHALLENGE = Path(__file__).with_name("temporal_challenge.json")


def validate_challenge(cases):
    seen = set()
    if not isinstance(cases, list):
        raise ValueError("Challenge cases must be an array")
    for case in cases:
        required = {"id", "category", "reference_date", "claim", "expected_classification",
                    "expected_expressions", "rationale", "evidence"}
        if not isinstance(case, dict) or not required.issubset(case):
            raise ValueError("Missing temporal challenge fields")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in seen:
            raise ValueError("Missing or duplicate temporal case ID")
        seen.add(case["id"])
        if case["expected_classification"] not in CLASSIFICATIONS:
            raise ValueError("Invalid temporal classification")
        if not isinstance(case["claim"], str) or not isinstance(case["expected_expressions"], list):
            raise ValueError("Invalid claim/expression annotations")
        if any(not isinstance(item, str) or item not in case["claim"] for item in case["expected_expressions"]):
            raise ValueError("Expected expressions must occur verbatim in the claim")
        if not isinstance(case["evidence"], list):
            raise ValueError("Evidence must be an array")
        for source in case["evidence"]:
            if (not isinstance(source, dict) or not isinstance(source.get("content"), str)
                    or not isinstance(source.get("expected_mismatch"), bool)):
                raise ValueError("Missing evidence text or expected mismatch label")
            if source.get("url"):
                raise ValueError("Synthetic temporal challenge must not invent public citation URLs")
    return cases


def evaluate_temporal_cases(cases):
    validate_challenge(cases)
    actual_classes, expected_classes, expected_mismatch, actual_mismatch = [], [], [], []
    tp = fp = fn = 0
    timeless_count = timeless_warnings = 0
    evidence_count = 0
    outputs = []
    for case in cases:
        analysis = temporal_evidence_analysis(case["claim"], case["evidence"], case["reference_date"])
        expected_classes.append(case["expected_classification"])
        actual_classes.append(analysis["claim"]["classification"])
        expected = Counter(case["expected_expressions"])
        actual = Counter(row["text"] for row in analysis["claim"]["expressions"])
        matched = sum((expected & actual).values())
        tp += matched
        fp += sum(actual.values()) - matched
        fn += sum(expected.values()) - matched
        case_outputs = []
        has_warning = False
        for source, result in zip(case["evidence"], analysis["sources"]):
            codes = [row["code"] for row in result["warnings"]]
            prediction = bool(MISMATCH_CODES & set(codes))
            expected_mismatch.append("mismatch" if source["expected_mismatch"] else "no_mismatch")
            actual_mismatch.append("mismatch" if prediction else "no_mismatch")
            has_warning = has_warning or prediction
            evidence_count += 1
            case_outputs.append({"expected_mismatch": source["expected_mismatch"],
                                 "actual_mismatch": prediction, "warning_codes": codes})
        if case["expected_classification"] == "timeless_candidate":
            timeless_count += 1
            timeless_warnings += int(has_warning)
        global_codes = [row["code"] for row in analysis["warnings"] if row["source_index"] is None]
        outputs.append({"id": case["id"], "category": case["category"],
                        "expected_classification": case["expected_classification"],
                        "actual_classification": analysis["claim"]["classification"],
                        "expected_expressions": list(case["expected_expressions"]),
                        "actual_expressions": list(actual.elements()),
                        "unresolved": analysis["claim"]["unresolved"], "sources": case_outputs,
                        "global_codes": global_codes,
                        "expected_global_codes": case.get("expected_global_codes")})
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {
        "scope": "Preliminary developer-authored synthetic diagnostics; not an independent or blind benchmark",
        "network_used": False, "model_used": False, "production_verdicts_changed": False,
        "claim_count": len(cases), "evidence_count": evidence_count,
        "classification": classification_metrics(expected_classes, actual_classes, CLASSIFICATIONS),
        "expression_detection": {"scope": "Exact expression text/occurrence counts in claims only; not date-resolution accuracy",
                                 "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
                                 "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None},
        "mismatch_detection": classification_metrics(expected_mismatch, actual_mismatch, ("mismatch", "no_mismatch")),
        "timeless_warning_rate": {"claims": timeless_count, "claims_with_mismatch_warning": timeless_warnings,
                                  "rate": timeless_warnings / timeless_count if timeless_count else None,
                                  "note": "Missing-date informational notices are excluded"},
        "cases": outputs,
        "limitations": "Authored together with the implementation; small convenience sample. No stance, factual accuracy, live retrieval quality or human comprehension is measured. Undefined metrics are null.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Create a new JSON report; refuses overwriting")
    args = parser.parse_args(argv)
    cases = json.loads(CHALLENGE.read_text(encoding="utf-8"))["cases"]
    report = evaluate_temporal_cases(cases)
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({key: value for key, value in report.items() if key != "cases"}, indent=2))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
