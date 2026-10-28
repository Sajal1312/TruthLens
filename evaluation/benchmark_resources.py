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

from evaluation.run_evaluation import DATA_DIR, load_cases
from nli_assessor import MODEL_ID, MODEL_REVISION, load_local_nli_model


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
            "Peak RSS is the process high-water mark and includes Python, model loading, and inference; it is not inference-only memory.",
            "Peak RSS may not include all accelerator or unified-memory details, so treat it as a process-level estimate.",
            "Inference timings are local to this machine and run; they are not a comparison with a hosted service.",
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
