"""Offline pair-level evaluation on the separate synthetic provenance challenge."""
import argparse
from itertools import combinations
import json
from pathlib import Path
from urllib.parse import urlsplit

from evidence_independence import analyze_evidence_independence
from evaluation.metrics import classification_metrics


CHALLENGE = Path(__file__).with_name("independence_challenge.json")
_FLAGS = {"exact": "exact_duplicate", "near": "near_duplicate", "explicit": "explicit_dependency"}


def validate_challenge(cases):
    seen = set()
    if not isinstance(cases, list):
        raise ValueError("Cases must be an array")
    for case in cases:
        if not isinstance(case, dict) or not {"id", "category", "rationale", "sources", "pairs"}.issubset(case):
            raise ValueError("Missing independence challenge fields")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in seen:
            raise ValueError("Missing or duplicate challenge ID")
        seen.add(case["id"])
        if not isinstance(case["sources"], list) or not isinstance(case["pairs"], list):
            raise ValueError("Sources/pairs must be arrays")
        for source in case["sources"]:
            if not isinstance(source, dict) or not isinstance(source.get("content"), str):
                raise ValueError("Missing synthetic source text")
            # Malformed URLs are intentional fixtures, but public source hosts
            # must not be fabricated in this synthetic dataset.
            try:
                host = urlsplit(source.get("url") or "").hostname
            except ValueError:
                host = None
            if host and not host.endswith((".example", ".invalid")):
                raise ValueError("Synthetic source URLs must use reserved example/invalid domains")
        pairs = set()
        for pair in case["pairs"]:
            if not isinstance(pair, dict) or not {"left", "right", "exact", "near", "explicit", "group"}.issubset(pair):
                raise ValueError("Missing pair annotations")
            key = (pair["left"], pair["right"])
            if (any(type(index) is not int for index in key) or not 0 <= key[0] < key[1] < len(case["sources"]) or key in pairs):
                raise ValueError("Invalid or duplicate pair references")
            if any(type(pair[field]) is not bool for field in ("exact", "near", "explicit", "group")):
                raise ValueError("Pair labels must be explicit booleans")
            pairs.add(key)
        if pairs != set(combinations(range(len(case["sources"])), 2)):
            raise ValueError("Every source pair needs annotations")
    return cases


def evaluate_independence_cases(cases):
    validate_challenge(cases)
    gold = {name: [] for name in (*_FLAGS, "group")}
    actual = {name: [] for name in gold}
    outputs = []
    source_count = 0
    for case in cases:
        analysis = analyze_evidence_independence(case["sources"])
        by_pair = {(row["left"], row["right"]): row for row in analysis["relationships"]}
        source_count += len(case["sources"])
        pairs = []
        for expected in case["pairs"]:
            relationship = by_pair[(expected["left"], expected["right"])]
            predicted = {name: relationship[key] for name, key in _FLAGS.items()}
            predicted["group"] = any({expected["left"], expected["right"]}.issubset(group["members"]) for group in analysis["groups"])
            for name in gold:
                gold[name].append("detected" if expected[name] else "not_detected")
                actual[name].append("detected" if predicted[name] else "not_detected")
            pairs.append({"left": expected["left"], "right": expected["right"],
                          "expected": {name: expected[name] for name in gold}, "actual": predicted,
                          "category": relationship["category"], "signals": relationship["signals"]})
        outputs.append({"id": case["id"], "category": case["category"], "pairs": pairs,
                        "groups": [{"members": group["members"], "reason": group["reason"]} for group in analysis["groups"]]})
    metrics = {name: classification_metrics(gold[name], actual[name], ("detected", "not_detected")) for name in gold}
    negative_groups = sum(value == "not_detected" for value in gold["group"])
    false_groups = sum(expected == "not_detected" and predicted == "detected" for expected, predicted in zip(gold["group"], actual["group"]))
    return {"scope": "Preliminary developer-authored synthetic diagnostics; no independent benchmark or proven independence",
            "network_used": False, "model_used": False, "case_count": len(cases), "source_count": source_count,
            "pair_count": len(gold["group"]), "metrics": metrics,
            "false_positive_grouping": {"false_grouped_pairs": false_groups, "gold_ungrouped_pairs": negative_groups,
                                        "rate": false_groups / negative_groups if negative_groups else None},
            "cases": outputs,
            "limitations": "Pair labels are authored diagnostic expectations, not verified reporting chains. Cases are small, clustered within documents and developed alongside code. Shared references can be critical or incidental. Lexical similarity misses substantial paraphrases. Undefined metrics are null."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Create a new report; refuse overwrite")
    args = parser.parse_args(argv)
    bundle = json.loads(CHALLENGE.read_text(encoding="utf-8"))
    report = evaluate_independence_cases(bundle["cases"])
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({key: value for key, value in report.items() if key != "cases"}, indent=2))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
