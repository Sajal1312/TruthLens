#!/usr/bin/env python3
"""Run TruthLens against fixed passages using only its local NLI assessment path.

This module never reads Tavily configuration and never calls the search API.
Set HF_HUB_OFFLINE=1 before model loading so missing cached weights fail clearly.
"""
import argparse
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.metrics import (LABELS, RELEVANCE_LABELS, STANCE_LABELS,
                                classification_metrics, selective_metrics)
from nli_assessor import (MIN_CONFIDENCE, MIN_DIRECTIONAL_SOURCES, MIN_MARGIN,
                          MODEL_ID, MODEL_REVISION, assess_evidence_nli,
                          load_local_nli_model)

DATA_DIR = Path(__file__).parent / "data"


def load_cases(path):
    cases = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError("{0}:{1}: invalid JSONL: {2}".format(path, line_number, exc)) from exc
    validate_cases(cases)
    return cases


def validate_cases(cases):
    ids = set()
    for case in cases:
        required = {"case_id", "split", "claim", "tags", "expected_final_verdict", "rationale", "evidence"}
        missing = required - set(case)
        if missing:
            raise ValueError("case missing fields: " + ", ".join(sorted(missing)))
        if case["case_id"] in ids:
            raise ValueError("duplicate case_id: " + case["case_id"])
        ids.add(case["case_id"])
        evidence_ids = set()
        if case["expected_final_verdict"] not in LABELS:
            raise ValueError("invalid final verdict in " + case["case_id"])
        if case["split"] not in ("development", "held_out", "diagnostics"):
            raise ValueError("invalid split in " + case["case_id"])
        for evidence in case["evidence"]:
            if not evidence.get("evidence_id") or evidence["evidence_id"] in evidence_ids:
                raise ValueError("missing or duplicate evidence_id in " + case["case_id"])
            evidence_ids.add(evidence["evidence_id"])
            if evidence.get("expected_relevance") not in RELEVANCE_LABELS:
                raise ValueError("invalid expected relevance in " + case["case_id"])
            if evidence.get("expected_stance") not in STANCE_LABELS:
                raise ValueError("invalid expected stance in " + case["case_id"])
            source = evidence.get("source", {})
            if source.get("kind") == "public_excerpt":
                if not source.get("url", "").startswith("https://"):
                    raise ValueError("public excerpt needs an HTTPS source URL: " + evidence["evidence_id"])
                if not source.get("publisher_id") or not source.get("checked_on") or not source.get("title"):
                    raise ValueError("public excerpt needs title, publisher_id, and checked_on: " + evidence["evidence_id"])
            if source.get("kind") == "synthetic_fixture" and source.get("url") is not None:
                raise ValueError("synthetic fixture must not have a citation URL: " + evidence["evidence_id"])
        if case["expected_final_verdict"] in ("SUPPORTED", "CONTRADICTED") and case["split"] != "diagnostics":
            directional = [entry for entry in case["evidence"]
                           if entry["expected_stance"] == ("SUPPORTS" if case["expected_final_verdict"] == "SUPPORTED" else "CONTRADICTS")
                           and entry["source"].get("kind") == "public_excerpt"]
            urls = {entry["source"].get("url") for entry in directional}
            if len(directional) < 2 or len(urls) < 2:
                raise ValueError("directional gold case needs two distinct public URLs: " + case["case_id"])


def _result_item(case, evidence):
    source = evidence["source"]
    url = source.get("url") or "https://evaluation.invalid/{0}/{1}".format(
        case["case_id"], evidence["evidence_id"])
    return {"title": source["title"], "url": url, "content": evidence["passage"],
            "published_date": source.get("published_date") or ""}


def _actual_relevance(value):
    return {"Directly relevant candidate": "relevant", "Different time period": "relevant",
            "Weakly related": "weakly_related", "Unrelated": "unrelated"}.get(value, "unrelated")


def _source_diversity(evidence, assessed_rows):
    """Summarize annotated publishers among counted passages without asserting independence."""
    evidence_by_id = {item["evidence_id"]: item for item in evidence}
    publisher_counts = Counter()
    public_urls = set()
    synthetic_count = 0
    counted = 0
    for row in assessed_rows:
        if not row["contributed"]:
            continue
        counted += 1
        source = evidence_by_id[row["evidence_id"]]["source"]
        if source.get("kind") == "synthetic_fixture":
            synthetic_count += 1
            continue
        publisher = source.get("publisher_id")
        if isinstance(publisher, str) and publisher.strip():
            publisher_counts[publisher.strip()] += 1
        if source.get("url"):
            public_urls.add(source["url"])
    public_count = sum(publisher_counts.values())
    return {
        "counted_directional_passages": counted,
        "counted_public_passages": public_count,
        "counted_synthetic_passages": synthetic_count,
        "counted_unique_public_urls": len(public_urls),
        "distinct_declared_publishers": len(publisher_counts),
        "passages_per_declared_publisher": dict(sorted(publisher_counts.items())),
        "largest_publisher_share": max(publisher_counts.values()) / public_count if public_count else None,
        "independence_verified": False,
        "note": "Publisher IDs are dataset annotations. Different publishers or URLs do not prove independent reporting.",
    }


def _publisher_key(source, require_declared=False):
    """Normalize declared publisher metadata; missing values share one bucket."""
    publisher = source.get("publisher_id")
    if isinstance(publisher, str) and publisher.strip():
        return "publisher:" + re.sub(r"[^a-z0-9]+", " ", publisher.casefold()).strip()
    if require_declared:
        return None
    # Do not infer publisher identity from hostnames: domains do not establish
    # shared ownership or independent reporting. Unknown provenance is one
    # shared bucket so missing metadata cannot manufacture multiple votes.
    return "publisher:unknown"


def _experimental_verdict(case, assessed_rows, mode):
    """Reaggregate eligible passage labels for comparison; production is unchanged."""
    part_names = []
    for row in assessed_rows:
        for part in row.get("part_assessments", []):
            name = part.get("claim_part")
            if name not in part_names:
                part_names.append(name)
    if not part_names:
        return "INCONCLUSIVE", {"part_outcomes": [], "reason": "No eligible assessed claim parts."}

    source_by_id = {entry["evidence_id"]: entry["source"] for entry in case["evidence"]}
    outcomes = []
    for index, part_name in enumerate(part_names):
        groups = defaultdict(set)
        passages = defaultdict(set)
        for row in assessed_rows:
            assessments = row.get("part_assessments", [])
            if index >= len(assessments):
                continue
            assessment = assessments[index]
            if not assessment.get("contributed"):
                continue
            label = assessment.get("label")
            if label not in ("SUPPORTS", "CONTRADICTS"):
                continue
            source = source_by_id[row["evidence_id"]]
            if mode == "distinct_publishers":
                key = _publisher_key(source, require_declared=True)
                if key is None:
                    continue
            else:
                key = _publisher_key(source)
            # A conflicting publisher group remains a conflict; it is not
            # allowed to cast two votes in one direction.
            groups[key].add(label)
            passage = row.get("passage_normalized")
            if passage:
                passages[key].add(label + ":" + passage)

        support_groups = {group for group, labels in groups.items() if "SUPPORTS" in labels}
        contradiction_groups = {group for group, labels in groups.items() if "CONTRADICTS" in labels}
        if support_groups and contradiction_groups:
            outcome = "INCONCLUSIVE"
            reason = "Eligible evidence points in both directions after publisher grouping."
        elif len(support_groups) >= MIN_DIRECTIONAL_SOURCES:
            outcome = "SUPPORTED"
            reason = "At least two qualifying publisher groups support this component."
        elif len(contradiction_groups) >= MIN_DIRECTIONAL_SOURCES:
            outcome = "CONTRADICTED"
            reason = "At least two qualifying publisher groups contradict this component."
        else:
            outcome = "INCONCLUSIVE"
            reason = "Fewer than two qualifying publisher groups support one direction."
        outcomes.append({"claim_part": part_name, "verdict": outcome,
                         "support_groups": len(support_groups),
                         "contradiction_groups": len(contradiction_groups),
                         "reason": reason})

    part_verdicts = {item["verdict"] for item in outcomes}
    if part_verdicts == {"SUPPORTED"}:
        verdict = "SUPPORTED"
    elif part_verdicts == {"CONTRADICTED"}:
        verdict = "CONTRADICTED"
    else:
        verdict = "INCONCLUSIVE"
    return verdict, {"part_outcomes": outcomes,
                     "note": ("Publisher grouping is a provenance diagnostic, not evidence of editorial or reporting independence. "
                              "Production verdict logic is not changed.")}


def _comparison_metrics(cases, output_cases, mode):
    expected = [case["expected_final_verdict"] for case in cases]
    predicted = [result["experimental_verdicts"][mode]["verdict"] for result in output_cases]
    errors = [{"case_id": case["case_id"], "expected": case["expected_final_verdict"],
               "predicted": result["experimental_verdicts"][mode]["verdict"], "tags": case["tags"]}
              for case, result in zip(cases, output_cases)
              if case["expected_final_verdict"] != result["experimental_verdicts"][mode]["verdict"]]
    by_error_tag = defaultdict(int)
    for error in errors:
        for tag in error["tags"]:
            by_error_tag[tag] += 1
    return {"verdict_metrics": classification_metrics(expected, predicted, LABELS),
            "selective_metrics": selective_metrics(expected, predicted),
            "verdict_distribution": dict(Counter(predicted)),
            "expected_distribution": dict(Counter(expected)),
            "error_counts_by_tag": dict(sorted(by_error_tag.items())),
            "errors": errors}


def _semantic_comparison(cases, output_cases):
    expected = [case["expected_final_verdict"] for case in cases]
    predicted = [result["experimental_semantic"]["verdict"] for result in output_cases]
    errors = [{"case_id": case["case_id"], "expected": case["expected_final_verdict"],
               "predicted": result["experimental_semantic"]["verdict"], "tags": case["tags"]}
              for case, result in zip(cases, output_cases)
              if case["expected_final_verdict"] != result["experimental_semantic"]["verdict"]]
    by_error_tag = defaultdict(int)
    for error in errors:
        for tag in error["tags"]:
            by_error_tag[tag] += 1
    expected_stance, effective_stance, raw_expected, raw_predicted = [], [], [], []
    expected_relevance, actual_relevance = [], []
    for case, result in zip(cases, output_cases):
        for evidence, assessed in zip(case["evidence"], result["experimental_semantic"]["evidence"]):
            components = assessed.get("part_assessments", [])
            first = components[0] if components else {}
            label = first.get("effective_label", "NOT ENOUGH INFORMATION")
            if label not in STANCE_LABELS:
                label = "NOT ENOUGH INFORMATION"
            expected_stance.append(evidence["expected_stance"])
            effective_stance.append(label)
            if first.get("model_label") in STANCE_LABELS:
                raw_expected.append(evidence["expected_stance"])
                raw_predicted.append(first["model_label"])
            expected_relevance.append(evidence["expected_relevance"])
            actual_relevance.append(assessed["actual_relevance"])
    return {"verdict_metrics": classification_metrics(expected, predicted, LABELS),
            "selective_metrics": selective_metrics(expected, predicted),
            "effective_passage_stance_metrics": classification_metrics(
                expected_stance, effective_stance, STANCE_LABELS),
            "raw_model_stance_metrics": classification_metrics(
                raw_expected, raw_predicted, STANCE_LABELS),
            "relevance_metrics": classification_metrics(
                expected_relevance, actual_relevance, RELEVANCE_LABELS),
            "verdict_distribution": dict(Counter(predicted)),
            "error_counts_by_tag": dict(sorted(by_error_tag.items())),
            "errors": errors}


def evaluate_cases(cases, predictor):
    """Evaluate fixed evidence. `predictor` is the existing premise/hypothesis callback."""
    output_cases = []
    expected_stance, predicted_stance = [], []
    expected_relevance, predicted_relevance = [], []
    raw_expected, raw_predicted = [], []
    for case in cases:
        items = [_result_item(case, evidence) for evidence in case["evidence"]]
        assessment = assess_evidence_nli(case["claim"], items, predictor)
        experimental_assessment = assess_evidence_nli(
            case["claim"], items, predictor, experimental_semantic=True)
        rows = []
        # Preserve input order: a URL-keyed map collapses duplicate URLs and
        # can assign one result's assessment to another annotated passage.
        for evidence, assessed in zip(case["evidence"], assessment["per_source"]):
            item = _result_item(case, evidence)
            part = assessed["part_assessments"][0] if assessed.get("part_assessments") else {}
            relevance_prediction = _actual_relevance(assessed.get("relevance", "Unrelated"))
            # For actual stance we score the final effective label after contextual,
            # date, confidence, margin, and duplicate gates; all abstentions map to NEI.
            effective = part.get("label", "NOT ENOUGH INFORMATION")
            if effective not in STANCE_LABELS:
                effective = "NOT ENOUGH INFORMATION"
            expected_stance.append(evidence["expected_stance"])
            predicted_stance.append(effective)
            expected_relevance.append(evidence["expected_relevance"])
            predicted_relevance.append(relevance_prediction)
            if part.get("model_label") in STANCE_LABELS:
                raw_expected.append(evidence["expected_stance"])
                raw_predicted.append(part["model_label"])
            rows.append({"evidence_id": evidence["evidence_id"],
                         "source_kind": evidence["source"]["kind"],
                         "title": evidence["source"]["title"],
                         "url": evidence["source"].get("url"),
                         "expected_relevance": evidence["expected_relevance"],
                         "actual_relevance": relevance_prediction,
                         "expected_stance": evidence["expected_stance"],
                         "raw_model_label": part.get("model_label"),
                         "model_confidence": part.get("confidence"),
                         "model_margin": part.get("margin"),
                         "effective_assessment": effective,
                         "contributed": bool(part.get("contributed")),
                         "passage_normalized": re.sub(r"\s+", " ", part.get("passage", "")).strip().casefold(),
                         "part_assessments": assessed.get("part_assessments", []),
                         "status": part.get("status", "No passage assessment")})
        actual_verdict = assessment["verdict"].upper()
        experimental = {}
        for mode in ("publisher_cap", "distinct_publishers"):
            verdict, detail = _experimental_verdict(case, rows, mode)
            experimental[mode] = {"verdict": verdict, **detail}
        experimental_evidence = []
        for evidence, assessed in zip(case["evidence"], experimental_assessment["per_source"]):
            part = assessed.get("part_assessments", [{}])[0]
            experimental_evidence.append({
                "evidence_id": evidence["evidence_id"],
                "source_kind": evidence["source"]["kind"],
                "title": evidence["source"]["title"],
                "url": evidence["source"].get("url"),
                "expected_relevance": evidence["expected_relevance"],
                "actual_relevance": _actual_relevance(assessed.get("relevance", "Unrelated")),
                "expected_stance": evidence["expected_stance"],
                "raw_model_label": part.get("model_label"),
                "effective_assessment": part.get("label", "NOT ENOUGH INFORMATION"),
                "contributed": bool(part.get("contributed")),
                "status": part.get("status", "No passage assessment"),
                "assessed_passage": part.get("passage"),
                "part_assessments": [{
                    "claim_part": assessment.get("claim_part"),
                    "model_label": assessment.get("model_label"),
                    "effective_label": assessment.get("label", "NOT ENOUGH INFORMATION"),
                    "confidence": assessment.get("confidence"),
                    "margin": assessment.get("margin"),
                    "contributed": bool(assessment.get("contributed")),
                    "status": assessment.get("status"),
                    "passage": assessment.get("passage"),
                } for assessment in assessed.get("part_assessments", [])],
            })
        output_cases.append({"case_id": case["case_id"], "split": case["split"],
                             "tags": case["tags"], "claim": case["claim"],
                             "annotation_notes": case.get("annotation_notes", ""),
                             "expected_final_verdict": case["expected_final_verdict"],
                             "actual_final_verdict": actual_verdict,
                             "reasoning": assessment["reasoning"], "evidence": rows,
                             "experimental_semantic": {
                                 "verdict": experimental_assessment["verdict"].upper(),
                                 "reasoning": experimental_assessment["reasoning"],
                                 "part_outcomes": experimental_assessment.get("part_outcomes", []),
                                 "evidence": experimental_evidence,
                             },
                             "experimental_verdicts": experimental,
                             "source_diversity": _source_diversity(case["evidence"], rows)})

    final_expected = [case["expected_final_verdict"] for case in cases]
    final_predicted = [case["actual_final_verdict"] for case in output_cases]
    by_tag = defaultdict(list)
    case_by_id = {case["case_id"]: case for case in cases}
    for result in output_cases:
        for tag in result["tags"]:
            by_tag[tag].append(result)
    directional_cases = [case for case in output_cases
                         if case["actual_final_verdict"] in ("SUPPORTED", "CONTRADICTED")]
    source_diversity_summary = {
        "directional_case_count": len(directional_cases),
        "cases_with_two_or_more_declared_publishers": sum(
            case["source_diversity"]["distinct_declared_publishers"] >= 2
            for case in directional_cases),
        "cases_with_one_declared_publisher": sum(
            case["source_diversity"]["distinct_declared_publishers"] == 1
            for case in directional_cases),
        "cases_with_no_public_publisher_annotation": sum(
            case["source_diversity"]["distinct_declared_publishers"] == 0
            for case in directional_cases),
        "independence_verified_for_any_case": False,
        "note": "Diagnostic only; this publisher summary never changes a verdict.",
    }
    stress = {}
    for tag, tagged in sorted(by_tag.items()):
        actual_map = {x["case_id"]: x["actual_final_verdict"] for x in tagged}
        expected_map = {x["case_id"]: case_by_id[x["case_id"]]["expected_final_verdict"] for x in tagged}
        stress[tag] = {"case_count": len(tagged), "passage_count": sum(len(x["evidence"]) for x in tagged),
                       "final_verdict_accuracy": sum(actual_map[k] == expected_map[k] for k in actual_map) / len(tagged)}
    return {
        "python_version": sys.version.split()[0],
        "model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "assessment_thresholds": {"confidence": MIN_CONFIDENCE, "margin": MIN_MARGIN,
                                  "directional_sources": MIN_DIRECTIONAL_SOURCES},
        "network_search_used": False,
        "case_count": len(cases),
        "case_counts_by_expected_verdict": dict(Counter(final_expected)),
        "passage_count": len(expected_stance),
        "passage_counts_by_expected_stance": dict(Counter(expected_stance)),
        "passage_counts_by_expected_relevance": dict(Counter(expected_relevance)),
        "metrics": {
            "final_verdict": classification_metrics(final_expected, final_predicted, LABELS),
            "selective": selective_metrics(final_expected, final_predicted),
            "effective_passage_stance": classification_metrics(expected_stance, predicted_stance, STANCE_LABELS),
            "raw_model_stance": classification_metrics(raw_expected, raw_predicted, STANCE_LABELS),
            "relevance": classification_metrics(expected_relevance, predicted_relevance, RELEVANCE_LABELS),
        },
        "aggregation_comparison": {
            "production_default": {
                "verdict_metrics": classification_metrics(final_expected, final_predicted, LABELS),
                "selective_metrics": selective_metrics(final_expected, final_predicted),
                "verdict_distribution": dict(Counter(final_predicted)),
                "expected_distribution": dict(Counter(final_expected)),
                "errors": [{"case_id": case["case_id"], "expected": case["expected_final_verdict"],
                            "predicted": result["actual_final_verdict"], "tags": case["tags"]}
                           for case, result in zip(cases, output_cases)
                           if case["expected_final_verdict"] != result["actual_final_verdict"]],
                "error_counts_by_tag": dict(sorted(Counter(
                    tag for case, result in zip(cases, output_cases)
                    if case["expected_final_verdict"] != result["actual_final_verdict"]
                    for tag in case["tags"]).items())),
            },
            "one_vote_per_normalized_publisher": _comparison_metrics(cases, output_cases, "publisher_cap"),
            "distinct_declared_publishers_only": _comparison_metrics(cases, output_cases, "distinct_publishers"),
            "note": "Experimental modes are evaluation-only. Publisher metadata and domains do not establish source independence; missing declared IDs cannot count in distinct-publisher mode.",
        },
        "semantic_interpretation_comparison": {
            "production_default": {
                "verdict_metrics": classification_metrics(final_expected, final_predicted, LABELS),
                "selective_metrics": selective_metrics(final_expected, final_predicted),
                "errors": [{"case_id": case["case_id"], "expected": case["expected_final_verdict"],
                            "predicted": result["actual_final_verdict"], "tags": case["tags"]}
                           for case, result in zip(cases, output_cases)
                           if case["expected_final_verdict"] != result["actual_final_verdict"]],
            },
            "experimental_semantic": _semantic_comparison(cases, output_cases),
            "note": "The experimental mode is opt-in in the assessor and evaluation-only in this report; production call sites use the unchanged default.",
        },
        "stress_groups": stress,
        "source_diversity": source_diversity_summary,
        "cases": output_cases,
        "metric_notes": [
            "Effective stance maps uncertain, context-excluded, duplicate-excluded, and unassessed passages to NOT ENOUGH INFORMATION.",
            "Raw model stance is scored only when the assessor emitted a recognized model_label; its denominator may be smaller.",
            "Passage-level stance metrics use the first assessed claim component; diagnostic examples also record every experimental component assessment, but component-specific gold labels are not yet annotated.",
            "Relevant includes the pipeline's Directly relevant candidate and Different time period diagnostics; the latter is separately visible in case notes.",
            "Synthetic fixtures are controlled probes, not real-world evidence. A .invalid URL is supplied internally only to exercise URL validation and is never a citation.",
            "Publisher diversity is descriptive metadata only; the evaluation cannot establish editorial independence and does not alter verdicts.",
            "Experimental publisher aggregation modes are post-hoc comparisons and do not alter the production assessment or its thresholds.",
            "Small, purpose-selected cases are pilot diagnostics, not an estimate of population accuracy."
        ]
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("development", "diagnostics", "held_out", "all"), default="held_out")
    parser.add_argument("--output", help="Optional path for a JSON report")
    args = parser.parse_args(argv)
    if args.split == "all":
        data_paths = [DATA_DIR / "development.jsonl", DATA_DIR / "diagnostics.jsonl", DATA_DIR / "held_out.jsonl"]
        cases = load_cases(data_paths[0]) + load_cases(data_paths[1])
    else:
        data_paths = [DATA_DIR / (args.split + ".jsonl")]
        cases = load_cases(data_paths[0])
    # Fail closed: no model download is attempted during this evaluation command.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        predictor = load_local_nli_model()
    except Exception as exc:
        report = {"status": "NOT MEASURED", "reason": "Local model unavailable in offline mode: " + type(exc).__name__ + ": " + str(exc),
                  "network_search_used": False, "split": args.split}
        rendered = json.dumps(report, indent=2, ensure_ascii=False)
        print(rendered)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        return 2
    report = evaluate_cases(cases, predictor)
    report["status"] = "MEASURED"
    report["split"] = args.split
    report["dataset_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in data_paths}
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
