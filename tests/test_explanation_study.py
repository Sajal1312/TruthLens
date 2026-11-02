"""Synthetic response tests live only in temporary directories, never real study data."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from html.parser import HTMLParser

from jsonschema import ValidationError
import pytest

from evaluation.explanation_study import analyze, prepare


@pytest.fixture
def bundle(tmp_path):
    path = tmp_path / "synthetic-test-study"
    prepare.prepare_study(path, slots=4, seed=42)
    return path


def structure(bundle):
    manifest, assignments = analyze.read_bundle(bundle)
    schema = json.loads((bundle / "private/response.schema.json").read_text())
    return manifest, assignments, schema


def test_assignment_reproduction_balance_and_unique_claims():
    _spec, items = prepare.load_materials()
    first = prepare.generate_assignments(items, 24, 20261102)
    assert first == prepare.generate_assignments(items, 24, 20261102)
    assert first != prepare.generate_assignments(items, 24, 20261103)
    counts = Counter()
    positions = Counter()
    for slot in first:
        assert len({row["item_id"] for row in slot["trials"]}) == 12
        assert Counter(row["condition"] for row in slot["trials"]) == {"baseline": 6, "enhanced": 6}
        for trial in slot["trials"]:
            counts[trial["item_id"], trial["condition"]] += 1
            positions[trial["position"], trial["condition"]] += 1
    assert set(counts.values()) == {12} and set(positions.values()) == {12}


@pytest.mark.parametrize("slots", [0, 1, 3, 201, True])
def test_invalid_planned_slot_count_rejected(slots):
    _spec, items = prepare.load_materials()
    with pytest.raises(ValueError, match="even number"):
        prepare.generate_assignments(items, slots, 1)


def test_repeated_claims_and_broken_counterbalance_rejected():
    _spec, items = prepare.load_materials()
    repeated = deepcopy(items)
    repeated[1]["claim"] = repeated[0]["claim"]
    with pytest.raises(ValueError, match="Duplicate"):
        prepare.generate_assignments(repeated, 4, 1)
    assignments = prepare.generate_assignments(items, 4, 1)
    assignments[1]["trials"][0]["item_id"] = assignments[1]["trials"][1]["item_id"]
    with pytest.raises(ValueError, match="exposure"):
        prepare.validate_assignments(assignments, items)


def test_complete_materials_are_frozen_and_not_gold_annotations():
    _spec, items = prepare.load_materials()
    assert len(items) == 12 and len({row["selection"]["family"] for row in items}) == 12
    assert {row["assessment"]["verdict"] for row in items} == {"Inconclusive"}
    for item in items:
        assert "expected_final_verdict" not in item
        assert all("expected_stance" not in row for row in item["evidence"])
        assert item["assessment"]["verdict"] == item["diagnostics"]["verdict"]


def test_prepared_packets_have_no_condition_map_keys_or_fake_people(bundle):
    manifest, assignments, schema = structure(bundle)
    assert manifest["actual_participants"] == 0
    assert list((bundle / "responses").iterdir()) == []
    assert json.loads((bundle / "private/key_reviews.json").read_text()) == []
    for slot in assignments:
        folder = bundle / "public/slots" / slot["slot_id"]
        template = json.loads((folder / "blank_response.json").read_text())
        analyze.validate_response(template, manifest, assignments, schema)
        assert template["record_type"] == "blank_template" and template["consent"] is None
        packet = (folder / "packet.html").read_text()
        for token in ("enhanced", "current_rule_", "answer_keys", "validation_status", '"condition"', "diag_", "dev_", '"assignment_seed"'):
            assert token not in packet
        assert "id='consent' type='checkbox'>" in packet  # No checked default.
        assert "connect-src 'none'" in packet and "fetch(" not in packet and "localStorage" not in packet
        assert '"answer": "' not in packet
        assert packet.count("<h2>Task ") == 12


def test_html_is_escaped_and_synthetic_stance_titles_hidden():
    _spec, items = prepare.load_materials()
    item = deepcopy(items[0])
    item["claim"] = "<script>alert('claim')</script>"
    item["evidence"][0]["passage"] = "## Heading <img src=x onerror=alert(1)>"
    rendered = prepare.item_html(item, "baseline")
    assert "<script>" not in rendered and "<img " not in rendered
    assert "&lt;script&gt;" in rendered and "## Heading" in rendered
    synthetic = next(item for item in items if item["selection"]["case_id"] == "dev_conflicting")
    rendered = prepare.item_html(synthetic, "baseline")
    assert "Constructed support passage" not in rendered and "Constructed contradiction passage" not in rendered
    assert "not a real-world citation" in rendered and "evaluation.invalid" not in rendered


def test_quiz_selects_are_programmatically_named_by_their_actual_questions(bundle):
    class QuizLabels(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids = set()
            self.references = []

        def handle_starttag(self, tag, attributes):
            attributes = dict(attributes)
            if attributes.get("id"):
                assert attributes["id"] not in self.ids
                self.ids.add(attributes["id"])
            if tag == "select" and "data-answer" in attributes:
                self.references.append(attributes.get("aria-labelledby"))

    for path in (bundle / "public/slots").glob("*/packet.html"):
        parser = QuizLabels()
        parser.feed(path.read_text())
        assert len(parser.references) == 24
        assert len(set(parser.references)) == 24
        assert all(reference in parser.ids for reference in parser.references)


def synthetic_response(bundle, index=0):
    """TEST-ONLY simulated responses; never saved outside pytest's temp folder."""
    manifest, assignments, schema = structure(bundle)
    slot = assignments[index]
    response = prepare.blank_response(manifest["study_version"], manifest["bundle_id"], slot)
    response.update(record_type="participant_response", consent=True)
    return response, manifest, assignments, schema


@pytest.mark.parametrize("mutation", ["missing", "rating", "answer", "condition", "bundle", "slot", "duplicate_trial", "unknown_trial", "timing", "nan"])
def test_response_schema_and_assignment_validation_reject_invalid_input(bundle, mutation):
    response, manifest, assignments, schema = synthetic_response(bundle)
    row = response["responses"][0]
    if mutation == "missing":
        del response["consent"]
    elif mutation == "rating":
        row["ratings"]["clarity"] = 6
    elif mutation == "answer":
        row["answers"]["reason"] = "D"
    elif mutation == "condition":
        row["condition"] = "enhanced"
    elif mutation == "bundle":
        response["bundle_id"] = "B" + "0" * 16
    elif mutation == "slot":
        response["slot_id"] = "S" + "0" * 10
    elif mutation == "duplicate_trial":
        response["responses"].append(deepcopy(row))
    elif mutation == "unknown_trial":
        row["trial_id"] = "T" + "0" * 12
    elif mutation == "timing":
        row["elapsed_seconds"] = 20
    else:
        row.update(elapsed_seconds=float("nan"), timing_method="facilitator_stopwatch", timing_interrupted=False)
    with pytest.raises((ValidationError, ValueError)):
        analyze.validate_response(response, manifest, assignments, schema)


def test_empty_analysis_has_no_invented_results(bundle):
    report = analyze.analyze_study(bundle)
    assert report["status"] == "Study not yet conducted"
    assert report["counts"]["consenting_response_files"] == 0
    assert report["counts"]["planned_trials_without_any_response"] == 48
    for scores in report["ratings"].values():
        assert scores["by_condition"]["baseline"]["mean"] is None
        assert scores["difference_of_condition_means"] is None
        assert scores["interval"]["low"] is None
    assert report["objective_comprehension"]["status"] == "NOT MEASURED"
    assert "Study not yet conducted" in analyze.render_analysis(report)


def test_blank_templates_are_not_participant_responses(bundle):
    manifest, assignments, _schema = structure(bundle)
    template = prepare.blank_response(manifest["study_version"], manifest["bundle_id"], assignments[0])
    prepare.write_json(bundle / "responses/accidental-template.json", template)
    report = analyze.analyze_study(bundle)
    assert report["counts"]["ignored_blank_templates"] == 1
    assert report["status"] == "Study not yet conducted"


def test_template_with_answers_is_rejected_instead_of_silently_discarded(bundle):
    manifest, assignments, schema = structure(bundle)
    template = prepare.blank_response(manifest["study_version"], manifest["bundle_id"], assignments[0])
    template["responses"][0]["ratings"]["clarity"] = 4
    with pytest.raises(ValueError, match="blank template"):
        analyze.validate_response(template, manifest, assignments, schema)


def test_condition_decoding_and_missing_values_are_correct(bundle):
    response, _manifest, assignments, _schema = synthetic_response(bundle)
    lookup = {trial["trial_id"]: trial for trial in assignments[0]["trials"]}
    for row in response["responses"]:
        row["ratings"]["usefulness"] = 5 if lookup[row["trial_id"]]["condition"] == "enhanced" else 1
    response["responses"][0]["ratings"]["usefulness"] = None
    prepare.write_json(bundle / "responses/SYNTHETIC_TEST_ONLY.json", response)
    report = analyze.analyze_study(bundle)
    scores = report["ratings"]["usefulness"]
    assert scores["difference_of_condition_means"] == 4
    assert scores["within_slot_differences"]["mean"] == 4
    assert sum(row["missing"] for row in scores["by_condition"].values()) == 1
    assert report["counts"]["consenting_response_files"] == 1
    assert report["ratings"]["clarity"]["by_condition"]["baseline"]["mean"] is None
    assert scores["interval"]["low"] is None


def test_partial_response_and_no_consent_are_not_imputed(bundle):
    response, _manifest, _assignments, _schema = synthetic_response(bundle)
    response["responses"] = response["responses"][:1]
    response["responses"][0]["ratings"]["clarity"] = 3
    prepare.write_json(bundle / "responses/SYNTHETIC_PARTIAL.json", response)
    report = analyze.analyze_study(bundle)
    assert sum(row["missing"] for row in report["ratings"]["clarity"]["by_condition"].values()) == 11
    assert report["counts"]["planned_trials_without_any_response"] == 47
    declined, *_ = synthetic_response(bundle, 1)
    declined["consent"] = False
    prepare.write_json(bundle / "responses/SYNTHETIC_NONCONSENT.json", declined)
    report = analyze.analyze_study(bundle)
    assert report["counts"]["nonconsenting_files_excluded"] == 1
    assert report["counts"]["consenting_response_files"] == 1


def review_keys_synthetically_in_temp_only(bundle):
    keys = bundle / "private/answer_keys.json"
    records = [{"study_version": "truthlens-explanation-v1", "keys_sha256": prepare.sha256(keys),
                "reviewer_alias": "SYNTHETIC_UNIT_TEST_ONLY", "independent_of_materials_author": True,
                "decision": "verified", "reviewed_at": "2026-11-02T00:00:00Z", "rationale": "Synthetic temporary test; not a real review"}]
    (bundle / "private/key_reviews.json").write_text(json.dumps(records))


def test_objective_accuracy_is_withheld_until_key_review(bundle):
    response, *_ = synthetic_response(bundle)
    response["responses"][0]["answers"]["reason"] = "A"
    prepare.write_json(bundle / "responses/SYNTHETIC_UNREVIEWED.json", response)
    objective = analyze.analyze_study(bundle)["objective_comprehension"]
    assert objective["status"] == "NOT MEASURED"
    assert all(row["questions"]["reason"]["correct"] is None for row in objective["by_condition"].values())


def test_objective_calibration_and_accuracy_use_correct_keys_after_review(bundle):
    review_keys_synthetically_in_temp_only(bundle)
    response, _manifest, assignments, _schema = synthetic_response(bundle)
    keys = json.loads((bundle / "private/answer_keys.json").read_text())["items"]
    for row, trial in zip(response["responses"], assignments[0]["trials"]):
        for question in ("reason", "limitation"):
            row["answers"][question] = keys[trial["item_id"]][question]["answer"]
        row["answer_confidence"] = 100
    prepare.write_json(bundle / "responses/SYNTHETIC_KEYED.json", response)
    objective = analyze.analyze_study(bundle)["objective_comprehension"]
    assert objective["status"] == "MEASURED"
    for result in objective["by_condition"].values():
        assert result["questions"]["reason"]["accuracy"] == 1
        assert result["calibration"]["brier_score"] == 0


def test_stale_key_reviews_duplicate_submissions_and_integrity_fail_closed(bundle):
    review_keys_synthetically_in_temp_only(bundle)
    records = json.loads((bundle / "private/key_reviews.json").read_text())
    records[0]["keys_sha256"] = "0" * 64
    (bundle / "private/key_reviews.json").write_text(json.dumps(records))
    with pytest.raises(ValueError, match="frozen keys"):
        analyze.analyze_study(bundle)
    (bundle / "private/key_reviews.json").write_text("[]")
    response, *_ = synthetic_response(bundle)
    prepare.write_json(bundle / "responses/SYNTHETIC_A.json", response)
    prepare.write_json(bundle / "responses/SYNTHETIC_B.json", response)
    with pytest.raises(ValueError, match="Duplicate response slot"):
        analyze.analyze_study(bundle)


def test_frozen_packet_modification_is_detected(bundle):
    packet = next((bundle / "public/slots").glob("*/packet.html"))
    packet.write_text("Accidentally changed packet")
    with pytest.raises(ValueError, match="integrity mismatch"):
        analyze.read_bundle(bundle)


def test_interrupted_timing_is_excluded(bundle):
    response, *_ = synthetic_response(bundle)
    response["responses"][0].update(elapsed_seconds=35, timing_method="facilitator_stopwatch", timing_interrupted=True)
    response["responses"][1].update(elapsed_seconds=42, timing_method="facilitator_stopwatch", timing_interrupted=False)
    prepare.write_json(bundle / "responses/SYNTHETIC_TIMING.json", response)
    timing = analyze.analyze_study(bundle)["timing_seconds"]
    assert sum(row["n"] for row in timing.values()) == 1
    assert next(row for row in timing.values() if row["n"])["mean"] == 42


def test_block_intervals_are_deterministic_and_require_enough_blocks():
    settings = {"seed": 7, "repetitions": 2000, "minimum_complete_blocks": 8}
    assert analyze.block_interval([1, 2], settings, "usefulness")["low"] is None
    assert analyze.block_interval([1] * 8, settings, "usefulness")["low"] is None
    first = analyze.block_interval(list(range(8)), settings, "usefulness")
    assert first == analyze.block_interval(list(range(8)), settings, "usefulness")
    assert first["low"] < 3.5 < first["high"]


def test_actual_analysis_bootstraps_complete_blocks_only_in_synthetic_temp_data(tmp_path):
    path = tmp_path / "SYNTHETIC_BOOTSTRAP_TEST_ONLY"
    prepare.prepare_study(path, slots=16, seed=7)
    manifest, assignments, _schema = structure(path)
    for assignment in assignments:
        response = prepare.blank_response(manifest["study_version"], manifest["bundle_id"], assignment)
        response.update(record_type="participant_response", consent=True)
        effect = int(assignment["block_id"].split("-")[1]) % 2
        for row, trial in zip(response["responses"], assignment["trials"]):
            row["ratings"]["usefulness"] = 2 + effect if trial["condition"] == "enhanced" else 2
        prepare.write_json(path / "responses" / (assignment["slot_id"] + ".json"), response)
    scores = analyze.analyze_study(path)["ratings"]["usefulness"]
    assert scores["complete_block_contrast"]["n"] == 8
    assert scores["complete_block_contrast"]["mean"] == 0.5
    assert scores["interval"]["low"] < 0.5 < scores["interval"]["high"]
    # Simulate one missing synthetic respondent; do not count the remaining
    # half-block as a full independent bootstrap unit.
    (path / "responses" / (assignments[0]["slot_id"] + ".json")).unlink()
    scores = analyze.analyze_study(path)["ratings"]["usefulness"]
    assert scores["complete_block_contrast"]["n"] == 7 and scores["interval"]["low"] is None


def test_incorrect_confident_quiz_answers_raise_brier_loss_in_synthetic_data(bundle):
    review_keys_synthetically_in_temp_only(bundle)
    response, _manifest, assignments, _schema = synthetic_response(bundle)
    keys = json.loads((bundle / "private/answer_keys.json").read_text())["items"]
    for row, trial in zip(response["responses"], assignments[0]["trials"]):
        correct = keys[trial["item_id"]]["limitation"]["answer"]
        row["answers"]["limitation"] = next(letter for letter in "ABC" if letter != correct)
        row["answer_confidence"] = 100
    prepare.write_json(bundle / "responses/SYNTHETIC_INCORRECT.json", response)
    for result in analyze.analyze_study(bundle)["objective_comprehension"]["by_condition"].values():
        assert result["questions"]["limitation"]["accuracy"] == 0
        assert result["calibration"]["brier_score"] == 1


def test_preparation_and_analysis_refuse_overwriting(bundle, tmp_path):
    with pytest.raises(FileExistsError):
        prepare.prepare_study(bundle)
    output = tmp_path / "existing-analysis"
    output.mkdir()
    with pytest.raises(FileExistsError):
        analyze.main(["--bundle", str(bundle), "--output-dir", str(output)])


def test_full_preparation_is_byte_reproducible_and_offline(tmp_path, monkeypatch):
    import requests
    import nli_assessor
    monkeypatch.setattr(requests, "get", lambda *_a, **_k: pytest.fail("No network permitted"))
    monkeypatch.setattr(nli_assessor, "assess_evidence_nli", lambda *_a, **_k: pytest.fail("No inference permitted"))
    left, right = tmp_path / "a", tmp_path / "b"
    prepare.prepare_study(left, slots=4, seed=12)
    prepare.prepare_study(right, slots=4, seed=12)
    files = [path.relative_to(left) for path in left.rglob("*") if path.is_file()]
    assert all((left / name).read_bytes() == (right / name).read_bytes() for name in files)
    assert analyze.analyze_study(left) == analyze.analyze_study(right)


def test_custom_information_is_frozen_and_changes_bundle_identity(tmp_path):
    left, right = tmp_path / "left", tmp_path / "right"
    first = prepare.prepare_study(left, slots=4, seed=12)
    sheet = tmp_path / "SYNTHETIC_INFORMATION_TEST.md"
    sheet.write_text("Synthetic test sheet, not real ethics approval or participant consent")
    second = prepare.prepare_study(right, slots=4, seed=12, information_sheet=sheet)
    assert first["bundle_id"] != second["bundle_id"]
    assert (right / "public/PARTICIPANT_INFORMATION.md").read_bytes() == sheet.read_bytes()
    analyze.read_bundle(right)
