#!/usr/bin/env python3
"""Offline timing and process-memory benchmark for TruthLens' local NLI model.

No Tavily configuration is read and no network search is performed. The model
must already be cached; Hugging Face is forced into offline mode.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.run_evaluation import DATA_DIR, _result_item, load_cases
from nli_assessor import (MODEL_ID, MODEL_REVISION, assess_evidence_nli,
                          load_local_nli_model)


def _normalize_peak_rss_bytes(raw_value, platform_name):
    """macOS reports ru_maxrss in bytes; Linux and the common BSDs use KiB."""
    return int(raw_value if platform_name == "darwin" else raw_value * 1024)


def _latency_summary(samples_seconds):
    milliseconds = [value * 1000 for value in samples_seconds]
    return {
        "sample_count": len(milliseconds),
        "min_ms": min(milliseconds) if milliseconds else None,
        "median_ms": statistics.median(milliseconds) if milliseconds else None,
        "mean_ms": statistics.mean(milliseconds) if milliseconds else None,
        "max_ms": max(milliseconds) if milliseconds else None,
    }


def _predictions_match(individual, batched):
    """Compare labels and probability outputs without rounding differences."""
    if len(individual) != len(batched):
        return False
    for left, right in zip(individual, batched):
        if left.get("label") != right.get("label"):
            return False
        left_scores, right_scores = left.get("scores", {}), right.get("scores", {})
        if set(left_scores) != set(right_scores):
            return False
        if any(abs(float(left_scores[key]) - float(right_scores[key])) > 1e-5
               for key in left_scores):
            return False
    return True


def _assessment_signature(assessment):
    """Fields that must stay identical when only the inference cache changes."""
    source_signatures = []
    for row in assessment.get("per_source", []):
        parts = []
        for part in row.get("part_assessments", []):
            parts.append(tuple(part.get(key) for key in (
                "claim_part", "label", "predicted_label", "model_label", "confidence",
                "margin", "scores", "passage", "contributed", "status")))
        source_signatures.append((row.get("title"), row.get("url"), row.get("label"),
                                  row.get("status"), tuple(parts)))
    return (assessment.get("verdict"), assessment.get("reasoning"),
            tuple(assessment.get("evidence_used", [])), tuple(source_signatures),
            tuple((part.get("claim_part"), part.get("verdict"))
                  for part in assessment.get("part_outcomes", [])))


def _cache_comparison(predictor, split):
    """Compare per-verification exact-input caching on fixed offline passages."""
    cases = load_cases(DATA_DIR / (split + ".jsonl"))
    uncached_calls = cached_calls = cache_hits = passage_count = 0
    uncached_wall, cached_wall, mismatches = [], [], []
    for case in cases:
        items = [_result_item(case, item) for item in case["evidence"]]
        passage_count += len(items)
        uncached_timings, cached_timings = {}, {}
        started = time.perf_counter()
        uncached = assess_evidence_nli(case["claim"], items, predictor, timings=uncached_timings)
        uncached_wall.append(time.perf_counter() - started)
        started = time.perf_counter()
        cached = assess_evidence_nli(case["claim"], items, predictor,
                                     cache_predictions=True, timings=cached_timings)
        cached_wall.append(time.perf_counter() - started)
        uncached_calls += uncached_timings.get("nli_model_calls", 0)
        cached_calls += cached_timings.get("nli_model_calls", 0)
        cache_hits += cached_timings.get("nli_cache_hits", 0)
        if _assessment_signature(uncached) != _assessment_signature(cached):
            mismatches.append(case["case_id"])
    reduction = ((uncached_calls - cached_calls) / uncached_calls
                 if uncached_calls else 0.0)
    return {
        "split": split,
        "claim_count": len(cases),
        "passage_count": passage_count,
        "uncached_predictor_calls": uncached_calls,
        "cached_predictor_calls": cached_calls,
        "exact_pair_cache_hits": cache_hits,
        "predictor_call_reduction_fraction": reduction,
        "uncached_assessment_latency": _latency_summary(uncached_wall),
        "cached_assessment_latency": _latency_summary(cached_wall),
        "assessment_outputs_match": not mismatches,
        "mismatched_case_ids": mismatches,
        "note": "Same-run exact premise/hypothesis prediction reuse only. No results persist across claims or searches; source-specific context checks and verdict aggregation run again for every source.",
    }


def _representative_pairs():
    cases = load_cases(DATA_DIR / "development.jsonl")
    wanted = ("dev_earth_orbit_support", "dev_historical_belief", "dev_qualified_frame")
    by_id = {case["case_id"]: case for case in cases}
    pairs = []
    for case_id in wanted:
        case = by_id[case_id]
        evidence = next((entry for entry in case["evidence"]
                         if entry["source"].get("kind") == "public_excerpt"), None)
        if evidence:
            pairs.append({"case_id": case_id, "premise": evidence["passage"],
                          "hypothesis": case["claim"]})
    if len(pairs) != len(wanted):
        raise RuntimeError("The development resource probes are incomplete.")
    return pairs


def _fixed_batch_pairs(limit=32):
    """Use a larger deduplicated sample of labeled fixed passages, never Tavily."""
    pairs, seen = [], set()
    for split in ("development", "diagnostics"):
        for case in load_cases(DATA_DIR / (split + ".jsonl")):
            for evidence in case["evidence"]:
                premise, hypothesis = evidence["passage"], case["claim"]
                key = (premise, hypothesis)
                if key in seen:
                    continue
                seen.add(key)
                pairs.append({"case_id": case["case_id"], "premise": premise,
                              "hypothesis": hypothesis})
                if len(pairs) >= limit:
                    return pairs
    return pairs


def run_benchmark(repeats=5, predictor_loader=None):
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    loader = predictor_loader or load_local_nli_model
    load_started = time.perf_counter()
    predictor = loader()
    model_load_seconds = time.perf_counter() - load_started
    pairs = _representative_pairs()

    # One untimed pass lets tokenizer/device initialization finish. Report this
    # separately from repeated steady-state inference timings.
    for pair in pairs:
        predictor(pair["premise"], pair["hypothesis"])

    batch_predictor = getattr(predictor, "predict_batch", None)
    batch_comparison = {"status": "NOT AVAILABLE",
                        "reason": "The predictor does not expose a batch inference function."}
    if callable(batch_predictor):
        inputs = [(pair["premise"], pair["hypothesis"])
                  for pair in _fixed_batch_pairs()]
        if len(inputs) < 16:
            raise RuntimeError("The fixed evaluation corpus has too few distinct input pairs for batch comparison.")
        # Warm sequential and batch shapes before timing; compare the same 32
        # unique passage/claim pairs at each batch size.
        individual_reference = [predictor(*item) for item in inputs]
        batch_sizes = [size for size in (1, 2, 4, 8, 16) if size <= len(inputs)]
        warmup_matches = {}
        for size in batch_sizes:
            warm_batch = []
            for start in range(0, len(inputs), size):
                warm_batch.extend(batch_predictor(inputs[start:start + size]))
            warmup_matches[size] = _predictions_match(individual_reference, warm_batch)
        sequential_samples = []
        batch_samples = {size: [] for size in batch_sizes}
        batch_equivalence = {size: True for size in batch_sizes}
        batch_rss_highwater = {size: [] for size in batch_sizes}
        for _ in range(repeats):
            started = time.perf_counter()
            individual = [predictor(*item) for item in inputs]
            sequential_samples.append(time.perf_counter() - started)
            for size in batch_sizes:
                started = time.perf_counter()
                batched = []
                for start in range(0, len(inputs), size):
                    batched.extend(batch_predictor(inputs[start:start + size]))
                batch_samples[size].append(time.perf_counter() - started)
                batch_equivalence[size] = batch_equivalence[size] and _predictions_match(individual, batched)
                batch_rss_highwater[size].append(_normalize_peak_rss_bytes(
                    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, sys.platform))
        batch_comparison = {
            "status": "MEASURED",
            "input_pair_count": len(inputs),
            "sequential_forward_calls_per_repeat": len(inputs),
            "sequential_latency": _latency_summary(sequential_samples),
            "score_tolerance": 1e-5,
            "warmup_predictions_match_by_batch_size": {
                str(size): warmup_matches[size] for size in batch_sizes
            },
            "by_batch_size": {
                str(size): {
                    "forward_calls_per_repeat": (len(inputs) + size - 1) // size,
                    "latency": _latency_summary(batch_samples[size]),
                    "predictions_match_all_sequential_runs": batch_equivalence[size],
                    "process_rss_highwater_bytes_after_batch_runs": max(batch_rss_highwater[size]),
                }
                for size in batch_sizes
            },
            "experimental_only": True,
            "note": "Model-only comparison on fixed development and diagnostic passages; the Streamlit assessment pipeline remains sequential.",
        }

    per_probe = []
    all_samples = []
    for pair in pairs:
        samples = []
        for _ in range(repeats):
            started = time.perf_counter()
            predictor(pair["premise"], pair["hypothesis"])
            samples.append(time.perf_counter() - started)
        all_samples.extend(samples)
        per_probe.append({"case_id": pair["case_id"], "latency": _latency_summary(samples)})

    import torch
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    raw_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "status": "MEASURED",
        "network_search_used": False,
        "model_download_allowed": False,
        "model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "run_count": repeats * len(pairs),
        "repeats_per_probe": repeats,
        "probe_count": len(pairs),
        "warmup_inferences": len(pairs),
        "model_load_seconds": model_load_seconds,
        "inference_latency_all_probes": _latency_summary(all_samples),
        "per_probe": per_probe,
        "batch_comparison": batch_comparison,
        "offline_assessment_cache_comparison": {
            "status": "MEASURED",
            "development": _cache_comparison(predictor, "development"),
            "diagnostics": _cache_comparison(predictor, "diagnostics"),
        },
        "end_to_end_verification": {
            "status": "NOT MEASURED",
            "reason": "This benchmark times model loading and predictor calls only; it does not measure Tavily, relevance filtering, or complete claim aggregation.",
        },
        "timing_methodology": "perf_counter wall-clock timing; model loader duration includes local initialization; one untimed predictor call per probe warms each input; reported inference values are repeated predictor calls only.",
        "peak_process_rss_bytes_since_process_start": _normalize_peak_rss_bytes(raw_peak, sys.platform),
        "hardware": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor() or "Not reported by Python",
            "python_version": platform.python_version(),
            "torch_version": torch.__version__,
            "inference_device": device,
        },
        "energy": {"status": "NOT MEASURED", "reason": "No reliable energy telemetry tool is configured."},
        "interpretation": [
            "Peak RSS is the process high-water mark after the sequential, batch, and cached-assessment probes. It includes Python, model loading, and inference; it is not inference-only memory and is not directly comparable with older benchmark runs that did not execute all these probes.",
            "Peak RSS may not include all accelerator or unified-memory details, so treat it as a process-level estimate.",
            "Inference timings are local to this machine and run; they are not a comparison with a hosted service.",
            "Batch comparison is model-only and does not demonstrate end-to-end application speedup.",
            "Local execution does not by itself establish lower energy use or carbon emissions.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5, help="Timed repetitions per representative input (default: 5)")
    parser.add_argument("--output", help="Optional output JSON path")
    args = parser.parse_args(argv)
    try:
        report = run_benchmark(args.repeats)
    except Exception as exc:
        report = {"status": "NOT MEASURED", "reason": type(exc).__name__ + ": " + str(exc),
                  "network_search_used": False, "model_download_allowed": False,
                  "energy": {"status": "NOT MEASURED"}}
        exit_code = 2
    else:
        exit_code = 0
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
