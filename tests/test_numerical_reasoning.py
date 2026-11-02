"""Synthetic numerical diagnostics: arithmetic is not fact verification."""
from copy import deepcopy
from unittest.mock import Mock

import pytest

from explainability import build_explanation
from nli_assessor import _QUANTIFIER_SCOPE_CUES, assess_evidence_nli
from numerical_reasoning import (analyze_numerical_evidence,
                                 detect_quantifiers, extract_quantities)
from verifier import assess_evidence


def compare(claim, evidence, **metadata):
    analysis = analyze_numerical_evidence(claim, [{"content": evidence, **metadata}], "2026-11-02")
    return analysis["sources"][0]["comparisons"]


@pytest.mark.parametrize("text, values", [
    ("Sensor A reading is -5.5 meters.", ["-5.5"]),
    ("Sensor A reading is −2 kilograms.", ["-2"]),
    ("Class A has 1,000 students.", ["1000"]),
    ("Sensor A reading is .25 meters.", ["0.25"]),
    ("Class A has 10, according to the record.", ["10"]),
    ("Sensor A readings are 2 meters and 3 kilograms.", ["2", "3"]),
])
def test_signed_decimal_and_integer_extraction_preserves_source_offsets(text, values):
    rows = extract_quantities(text)["quantities"]
    assert [row["lower"] for row in rows] == values
    assert all(row["status"] == "resolved" for row in rows)
    assert all(text[row["start"]:row["end"]] == row["text"] for row in rows)


@pytest.mark.parametrize("first, second", [("1000 meters", "1 kilometer"), ("2kg", "2000g"),
                                           ("20°C", "68°F"), ("-40°C", "-40°F")])
def test_supported_units_normalize_to_compatible_base_intervals(first, second):
    assert compare("Sensor A reading is " + first + ".", "Sensor A reading is " + second + ".")[0]["status"] == "compatible"


def test_equal_temperature_numbers_in_different_scales_can_be_disjoint():
    result = compare("Sensor A temperature is 20°C.", "Sensor A temperature is 20°F.")[0]
    assert result["status"] == "potential_mismatch"
    assert "review context" in result["reason"]


@pytest.mark.parametrize("first, second, status", [
    ("at least 10", "exactly 10", "compatible"),
    ("more than 10", "exactly 10", "potential_mismatch"),
    ("at most 10", "10", "compatible"),
    ("at most 10", "11", "potential_mismatch"),
    ("less than 10", "10", "potential_mismatch"),
    (">=10", "10", "compatible"),
    ("≤10", "11", "potential_mismatch"),
    ("no more than 10", "11", "potential_mismatch"),
])
def test_open_and_closed_comparator_bounds(first, second, status):
    result = compare("Class A has " + first + " students.", "Class A has " + second + " students.")[0]
    assert result["status"] == status


@pytest.mark.parametrize("first, second, status", [
    ("10 to 20 meters", "15 to 25 meters", "compatible"),
    ("between 10 and 20 meters", "between 30 and 40 meters", "potential_mismatch"),
    ("from 1km to 1500m", "1.25km", "compatible"),
    ("-5 to -1°C", "-3°C", "compatible"),
    ("10–20 meters", "20 meters", "compatible"),
])
def test_ranges_and_mixed_compatible_endpoint_units(first, second, status):
    assert compare("Sensor A reading is " + first + ".", "Sensor A reading is " + second + ".")[0]["status"] == status


def test_approximation_policy_is_explicit_and_does_not_use_truth_probabilities():
    row = extract_quantities("Class A pass rate is about 30%.")["quantities"][0]
    assert (row["lower"], row["upper"], row["tolerance"]) == ("29.4", "30.6", "0.6")
    assert compare("Class A pass rate is about 30%.", "Class A pass rate is 29.8%.")[0]["status"] == "compatible"
    assert compare("Class A pass rate is about 30%.", "Class A pass rate is 3%.")[0]["status"] == "potential_mismatch"
    row = extract_quantities("Sensor A temperature is approximately 0°C.")["quantities"][0]
    assert (row["lower"], row["upper"]) == ("-0.5", "0.5")


def test_approximation_inequality_scope_is_unresolved():
    row = extract_quantities("Class A has approximately at least 10 students.")["quantities"][0]
    assert row["status"] == "unresolved"


def test_percentage_and_percentage_points_are_distinct_concepts():
    result = compare("Class A score increased by 30%.", "Class A score increased by 30 percentage points.")[0]
    assert result["status"] == "comparison_unresolved"
    assert "baseline" in result["reason"]


@pytest.mark.parametrize("evidence", ["Class B has 20 students.", "Class A has 20 researchers.",
                                     "Class A has 20 students in 2020.", "Its roster has 20 students.",
                                     "Class A roster is unavailable."])
def test_different_entities_properties_populations_or_missing_context_are_unresolved(evidence):
    assert compare("Class A has 10 students.", evidence)[0]["status"] == "comparison_unresolved"


def test_different_explicit_years_are_not_numeric_contradictions():
    assert compare("Class A has 10 students in 2020.", "Class A has 20 students in 2021.")[0]["status"] == "comparison_unresolved"


def test_year_shaped_samples_are_quantities_but_calendar_dates_are_separate():
    data = extract_quantities("The array contains 2020 samples collected in 2021.")
    assert [row["text"] for row in data["quantities"]] == ["2020"]
    assert [row["text"] for row in data["dates"]] == ["2021"]
    assert extract_quantities("The lab opened on 30 April 1993.")["quantities"] == []
    assert extract_quantities("The event occurred on 2025-11-02.")["quantities"] == []


def test_multiple_values_align_by_property_and_retain_other_normalized_values():
    results = compare("Sample A length is 10m and Sample A mass is 2kg.",
                      "Sample A length is 0.01km and Sample A mass is 2000g.")
    assert [row["status"] for row in results] == ["compatible", "compatible"]
    assert [row["evidence_quantity"] for row in results] == [0, 1]
    changed = compare("Class A rate increased 30% from 100 samples.", "Class A rate increased 30% from 200 samples.")
    assert changed[0]["status"] == "comparison_unresolved"


@pytest.mark.parametrize("claim, evidence", [("Sample A mass is not 10kg.", "Sample A mass is 20kg."),
                                            ("Sample A mass is not 10kg.", "Sample A mass is not 20kg."),
                                            ("Its mass is 10kg.", "Its mass is 20kg.")])
def test_negation_and_pronouns_never_force_mismatch(claim, evidence):
    assert compare(claim, evidence)[0]["status"] == "comparison_unresolved"


def test_quantifier_detection_uses_the_existing_guard_inventory_and_keeps_negation():
    text = "Not all students passed; some passed; none failed; at least 10 attended; every class was recorded."
    rows = detect_quantifiers(text)
    assert [(row["start"], row["end"]) for row in rows] == [(match.start(), match.end()) for match in _QUANTIFIER_SCOPE_CUES.finditer(text)]
    assert rows[0]["kind"] == "negated_universal" and rows[0]["negated"]
    assert any(row["kind"] == "existential" for row in rows)
    assert any(row["kind"] == "negative_quantifier" for row in rows)


def test_some_neither_establishes_nor_disproves_all():
    result = analyze_numerical_evidence("All students in Class A passed.", [{"content": "Some students in Class A passed."}])
    source = result["sources"][0]
    assert source["comparisons"][0]["status"] == "comparison_unresolved"
    assert any("neither establishes nor disproves all" in warning for warning in source["quantifier_warnings"])


def test_negated_some_is_not_treated_as_an_affirmative_existential():
    data = detect_quantifiers("Not some students in Class A passed.")
    assert data[0]["kind"] == "negated_existential" and data[0]["negated"]
    result = analyze_numerical_evidence("All students in Class A passed.", [{"content": "Not some students in Class A passed."}])
    assert not any("Some alone" in warning for warning in result["sources"][0]["quantifier_warnings"])
    assert result["sources"][0]["comparisons"][0]["status"] == "comparison_unresolved"


@pytest.mark.parametrize("text", ["Sample A mass is 1,5kg.", "Sample A mass is 10 pounds.",
                                  "Sensor A speed is 10km/s.", "Sample A area is 10m².",
                                  "Sensor A reading is 20 to 10 meters."])
def test_unsupported_units_reversed_ranges_and_ambiguous_formats_are_retained_as_unresolved(text):
    rows = extract_quantities(text)["quantities"]
    assert rows and all(row["status"] == "unresolved" for row in rows)


def test_current_measurement_requires_explicit_source_event_anchor_not_publication_date():
    claim = "Class A currently has 10 students."
    assert compare(claim, claim, published_date="2026-11-02")[0]["status"] == "comparison_unresolved"
    assert compare(claim, claim, event_date="2026")[0]["status"] == "comparison_unresolved"
    assert compare(claim, claim, temporal_reference_date="2026-11-02")[0]["status"] == "compatible"


def test_same_relative_wording_with_different_anchors_is_unresolved():
    claim = "Class A had 10 students last year."
    result = compare(claim, "Class A had 20 students last year.", temporal_reference_date="2025-11-02")
    assert result[0]["status"] == "comparison_unresolved"
    result = compare(claim, "Class A had 20 students last year.", temporal_reference_date="2026-11-02")
    assert result[0]["status"] == "potential_mismatch"


def test_vague_relative_measurement_context_is_unresolved_even_with_reference_date():
    result = compare("Class A recently had 10 students.", "Class A recently had 20 students.", temporal_reference_date="2026-11-02")
    assert result[0]["status"] == "comparison_unresolved"


def test_html_like_context_is_not_interpreted_as_a_measurement_assertion():
    rows = extract_quantities('<script>Sensor A reading is 10 meters</script>')["quantities"]
    assert rows and not rows[0]["context_explicit"]


@pytest.mark.parametrize("mode", ["rule", "nli"])
def test_existing_verdict_original_evidence_and_guard_defaults_are_unchanged(mode):
    claim = "The Eiffel Tower is located in Paris."
    results = [{"url": "https://one.example/a", "content": "The Eiffel Tower is located in Paris, France."},
               {"url": "https://two.example/b", "content": "The Eiffel Tower is located in Paris near the Champ de Mars."}]
    predict = Mock(return_value={"label": "SUPPORTS", "confidence": .92, "margin": .60})
    assessment = assess_evidence(claim, results) if mode == "rule" else assess_evidence_nli(claim, results, predict)
    before = deepcopy((results, assessment))
    explanation = build_explanation(claim, results, assessment)
    assert explanation["verdict"] == "Supported"
    assert explanation["numerical"]["diagnostic_only"]
    assert (results, assessment) == before
    assert predict.call_count == (0 if mode == "rule" else 2)


def test_interval_compatibility_is_not_claim_entailment():
    result = compare("Class A has exactly 10 students.", "Class A has at least 10 students.")[0]
    assert result["status"] == "compatible" and "does not establish" in result["reason"]
