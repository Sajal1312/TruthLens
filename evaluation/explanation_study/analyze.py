"""Validate future real responses and analyze without manufacturing observations."""
import argparse
from collections import Counter
from datetime import datetime
import json
import math
from pathlib import Path
import random
from statistics import mean, median

from jsonschema import Draft202012Validator, FormatChecker

from evaluation.compare_systems import fingerprint, sha256
from evaluation.explanation_study.prepare import RATINGS, validate_assignments, write_json


def read_bundle(bundle):
    manifest = json.loads((bundle / "private/manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["files_sha256"].items():
        relative = Path(name)
        path = bundle / relative
        if relative.is_absolute() or ".." in relative.parts or path.is_symlink() or not path.resolve().is_relative_to(bundle.resolve()):
            raise ValueError("Unsafe bundle reference")
        if not path.is_file() or sha256(path) != expected:
            raise ValueError("Frozen study integrity mismatch: " + name)
    assignments = json.loads((bundle / "private/assignments.json").read_text(encoding="utf-8"))
    items = json.loads((bundle / "private/materials.json").read_text(encoding="utf-8"))
    validate_assignments(assignments, items)
    if manifest["planned_slots"] != len(assignments) or manifest["item_count"] != len(items):
        raise ValueError("Manifest allocation counts mismatch")
    return manifest, assignments


def validate_response(response, manifest, assignments, schema):
    Draft202012Validator(schema).validate(response)
    if response["study_version"] != manifest["study_version"] or response["bundle_id"] != manifest["bundle_id"]:
        raise ValueError("Response version/bundle mismatch")
    slots = {row["slot_id"]: row for row in assignments}
    if response["slot_id"] not in slots:
        raise ValueError("Unknown assignment slot")
    allowed = {trial["trial_id"] for trial in slots[response["slot_id"]]["trials"]}
    seen = set()
    for row in response["responses"]:
        if row["trial_id"] not in allowed or row["trial_id"] in seen:
            raise ValueError("Unknown or duplicate trial ID")
        seen.add(row["trial_id"])
        if row["elapsed_seconds"] is None:
            if row["timing_method"] is not None or row["timing_interrupted"] is not None:
                raise ValueError("Timing context without a time")
        elif row["timing_method"] != "facilitator_stopwatch" or type(row["timing_interrupted"]) is not bool:
            raise ValueError("Time must have explicit stopwatch method and interruption status")
        if row["elapsed_seconds"] is not None and not math.isfinite(row["elapsed_seconds"]):
            raise ValueError("Non-finite time is invalid")
        if response["record_type"] == "blank_template" and _has_data(row):
            raise ValueError("A blank template cannot contain participant answers")
    return response


def key_review_status(bundle, manifest):
    keys_path = bundle / "private/answer_keys.json"
    keys = json.loads(keys_path.read_text(encoding="utf-8"))
    review_path = bundle / "private/key_reviews.json"
    if not review_path.exists():
        return False, keys, "No independent key-review file"
    reviews = json.loads(review_path.read_text(encoding="utf-8"))
    schema = json.loads((bundle / "private/key_review.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(reviews)
    identities = set()
    for record in reviews:
        if not record["reviewer_alias"].strip() or not record["rationale"].strip():
            raise ValueError("Key reviewer alias and rationale must not be blank")
        if record["reviewer_alias"] in identities:
            raise ValueError("Duplicate or conflicting key reviewer records")
        identities.add(record["reviewer_alias"])
        if record["keys_sha256"] != sha256(keys_path) or record["study_version"] != manifest["study_version"]:
            raise ValueError("Key review does not match frozen keys")
        if datetime.fromisoformat(record["reviewed_at"].replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("Key review timestamp needs a time zone")
    verified = bool(reviews) and all(record["decision"] == "verified" for record in reviews)
    return verified, keys, "Declared independent human review matched frozen keys" if verified else "Independent verification pending or a revision was requested"


def descriptive(values):
    return {"n": len(values), "mean": mean(values) if values else None, "median": median(values) if values else None}


def _percentile(values, fraction):
    position = (len(values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def block_interval(block_values, settings, outcome):
    values = list(block_values)
    result = {"level": 0.95, "complete_blocks": len(values), "low": None, "high": None,
              "estimand": "Mean within-slot difference averaged within complete counterbalance blocks; conditional on the fixed item set"}
    if len(values) < settings["minimum_complete_blocks"]:
        return dict(result, status="NOT ESTIMATED", reason="Too few complete counterbalance blocks")
    if len(set(values)) < 2:
        return dict(result, status="NOT ESTIMATED", reason="No between-block variation; avoid an unjustified zero-width interval")
    rng = random.Random(str(settings["seed"]) + outcome)
    bootstrap = sorted(mean(rng.choice(values) for _ in values) for _ in range(settings["repetitions"]))
    return dict(result, status="EXPLORATORY", low=_percentile(bootstrap, 0.025), high=_percentile(bootstrap, 0.975),
                repeats=settings["repetitions"], seed=settings["seed"], reason="Block bootstrap, not independent-trial inference or population-wide generalization")


def rating_summary(rows, field, assignments, settings):
    conditions = {}
    for condition in ("baseline", "enhanced"):
        selected = [row for row in rows if row["condition"] == condition]
        values = [row["ratings"][field] for row in selected if row["ratings"][field] is not None]
        conditions[condition] = dict(descriptive(values), missing=len(selected) - len(values))
    contrasts, complete = {}, {}
    for assignment in assignments:
        slot_rows = [row for row in rows if row["slot_id"] == assignment["slot_id"]]
        values = {condition: [row["ratings"][field] for row in slot_rows
                              if row["condition"] == condition and row["ratings"][field] is not None]
                  for condition in ("baseline", "enhanced")}
        if all(values.values()):
            contrast = mean(values["enhanced"]) - mean(values["baseline"])
            contrasts[assignment["slot_id"]] = contrast
            if len(slot_rows) == len(assignment["trials"]) and all(row["ratings"][field] is not None for row in slot_rows):
                complete.setdefault(assignment["block_id"], []).append(contrast)
    block_values = [mean(values) for values in complete.values() if len(values) == 2]
    a, b = conditions["baseline"]["mean"], conditions["enhanced"]["mean"]
    return {"by_condition": conditions, "difference_of_condition_means": b - a if a is not None and b is not None else None,
            "within_slot_differences": descriptive(list(contrasts.values())),
            "complete_block_contrast": descriptive(block_values), "interval": block_interval(block_values, settings, field)}


def _has_data(row):
    return any(value is not None for value in list(row["ratings"].values()) + list(row["answers"].values()) +
               [row["answer_confidence"], row["elapsed_seconds"]]) or bool(row["comment"])


def analyze_study(bundle, responses_dir=None):
    manifest, assignments = read_bundle(bundle)
    directory = bundle / "responses" if responses_dir is None else responses_dir
    if not directory.is_dir():
        raise ValueError("Response directory does not exist")
    schema = json.loads((bundle / "private/response.schema.json").read_text(encoding="utf-8"))
    received, seen, ignored_templates, declined = {}, set(), 0, 0
    for path in sorted(directory.glob("*.json")):
        response = validate_response(json.loads(path.read_text(encoding="utf-8")), manifest, assignments, schema)
        if response["record_type"] == "blank_template":
            ignored_templates += 1
            continue
        if response["slot_id"] in seen:
            raise ValueError("Duplicate response slot; originals must not be silently merged")
        seen.add(response["slot_id"])
        if response["consent"] is not True:
            declined += 1
            continue
        received[response["slot_id"]] = response
    rows = []
    for assignment in assignments:
        response = received.get(assignment["slot_id"])
        if response is None:
            continue
        by_trial = {row["trial_id"]: row for row in response["responses"]}
        for trial in assignment["trials"]:
            row = dict(by_trial.get(trial["trial_id"], {}))
            # No imputation: an absent trial contributes nulls and missing counts.
            row.setdefault("ratings", {field: None for field in RATINGS})
            row.setdefault("answers", {field: None for field in ("reason", "limitation")})
            for field in ("answer_confidence", "elapsed_seconds", "timing_method", "timing_interrupted"):
                row.setdefault(field, None)
            row.setdefault("comment", "")
            row.update(slot_id=assignment["slot_id"], item_id=trial["item_id"], condition=trial["condition"])
            rows.append(row)
    spec = json.loads((bundle / "private/study_spec.json").read_text(encoding="utf-8"))
    verified, keys, review_note = key_review_status(bundle, manifest)
    objective = {"status": "MEASURED" if received and verified else "NOT MEASURED", "key_review": review_note, "by_condition": {}}
    for condition in ("baseline", "enhanced"):
        selected = [row for row in rows if row["condition"] == condition]
        quiz = {}
        for question in ("reason", "limitation"):
            answered = [row for row in selected if row["answers"][question] is not None]
            correct = sum(row["answers"][question] == keys["items"][row["item_id"]][question]["answer"] for row in answered) if verified else None
            quiz[question] = {"answered": len(answered), "missing": len(selected) - len(answered), "correct": correct,
                              "accuracy": correct / len(answered) if verified and answered else None}
        calibrated = [row for row in selected if row["answers"]["limitation"] is not None and row["answer_confidence"] is not None]
        brier = mean((row["answer_confidence"] / 100 - int(row["answers"]["limitation"] == keys["items"][row["item_id"]]["limitation"]["answer"])) ** 2 for row in calibrated) if verified and calibrated else None
        objective["by_condition"][condition] = {"questions": quiz, "calibration": {
            "n": len(calibrated), "brier_score": brier,
            "mean_confidence": mean(row["answer_confidence"] / 100 for row in calibrated) if calibrated else None,
            "accuracy": mean(row["answers"]["limitation"] == keys["items"][row["item_id"]]["limitation"]["answer"] for row in calibrated) if verified and calibrated else None,
            "interpretation": "Quiz-answer calibration only; no factual truth calibration is established"}}
    timing = {}
    for condition in ("baseline", "enhanced"):
        selected = [row for row in rows if row["condition"] == condition]
        usable = [row["elapsed_seconds"] for row in selected if row["elapsed_seconds"] is not None and row["timing_method"] == "facilitator_stopwatch" and row["timing_interrupted"] is False]
        timing[condition] = dict(descriptive(usable), excluded_or_unmeasured=len(selected) - len(usable),
                                 interpretation="Facilitator-reported uninterrupted stopwatch times only; not independently instrumented")
    return {
        "study_version": manifest["study_version"], "bundle_id": manifest["bundle_id"],
        "status": "Study not yet conducted" if not received else "Exploratory participant responses available",
        "counts": {"planned_slots": len(assignments), "consenting_response_files": len(received),
                   "slots_without_consenting_response": len(assignments) - len(received),
                   "planned_trials": manifest["planned_trials"], "trials_with_any_response": sum(bool(_has_data(row)) for row in rows),
                   "planned_trials_without_any_response": manifest["planned_trials"] - sum(bool(_has_data(row)) for row in rows),
                   "trials_in_consenting_allocations": len(rows), "ignored_blank_templates": ignored_templates,
                   "nonconsenting_files_excluded": declined, "condition_trial_counts": dict(Counter(row["condition"] for row in rows))},
        "ratings": {field: rating_summary(rows, field, assignments, spec["confidence_intervals"]) for field in RATINGS},
        "objective_comprehension": objective, "timing_seconds": timing,
        "integrity": "Frozen material checksums verified; response authenticity and reviewer independence remain human responsibilities",
        "limitations": spec["limitations"] + ["Ordinal summaries and within-slot contrasts are exploratory; missing data can change composition", "Intervals require complete paired allocation blocks and condition on these fixed claims; they do not estimate generalization to new claims", "No subjective rating demonstrates factual correctness or verdict accuracy"],
    }


def render_analysis(report):
    lines = ["# Explanation reading study analysis", "", "**" + report["status"] + "**", "",
             "Consenting response files: " + str(report["counts"]["consenting_response_files"]) + "; planned unfilled/filled slots: " + str(report["counts"]["planned_slots"]) + ".",
             "No values are imputed. No participant response is generated by preparation or analysis.", "",
             "| Rating | Baseline n / mean / median | Other presentation n / mean / median | Mean difference |", "|---|---|---|---|"]
    def fmt(value):
        return "not measured" if value is None else str(round(value, 3)) if isinstance(value, float) else str(value)
    for name, scores in report["ratings"].items():
        a, b = scores["by_condition"]["baseline"], scores["by_condition"]["enhanced"]
        lines.append("| {0} | {1} / {2} / {3} | {4} / {5} / {6} | {7} |".format(name, a["n"], fmt(a["mean"]), fmt(a["median"]), b["n"], fmt(b["mean"]), fmt(b["median"]), fmt(scores["difference_of_condition_means"])))
    lines += ["", "Objective comprehension: " + report["objective_comprehension"]["status"] + ". " + report["objective_comprehension"]["key_review"],
              "Complete-block contrast intervals, missing counts, quiz calibration and optional timing denominators are in analysis.json. With no responses, all estimates are null. Unverified keys suppress objective results.", "", "## Limitations", ""]
    lines += ["- " + note for note in report["limitations"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--responses", type=Path, help="Directory containing explicitly supplied real response exports")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError("Never overwrite an analysis report")
    report = analyze_study(args.bundle, args.responses)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_json(args.output_dir / "analysis.json", report)
    (args.output_dir / "REPORT.md").write_text(render_analysis(report), encoding="utf-8")
    print(report["status"] + "; consenting responses: " + str(report["counts"]["consenting_response_files"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
