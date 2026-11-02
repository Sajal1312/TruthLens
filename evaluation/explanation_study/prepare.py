"""Prepare offline blinded packets and empty allocations; never collect responses."""
import argparse
from collections import Counter
from copy import deepcopy
import html
import json
from pathlib import Path
import random
import re
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator

from evaluation.compare_systems import ROOT, fingerprint, offline_only, sha256
from evaluation.run_evaluation import _result_item, load_cases

HERE = Path(__file__).resolve().parent
SPEC = HERE / "study_spec.json"
SOURCE = ROOT / "evaluation/results/comparison_2026-11-02/comparison.json"
TRACKS = {"current_rule_development": "development", "current_rule_diagnostics": "diagnostics"}
RATINGS = ("clarity", "usefulness", "limitations_help", "verdict_understanding", "reliance_without_checking")
PROMPTS = (
    "The explanation is clear.", "The explanation is useful for examining this claim.",
    "The presentation helps me identify limitations of the evidence.",
    "I understand why the displayed verdict was reached.",
    "I would rely on this assessment without checking the underlying evidence.",
)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")


def check_schema(value, schema_path):
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)


def load_materials():
    """Read only the named comparison and its two allowed development inputs."""
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    if spec["source_comparison"] != str(SOURCE.relative_to(ROOT)):
        raise ValueError("Unsupported source report; no arbitrary dataset access allowed")
    report = json.loads(SOURCE.read_text(encoding="utf-8"))
    data = {}
    for split in TRACKS.values():
        descriptor = next(row for row in report["dataset_inventory"] if row["id"] == split)
        path = ROOT / "evaluation/data" / (split + ".jsonl")
        if descriptor["sha256"] != sha256(path):
            raise ValueError("Stored comparison dataset checksum is stale: " + split)
        data[split] = {row["case_id"]: row for row in load_cases(path)}
    items, families, claims = [], set(), set()
    for selection in spec["items"]:
        track_name = selection["track"]
        if track_name not in TRACKS:
            raise ValueError("Only complete current rule-mode comparison tracks are allowed")
        track = report["verdict_tracks"][track_name]
        case = data[TRACKS[track_name]][selection["case_id"]]
        saved = next(row for row in track["cases"] if row["case_id"] == selection["case_id"])
        assessment = saved["production_assessment"]
        diagnostics = saved["enhanced_diagnostics"]
        results = [_result_item(case, row) for row in case["evidence"]]
        if (track["status"] != "MEASURED" or saved["baseline_verdict"] != saved["enhanced_verdict"]
                or diagnostics["claim"] != case["claim"] or diagnostics["verdict"] != assessment["verdict"]
                or fingerprint(results) != saved["evidence_fingerprint_both_conditions"]
                or fingerprint(assessment) != saved["assessment_fingerprint"]):
            raise ValueError("Stored claim/evidence/assessment pairing mismatch")
        if not all(isinstance(assessment.get(key), str) and assessment[key] for key in ("reasoning", "method", "limitations")):
            raise ValueError("Baseline explanation fields are unavailable; do not reconstruct them")
        normalized = re.sub(r"\W+", " ", case["claim"].casefold()).strip()
        if selection["family"] in families or normalized in claims:
            raise ValueError("Duplicate claim/family exposure in proposed item set")
        families.add(selection["family"])
        claims.add(normalized)
        items.append({"item_id": "I" + fingerprint(selection)[:12], "selection": selection,
                      "claim": case["claim"], "assessment": deepcopy(assessment), "diagnostics": deepcopy(diagnostics),
                      "evidence": [{"evidence_id": row["evidence_id"], "passage": row["passage"], "source": deepcopy(row["source"])} for row in case["evidence"]],
                      "evidence_sha256": fingerprint(results)})
    return spec, items


def _longest_run(values):
    longest = run = 0
    previous = None
    for value in values:
        run = run + 1 if value == previous else 1
        longest = max(longest, run)
        previous = value
    return longest


def generate_assignments(items, slots, seed):
    """Allocate empty slots, not people; complementary pairs balance every position."""
    if type(slots) is not int or slots < 4 or slots > 200 or slots % 2:
        raise ValueError("Use an even number of planned slots from 4 to 200")
    if len(items) < 2 or len(items) % 2:
        raise ValueError("Use an even number of distinct items")
    ids = [row["item_id"] for row in items]
    if len(set(ids)) != len(ids) or len({row["claim"].casefold().strip() for row in items}) != len(ids):
        raise ValueError("Duplicate item or claim")
    rng = random.Random(seed)
    assignments = []
    for block in range(slots // 2):
        order = list(ids)
        rng.shuffle(order)
        mask = ["baseline"] * (len(ids) // 2) + ["enhanced"] * (len(ids) // 2)
        while True:
            rng.shuffle(mask)
            if _longest_run(mask) <= 3:
                break
        for member in range(2):
            slot = "S" + fingerprint([seed, block, member, ids])[:10]
            trials = [{"trial_id": "T" + fingerprint([slot, item])[:12], "position": index + 1,
                       "item_id": item, "condition": condition if member == 0 else
                       ("enhanced" if condition == "baseline" else "baseline")}
                      for index, (item, condition) in enumerate(zip(order, mask))]
            assignments.append({"slot_id": slot, "block_id": "block-{0:03d}".format(block + 1), "trials": trials})
    validate_assignments(assignments, items)
    return assignments


def validate_assignments(assignments, items):
    ids = {row["item_id"] for row in items}
    slots, trial_ids, blocks = set(), set(), {}
    for assignment in assignments:
        if assignment["slot_id"] in slots:
            raise ValueError("Duplicate slot")
        slots.add(assignment["slot_id"])
        trials = assignment["trials"]
        if len(trials) != len(ids) or {row["item_id"] for row in trials} != ids:
            raise ValueError("Missing or duplicate claim exposure")
        if [row["position"] for row in trials] != list(range(1, len(ids) + 1)):
            raise ValueError("Invalid presentation order")
        if Counter(row["condition"] for row in trials) != {"baseline": len(ids) // 2, "enhanced": len(ids) // 2}:
            raise ValueError("Unbalanced slot")
        if _longest_run([row["condition"] for row in trials]) > 3:
            raise ValueError("Long unbalanced presentation run")
        for trial in trials:
            if trial["trial_id"] in trial_ids:
                raise ValueError("Duplicate trial ID")
            trial_ids.add(trial["trial_id"])
        blocks.setdefault(assignment["block_id"], []).append(assignment)
    for block in blocks.values():
        if len(block) != 2:
            raise ValueError("Incomplete assignment block")
        for left, right in zip(block[0]["trials"], block[1]["trials"]):
            if left["item_id"] != right["item_id"] or left["condition"] == right["condition"]:
                raise ValueError("Block is not complementary")


def questions_for(item, index, seed):
    """Draft trace/policy keys; independent review is explicitly still pending."""
    literacy = [
        ("Does an NLI confidence score establish the probability that a claim is true?",
         ["No. It is a model classification score, not a calibrated probability of truth.", "Yes. It is the probability the claim is true.", "Yes, whenever more than one URL is listed."], "Documented NLI score limitation, displayed in the shared notice"),
        ("Do different source URLs alone establish independent confirmations?",
         ["No. Source independence must be checked separately.", "Yes. Every distinct URL is an independent confirmation.", "Yes, when their titles differ."], "Documented source-independence limitation, displayed in the shared notice"),
        ("Does missing evidence by itself establish that a claim is false?",
         ["No. Missing evidence does not establish falsity.", "Yes. No evidence means the claim is false.", "Yes, if the system displays an explanation."], "Documented absence-of-evidence limitation, displayed in the shared notice"),
    ]
    text, options, basis = literacy[index % len(literacy)]
    proposed = {
        "reason": ("Which reason does the system itself record for its displayed verdict?",
                   [item["assessment"]["reasoning"], "It established the claim's truth by publisher popularity.", "It treated missing evidence alone as proof that the claim is false."],
                   "Exact recorded production reasoning string; not a factual gold verdict"),
        "limitation": (text, options, basis),
    }
    public, keys = {}, {}
    rng = random.Random(str(seed) + item["item_id"])
    for name, (prompt, choices, basis) in proposed.items():
        order = list(range(3))
        rng.shuffle(order)
        public[name] = {"prompt": prompt, "options": {chr(65 + pos): choices[choice] for pos, choice in enumerate(order)}}
        keys[name] = {"answer": chr(65 + order.index(0)), "basis": basis}
    return public, keys


def blank_response(version, bundle_id, assignment):
    return {"study_version": version, "bundle_id": bundle_id, "slot_id": assignment["slot_id"],
            "record_type": "blank_template", "consent": None,
            "responses": [{"trial_id": trial["trial_id"], "ratings": {name: None for name in RATINGS},
                           "answers": {"reason": None, "limitation": None}, "answer_confidence": None,
                           "elapsed_seconds": None, "timing_method": None, "timing_interrupted": None, "comment": ""}
                          for trial in assignment["trials"]]}


def _p(text):
    return "<p>" + html.escape(str(text), quote=True) + "</p>"


def _li(values):
    return "<ul>" + "".join("<li>" + html.escape(str(value), quote=True) + "</li>" for value in values) + "</ul>"


def _additional_notes(item):
    view = item["diagnostics"]
    parts = ["<section><h3>Additional reading notes</h3>",
             _p("These checks help inspect evidence. Only the recorded reason above states the system's decision explanation. Additional warnings do not change the verdict."),
             "<h4>Evidence excerpts</h4>"]
    for entry in view["entries"]:
        parts += [_p("Passage E{0}: recorded assessment {1}; counted: {2}".format(entry["source_index"] + 1, entry["label"], entry["contributed"])),
                  "<blockquote><mark>" + html.escape(entry["excerpt"]["text"], quote=True) + "</mark></blockquote>", _p(entry["excerpt"]["basis"]), _p(entry["status"])]
        if entry["model_label"]:
            parts.append(_p("Raw model assessment: {0}; score: {1}; margin: {2}. Scores are not probabilities of truth.".format(entry["model_label"], entry["confidence"], entry["margin"])))
    temporal = view["temporal"]
    parts += ["<h4>Time context</h4>", _p("Claim classification: " + temporal["claim"]["classification"]),
              _li([row["text"] for row in temporal["claim"]["expressions"]]),
              _li([row["message"] for row in temporal["warnings"]]), _p(temporal["limitations"])]
    independent = view["independence"]
    parts += ["<h4>Source relationships</h4>", _p("Source independence is not established by the number of URLs."),
              _li(["Passages {0}: {1}".format(", ".join("E" + str(index + 1) for index in group["members"]), group["reason"])
                   for group in independent["groups"] if len(group["members"]) > 1]), _p(independent["limitations"])]
    numerical = view["numerical"]
    quantities = ", ".join(row["text"] for row in numerical["claim"]["quantities"])
    parts += ["<h4>Numbers and scope</h4>", _p("Claim quantities: " + (quantities or "None extracted; this does not establish absence of quantities"))]
    for source in numerical["sources"]:
        extracted = ", ".join(row["text"] for row in source["extracted"]["quantities"])
        parts.append(_p("E{0} quantities: {1}".format(source["source_index"] + 1, extracted or "None extracted; comparisons may remain unresolved")))
    comparisons = [row for source in numerical["sources"] for row in source["comparisons"]]
    parts.append(_li([str(row.get("status")) + ": " + str(row.get("reason", row.get("explanation", "Inspect the matching context"))) for row in comparisons]))
    parts.append(_li([warning for source in numerical["sources"] for warning in source["quantifier_warnings"]]))
    parts += [_p(numerical["tolerance_policy"]), _p(numerical["limitations"])]
    uncertainty = view["uncertainty"]
    parts += ["<h4>Evidence limitations</h4>", _li(uncertainty["categories"]),
              _li([row["message"] + " (" + row["basis"] + ")" for row in uncertainty["findings"]]),
              _li(uncertainty["suggestions"]), _p(uncertainty["limitations"]), "</section>"]
    return "".join(parts)


def item_html(item, condition):
    assessment = item["assessment"]
    parts = ["<h3>Claim</h3>", _p(item["claim"]), "<h3>Displayed assessment: " + html.escape(assessment["verdict"]) + "</h3>",
             _p("Method: " + assessment["method"]), "<h4>Recorded reason</h4>", _p(assessment["reasoning"]),
             "<h4>Limitations</h4>", _p(assessment["limitations"]), "<h3>Saved evidence</h3>"]
    for index, evidence in enumerate(item["evidence"]):
        source = evidence["source"]
        synthetic = source["kind"] == "synthetic_fixture"
        parts += ["<section class='source'>", _p("E" + str(index + 1) + ": " + ("Constructed study passage (not a real-world citation)" if synthetic else source["title"]))]
        url = source.get("url")
        if not synthetic and isinstance(url, str) and urlsplit(url).scheme in {"https", "http"} and urlsplit(url).hostname and not urlsplit(url).username:
            escaped = html.escape(url, quote=True)
            parts.append('<p><a href="' + escaped + '" target="_blank" rel="noopener noreferrer">' + escaped + '</a></p>')
        parts += [_p("Publication date: " + str(source.get("published_date") or "Unknown; not inferred")),
                  "<blockquote>" + html.escape(evidence["passage"], quote=True) + "</blockquote>"]
        rows = assessment.get("per_source") or []
        row = rows[index] if index < len(rows) else {}
        for record in row.get("part_assessments") or [row]:
            parts += [_p("Recorded passage assessment: " + str(record.get("label", "Not recorded"))), _p(record.get("status", "No passage status recorded"))]
        parts.append("</section>")
    parts.append(_p("TruthLens is a preliminary evidence-assessment tool. NLI classification scores are not probabilities that a claim is true. Different URLs alone do not establish independent confirmations. Missing evidence does not establish falsity. Use the recorded reason to understand the verdict; inspect source context before relying on it."))
    if condition == "enhanced":
        parts.append(_additional_notes(item))
    elif condition != "baseline":
        raise ValueError("Unknown presentation condition")
    return "".join(parts)


FORM_SCRIPT = """
document.getElementById('download').addEventListener('click', () => {
  if (!document.getElementById('consent').checked) { alert('No file is exported without your voluntary consent. You may close this page.'); return; }
  const response = JSON.parse(document.getElementById('blank-response').textContent);
  response.record_type = 'participant_response'; response.consent = true;
  const numberOrNull = element => element.value === '' ? null : Number(element.value);
  for (const row of response.responses) {
    const card = document.getElementById(row.trial_id);
    for (const key of Object.keys(row.ratings)) row.ratings[key] = numberOrNull(card.querySelector('[data-rating="'+key+'"]'));
    for (const key of Object.keys(row.answers)) row.answers[key] = card.querySelector('[data-answer="'+key+'"]').value || null;
    row.answer_confidence = numberOrNull(card.querySelector('[data-confidence]'));
    if (row.answer_confidence !== null && (!Number.isInteger(row.answer_confidence) || row.answer_confidence < 0 || row.answer_confidence > 100)) { alert('Confidence must be a whole number from 0 to 100, or blank.'); return; }
    row.elapsed_seconds = numberOrNull(card.querySelector('[data-seconds]'));
    row.timing_method = row.elapsed_seconds === null ? null : 'facilitator_stopwatch';
    const timing = card.querySelector('[data-interrupted]').value;
    row.timing_interrupted = timing === '' ? null : timing === 'yes';
    if (row.elapsed_seconds === null) row.timing_interrupted = null;
    if (row.elapsed_seconds !== null && (!Number.isFinite(row.elapsed_seconds) || row.elapsed_seconds < 0 || row.elapsed_seconds > 7200 || row.timing_interrupted === null)) { alert('Facilitator timing needs valid seconds and interruption status, or leave seconds blank.'); return; }
    row.comment = card.querySelector('textarea').value;
  }
  const link = document.createElement('a'); const url = URL.createObjectURL(new Blob([JSON.stringify(response,null,2)+'\\n'], {type:'application/json'}));
  link.href=url; link.download=response.slot_id+'-response.json'; link.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
});
"""


def packet_html(assignment, items, questionnaire, template):
    parts = ["<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>",
             "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; connect-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-study-offline'; base-uri 'none'; form-action 'none'\">",
             "<title>Evidence explanation reading study</title><style>body{max-width:850px;margin:2rem auto;padding:0 1rem;font:17px/1.6 system-ui;color:#182432;background:#f6f8fb}article,section.source{background:white;border:1px solid #ccd4de;border-radius:8px;padding:1rem;margin:1rem 0}p,blockquote,li{white-space:pre-wrap;overflow-wrap:anywhere}mark{background:#fff0b3;color:#172130}label{display:block;margin:.7rem 0}select,input,textarea,button{font:inherit;max-width:100%}textarea{width:95%;min-height:5rem}button{padding:.7rem}h2{border-bottom:2px solid #b1c2d5}a{color:#174f92}</style><body>",
             "<h1>Evidence explanation reading study</h1>", _p("Your assignment code: " + assignment["slot_id"]),
             _p("Read the finalized participant information sheet first. View only this packet. Read tasks in order using the saved evidence; source links are for later checking. Leave any question blank if you prefer. No answers or feedback are shown during the study. Nothing is sent automatically; download and share only if you choose. This form does not save after the tab is closed."),
             "<label><input id='consent' type='checkbox'> I have read the information sheet, had the opportunity to ask questions, and voluntarily agree to take part.</label>",
             _p("Scale for all ratings: 1 strongly disagree; 2 disagree; 3 neither agree nor disagree; 4 agree; 5 strongly agree.")]
    for trial in assignment["trials"]:
        item = items[trial["item_id"]]
        parts += ["<article id='" + trial["trial_id"] + "'><h2>Task " + str(trial["position"]) + "</h2>", item_html(item, trial["condition"]), "<h3>Your assessment of the presentation</h3>"]
        for name, prompt in zip(RATINGS, PROMPTS):
            parts.append("<label>" + html.escape(prompt) + " <select data-rating='" + name + "'><option value=''>Skip / unanswered</option>" + "".join("<option value='{0}'>{0}</option>".format(value) for value in range(1, 6)) + "</select></label>")
        for name, question in questionnaire[item["item_id"]].items():
            question_id = trial["trial_id"] + "-question-" + name
            parts += ["<p id='" + question_id + "'>" + html.escape(question["prompt"], quote=True) + "</p>",
                      _li([letter + ". " + value for letter, value in question["options"].items()]),
                      "<label>Your answer: <select aria-labelledby='" + question_id + "' data-answer='" + name + "'><option value=''>Skip / unanswered</option><option>A</option><option>B</option><option>C</option></select></label>"]
        parts += ["<label>How confident are you (0–100) that your answer to the second question is correct? <input data-confidence type='number' min='0' max='100' step='1'></label>",
                  "<label>Optional comments (no personal information): <textarea maxlength='2000'></textarea></label>",
                  "<details><summary>Facilitator-only optional stopwatch record</summary><label>Measured task seconds: <input data-seconds type='number' min='0' max='7200'></label><label>Was timing interrupted? <select data-interrupted><option value=''>Not recorded</option><option value='no'>No</option><option value='yes'>Yes</option></select></label></details></article>"]
    encoded = json.dumps(template, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    parts += ["<button id='download' type='button'>Download my responses</button>", _p("No file is sent to the organizer automatically. You decide whether to share the download. Please do not retake the study using another code."),
              "<script type='application/json' id='blank-response'>" + encoded + "</script>",
              "<script nonce='study-offline'>" + FORM_SCRIPT + "</script></body></html>"]
    return "".join(parts)


def prepare_study(destination, *, slots=None, seed=None, information_sheet=None):
    if destination.exists():
        raise FileExistsError("Study destination already exists; never overwrite a frozen study")
    with offline_only():
        spec, item_list = load_materials()
        slots = spec["planned_slots"] if slots is None else slots
        seed = random.SystemRandom().randrange(2 ** 63) if seed is None else seed
        assignments = generate_assignments(item_list, slots, seed)
        information = HERE / "PARTICIPANT_INFORMATION.md" if information_sheet is None else information_sheet
        information_bytes = information.read_bytes()
        framework = {name: sha256(HERE / name) for name in (
            "prepare.py", "analyze.py", "response.schema.json", "key_review.schema.json",
            "PROTOCOL.md", "ANALYSIS_PLAN.md", "QUESTIONNAIRE.md", "PARTICIPANT_INFORMATION.md")}
        bundle_id = "B" + fingerprint([spec, sha256(SOURCE), slots, seed, framework, sha256(information)])[:16]
        questionnaire, keys = {}, {}
        for index, item in enumerate(item_list):
            questionnaire[item["item_id"]], keys[item["item_id"]] = questions_for(item, index, seed)
        destination.mkdir(parents=True, exist_ok=False)
        (destination / "responses").mkdir()
        for name in ("response.schema.json", "key_review.schema.json", "PROTOCOL.md", "ANALYSIS_PLAN.md"):
            path = destination / "private" / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes((HERE / name).read_bytes())
        for name in ("PARTICIPANT_INFORMATION.md", "QUESTIONNAIRE.md"):
            path = destination / "public" / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(information_bytes if name == "PARTICIPANT_INFORMATION.md" else (HERE / name).read_bytes())
        write_json(destination / "private/assignments.json", assignments)
        write_json(destination / "private/materials.json", item_list)
        write_json(destination / "private/questionnaire.json", questionnaire)
        write_json(destination / "private/answer_keys.json", {"study_version": spec["study_version"], "bundle_id": bundle_id,
                                                             "validation_status": "pending_independent_review", "items": keys})
        write_json(destination / "private/key_reviews.json", [])
        write_json(destination / "private/study_spec.json", spec)
        for assignment in assignments:
            template = blank_response(spec["study_version"], bundle_id, assignment)
            check_schema(template, HERE / "response.schema.json")
            folder = destination / "public/slots" / assignment["slot_id"]
            write_json(folder / "blank_response.json", template)
            (folder / "packet.html").write_text(packet_html(assignment, {item["item_id"]: item for item in item_list}, questionnaire, template), encoding="utf-8")
        immutable = [path for path in destination.rglob("*") if path.is_file() and path.name != "key_reviews.json"]
        manifest = {"study_version": spec["study_version"], "bundle_id": bundle_id, "assignment_seed": seed,
                    "planned_slots": slots, "item_count": len(item_list), "planned_trials": slots * len(item_list),
                    "actual_participants": 0, "status": "Preparation only; no participants or responses generated",
                    "source_report_sha256": sha256(SOURCE), "spec_sha256": sha256(SPEC), "preparation_code_sha256": sha256(Path(__file__)),
                    "framework_sha256": framework, "information_sha256": sha256(information),
                    "information_status": "Custom sheet supplied; independent readiness verification still required" if information_sheet is not None else "Unfinalized template; complete before conducting and prepare a new bundle",
                    "files_sha256": {str(path.relative_to(destination)): sha256(path) for path in sorted(immutable)},
                    "readiness": ["Finalize consent/contact/retention and applicable institutional approval", "Independently review material families, keys and distractors", "Distribute individual packets only; never share private mapping or keys"]}
        write_json(destination / "private/manifest.json", manifest)
        return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--slots", type=int, help="Even planned allocation count; not actual participants")
    parser.add_argument("--seed", type=int, help="Explicit replay seed; omitted uses local random entropy, recorded privately")
    parser.add_argument("--information-sheet", type=Path, help="Organizer-finalized neutral information sheet, frozen into this bundle")
    args = parser.parse_args(argv)
    manifest = prepare_study(args.output_dir, slots=args.slots, seed=args.seed, information_sheet=args.information_sheet)
    print(json.dumps({key: manifest[key] for key in ("study_version", "bundle_id", "planned_slots", "item_count", "actual_participants", "status", "readiness")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
