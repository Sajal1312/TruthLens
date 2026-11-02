"""Offline tests for local NLI aggregation and graceful fallback."""
from unittest.mock import Mock

import pytest

from nli_assessor import (MIN_CONFIDENCE, MIN_DIRECTIONAL_SOURCES, MIN_MARGIN,
                          _claim_parts, _claim_parts_experimental,
                          assess_with_optional_nli, assess_evidence_nli)
from verifier import search_evidence
from nli_assessor import _near_duplicate


CLAIM = "The Eiffel Tower is located in Paris."


def tavily_result(number, content):
    return {"title": "Mock source {0}".format(number),
            "url": "https://source-{0}.example/page".format(number),
            "content": content, "published_date": ""}


@pytest.fixture
def mocked_tavily_results():
    return [tavily_result(1, "The Eiffel Tower is located in Paris, France."),
            tavily_result(2, "The Eiffel Tower is located in Paris near the Champ de Mars.")]


def prediction(label, confidence=0.92, margin=0.55):
    return {"label": label, "confidence": confidence, "margin": margin}


def test_nli_supports_with_two_distinct_sources(mocked_tavily_results):
    predict = Mock(side_effect=[prediction("ENTAILMENT"), prediction("SUPPORTS")])
    result = assess_evidence_nli(CLAIM, mocked_tavily_results, predict)
    assert result["verdict"] == "Supported"
    assert [row["label"] for row in result["per_source"]] == ["SUPPORTS", "SUPPORTS"]
    assert "not proof" in result["reasoning"]


def test_nli_contradicts_with_two_distinct_sources(mocked_tavily_results):
    mocked_tavily_results[0]["content"] = "The Eiffel Tower is not located in Paris, France."
    mocked_tavily_results[1]["content"] = "The Eiffel Tower is not located in Paris according to this page."
    predict = Mock(side_effect=[prediction("CONTRADICTION"), prediction("CONTRADICTS")])
    result = assess_evidence_nli(CLAIM, mocked_tavily_results, predict)
    assert result["verdict"] == "Contradicted"
    assert len(result["evidence_used"]) == 2


def test_one_directional_source_is_insufficient(mocked_tavily_results):
    predict = Mock(side_effect=[prediction("ENTAILMENT"), prediction("NEUTRAL")])
    result = assess_evidence_nli(CLAIM, mocked_tavily_results, predict)
    assert result["verdict"] == "Inconclusive"
    assert "Only one distinct URL" in result["reasoning"]


def test_duplicate_url_does_not_count_as_two_sources():
    duplicate_results = [
        tavily_result(1, "The Eiffel Tower is located in Paris."),
        {"title": "Same URL, repeated", "url": "https://source-1.example/page/",
         "content": "The Eiffel Tower is located in Paris.", "published_date": ""},
    ]
    predict = Mock(side_effect=[prediction("ENTAILMENT"), prediction("ENTAILMENT")])
    result = assess_evidence_nli(CLAIM, duplicate_results, predict)
    assert result["verdict"] == "Inconclusive"
    assert "Only one distinct URL" in result["reasoning"]


def test_identical_passages_on_different_urls_do_not_count_as_independent_sources():
    repeated = "The Eiffel Tower is located in Paris, France."
    results = [tavily_result(1, repeated), tavily_result(2, repeated)]
    results[1]["content"] = repeated
    predict = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(CLAIM, results, predict)
    assert result["verdict"] == "Inconclusive"
    assert len(result["evidence_used"]) == 1
    assert "Repeated passage" in result["per_source"][1]["part_assessments"][0]["status"]


def test_same_run_exact_input_cache_preserves_assessments_and_skips_duplicate_inference():
    repeated = "The Eiffel Tower is located in Paris, France."
    results = [tavily_result(1, repeated), tavily_result(2, repeated)]
    uncached_predictor = Mock(return_value=prediction("ENTAILMENT"))
    cached_predictor = Mock(return_value=prediction("ENTAILMENT"))
    timings = {}

    uncached = assess_evidence_nli(CLAIM, results, uncached_predictor)
    cached = assess_evidence_nli(CLAIM, results, cached_predictor,
                                 cache_predictions=True, timings=timings)

    assert uncached_predictor.call_count == 2
    assert cached_predictor.call_count == 1
    assert cached["verdict"] == uncached["verdict"] == "Inconclusive"
    for index in range(2):
        before = uncached["per_source"][index]["part_assessments"][0]
        after = cached["per_source"][index]["part_assessments"][0]
        for key in ("label", "confidence", "margin", "scores", "contributed", "status"):
            assert after[key] == before[key]
    assert cached["per_source"][1]["part_assessments"][0]["inference_cache_hit"] is True
    assert cached["per_source"][0]["part_assessments"][0]["inference_cache_hit"] is False
    assert timings["nli_model_calls"] == 1
    assert timings["nli_cache_hits"] == 1


def test_prediction_cache_never_persists_between_verifications():
    result = tavily_result(1, "The Eiffel Tower is located in Paris, France.")
    predictor = Mock(side_effect=[prediction("ENTAILMENT"), prediction("CONTRADICTION")])

    first = assess_evidence_nli(CLAIM, [result], predictor, cache_predictions=True)
    second = assess_evidence_nli(CLAIM, [result], predictor, cache_predictions=True)

    assert predictor.call_count == 2
    assert first["per_source"][0]["part_assessments"][0]["label"] == "SUPPORTS"
    assert second["per_source"][0]["part_assessments"][0]["label"] == "CONTRADICTS"


@pytest.mark.parametrize("claim, passage", [
    ("Not all planets have moons.", "Some planets have moons."),
    ("All planets have moons.", "Some planets have no moons."),
    ("No planets have moons.", "Some planets have moons."),
    ("Most students passed the examination.", "Some students passed the examination."),
    ("At least five students passed the examination.", "Some students passed the examination."),
    ("At most four students passed the examination.", "Some students passed the examination."),
    ("Only one student passed the examination.", "Some students passed the examination."),
    ("Not every student passed the examination.",
     "Not every student passed the examination; some students failed."),
    ("The team never lost a match.", "The team lost a match in 2024."),
])
def test_experimental_quantifier_scope_guard_abstains_but_keeps_raw_model_label(claim, passage):
    result = assess_evidence_nli(
        claim, [tavily_result(1, passage)],
        Mock(return_value=prediction("ENTAILMENT")), experimental_quantifier_guard=True)
    part = result["per_source"][0]["part_assessments"][0]

    assert result["verdict"] == "Inconclusive"
    assert part["model_label"] == "SUPPORTS"
    assert part["label"] in ("UNCERTAIN", "NOT ENOUGH INFORMATION")
    assert not part["contributed"]
    assert "quantifier scope" in part["status"].lower()


def test_experimental_quantifier_guard_does_not_change_production_path():
    claim = "Not all planets have moons."
    results = [
        tavily_result(1, "Some planets have moons."),
        tavily_result(2, "Some planets in the Solar System have moons orbiting them."),
    ]
    production = assess_evidence_nli(claim, results, Mock(return_value=prediction("ENTAILMENT")))
    experimental = assess_evidence_nli(
        claim, results, Mock(return_value=prediction("ENTAILMENT")),
        experimental_semantic=True, experimental_quantifier_guard=True)

    assert production["verdict"] == "Supported"
    assert experimental["verdict"] == "Inconclusive"
    assert all(row["part_assessments"][0]["model_label"] == "SUPPORTS"
               for row in experimental["per_source"])


def test_experimental_temporal_guard_abstains_on_reported_intent_not_event():
    claim = "The company will launch the product in 2030."
    passage = "In 2025, the company said it plans to launch the product in 2030."
    item = tavily_result(1, passage)
    raw_assessment = assess_evidence_nli(
        claim, [item], Mock(return_value=prediction("ENTAILMENT")), experimental_semantic=True)
    guarded_assessment = assess_evidence_nli(
        claim, [item], Mock(return_value=prediction("ENTAILMENT")), experimental_semantic=True,
        experimental_temporal_guard=True)
    raw_part = raw_assessment["per_source"][0]["part_assessments"][0]
    guarded_part = guarded_assessment["per_source"][0]["part_assessments"][0]

    assert raw_part["model_label"] == guarded_part["model_label"] == "SUPPORTS"
    assert raw_part["label"] == "SUPPORTS"
    assert guarded_part["label"] in ("UNCERTAIN", "NOT ENOUGH INFORMATION")
    assert "future intent" in guarded_part["status"].lower()
    assert not guarded_part["contributed"]
    assert guarded_assessment["verdict"] == "Inconclusive"


def test_cached_prediction_still_reapplies_source_specific_context_filters():
    claim = "The Eiffel Tower is located in Paris."
    repeated = "The Eiffel Tower is located in Paris."
    results = [
        {"title": "What if the Eiffel Tower is located in Paris?", "url": "https://source-1.example/page",
         "content": repeated, "published_date": ""},
        {"title": "Paris landmark overview", "url": "https://source-2.example/page",
         "content": repeated, "published_date": ""},
    ]
    predictor = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(claim, results, predictor, cache_predictions=True)

    assert predictor.call_count == 1
    historical, plain = [row["part_assessments"][0] for row in result["per_source"]]
    assert "hypothetical" in historical["status"].lower()
    assert not historical["contributed"]
    assert plain["contributed"]
    assert plain["inference_cache_hit"]
    assert result["verdict"] == "Inconclusive"


def test_near_duplicate_passages_are_not_independent_confirmations():
    base = ("The Eiffel Tower is located in Paris France and visitors can see the monument near the Champ de Mars "
            "beside the Seine River with public gardens and museums nearby according to this travel information page")
    lightly_edited = base.replace("public gardens", "beautiful gardens")
    assert _near_duplicate(base, lightly_edited)
    results = [tavily_result(1, base), tavily_result(2, lightly_edited)]
    predict = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(CLAIM, results, predict)
    assert result["verdict"] == "Inconclusive"
    assert "not independently counted" in result["per_source"][1]["independence"]


def test_credible_domain_with_irrelevant_text_cannot_influence_verdict():
    results = [
        {"title": "NASA astronomy", "url": "https://science.nasa.gov/space/", "content": "Mars has two moons.", "published_date": "2025-01-01"},
        tavily_result(2, "Paris is a popular city for visitors."),
    ]
    predict = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(CLAIM, results, predict)
    assert result["verdict"] == "Inconclusive"
    assert result["per_source"][0]["source_context"]["category"] == "Scientific institution / publication"
    assert result["per_source"][0]["relevance"] == "Unrelated"
    predict.assert_not_called()


def test_relevant_unknown_source_is_contextual_and_not_promoted_from_one_result():
    results = [tavily_result(1, "The Eiffel Tower is located in Paris, France.")]
    predict = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(CLAIM, results, predict)
    assert result["verdict"] == "Inconclusive"
    assert result["per_source"][0]["source_context"]["category"] == "Unknown"
    assert result["per_source"][0]["relevance"] == "Directly relevant candidate"


def test_explicitly_different_year_is_not_used_for_a_claim_about_another_year():
    claim = "The Eiffel Tower was open in 1889."
    results = [tavily_result(1, "The Eiffel Tower was not open in 1888, according to this archive.")]
    predict = Mock(return_value=prediction("CONTRADICTION"))
    result = assess_evidence_nli(claim, results, predict)
    assert result["verdict"] == "Inconclusive"
    assert result["per_source"][0]["relevance"] == "Different time period"
    assert "different year" in result["per_source"][0]["part_assessments"][0]["status"]
    predict.assert_not_called()


def test_malformed_source_url_is_never_counted_as_evidence():
    results = [{"title": "Bad URL", "url": "https://example.com:invalid/page",
                "content": "The Eiffel Tower is located in Paris.", "published_date": ""}]
    predict = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(CLAIM, results, predict)
    assert result["verdict"] == "Inconclusive"
    assert "missing or invalid" in result["per_source"][0]["status"]
    predict.assert_not_called()


def test_nonassertive_question_is_not_directional_evidence():
    results = [tavily_result(1, "Does the Eiffel Tower is located in Paris?")]
    predict = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(CLAIM, results, predict)
    assert result["verdict"] == "Inconclusive"
    assert result["per_source"][0]["label"] == "NOT ENOUGH INFORMATION"


def test_explicit_hypothetical_is_not_directional_evidence():
    results = [tavily_result(1, "Hypothetically, the Eiffel Tower could be located in Paris.")]
    predict = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(CLAIM, results, predict)
    assert result["verdict"] == "Inconclusive"


def test_historical_geocentric_claim_does_not_count_against_current_science():
    claim = "The Earth revolves around the Sun."
    results = [
        tavily_result(1, "Historically, people believed the Sun revolves around the Earth."),
        tavily_result(2, "Earth revolves around the Sun in its yearly orbit."),
        tavily_result(3, "The Earth orbits the Sun once each year."),
    ]
    predict = Mock(side_effect=[prediction("CONTRADICTION"), prediction("ENTAILMENT"), prediction("ENTAILMENT")])
    result = assess_evidence_nli(claim, results, predict)
    assert result["verdict"] == "Supported"
    assert result["per_source"][0]["label"] == "NOT ENOUGH INFORMATION"


def test_historical_belief_without_endorsement_is_excluded_as_directional_evidence():
    claim = "The Sun revolves around the Earth."
    results = [tavily_result(1, "Historically, many people believed that the Sun revolved around the Earth.")]
    predict = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(claim, results, predict)
    component = result["per_source"][0]["part_assessments"][0]
    assert result["verdict"] == "Inconclusive"
    assert component["model_label"] == "SUPPORTS"
    assert component["label"] == "UNCERTAIN"
    assert "Historical or attributed belief" in component["status"]
    assert component["contributed"] is False


def test_historical_source_title_and_reported_survey_belief_are_neutral():
    claim = "The Sun revolves around the Earth."
    item = tavily_result(1, "Polls found some respondents hold that the Sun revolves around the Earth.")
    item["title"] = "Geocentrism and public beliefs"
    result = assess_evidence_nli(claim, [item], Mock(return_value=prediction("CONTRADICTION")))
    component = result["per_source"][0]["part_assessments"][0]
    assert component["label"] == "UNCERTAIN"
    assert "Historical or attributed belief" in component["status"]
    assert component["contributed"] is False


def test_what_if_title_and_hypothetical_passage_are_not_present_day_evidence():
    claim = "The Sun revolves around the Earth."
    result_item = tavily_result(1, "If the Sun revolved around the Earth, its apparent motion would change.")
    result_item["title"] = "What if the Sun Revolved around the Earth?"
    predict = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(claim, [result_item], predict)
    component = result["per_source"][0]["part_assessments"][0]
    assert result["verdict"] == "Inconclusive"
    assert component["model_label"] == "SUPPORTS"
    assert component["contributed"] is False
    assert "hypothetical framing" in component["status"]


def test_explicit_earth_orbits_sun_assertion_remains_eligible_to_contradict_opposite_claim():
    claim = "The Sun revolves around the Earth."
    results = [tavily_result(1, "The Earth revolves around the Sun, not the reverse.")]
    predict = Mock(return_value=prediction("CONTRADICTION"))
    result = assess_evidence_nli(claim, results, predict)
    component = result["per_source"][0]["part_assessments"][0]
    assert component["label"] == "CONTRADICTS"
    assert component["contributed"] is True
    assert component["passage"] == "The Earth revolves around the Sun, not the reverse."
    assert result["verdict"] == "Inconclusive"  # One source is still below the unchanged threshold.


def test_model_support_cannot_override_an_explicitly_reversed_motion_relation():
    claim = "The Sun revolves around the Earth."
    passage = "The Earth revolves around the Sun."
    result = assess_evidence_nli(claim, [tavily_result(1, passage)],
                                 Mock(return_value=prediction("ENTAILMENT")))
    component = result["per_source"][0]["part_assessments"][0]
    assert component["model_label"] == "SUPPORTS"
    assert component["label"] == "UNCERTAIN"
    assert "reverse motion relationship" in component["status"]
    assert component["contributed"] is False


@pytest.mark.parametrize("passage", [
    "Earth revolves around the Sun, completing one revolution each year.",
    "Earth revolves about the Sun, completing one revolution each year.",
])
def test_model_contradiction_cannot_override_an_explicit_same_direction_assertion(passage):
    claim = "The Earth revolves around the Sun."
    result = assess_evidence_nli(claim, [tavily_result(1, passage)],
                                 Mock(return_value=prediction("CONTRADICTION")))
    component = result["per_source"][0]["part_assessments"][0]
    assert component["model_label"] == "CONTRADICTS"
    assert component["label"] == "UNCERTAIN"
    assert "same motion direction" in component["status"]
    assert component["contributed"] is False


def test_orbit_around_a_different_body_is_weakly_related_not_direct_evidence():
    claim = "The Sun revolves around the Earth."
    results = [tavily_result(1, "The Sun revolved around a central fire once a year.")]
    predict = Mock(return_value=prediction("CONTRADICTION"))
    result = assess_evidence_nli(claim, results, predict)
    assert result["verdict"] == "Inconclusive"
    assert result["per_source"][0]["relevance"] == "Weakly related"
    predict.assert_not_called()


@pytest.mark.parametrize("passage", [
    "The Sun's immense mass pulls Earth into its orbit.",
    "The immense mass of the Sun pulls Earth into its orbit.",
])
def test_gravity_orbit_wording_cannot_turn_the_reverse_relation_into_support(passage):
    claim = "The Sun revolves around the Earth."
    results = [tavily_result(1, passage)]
    predict = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(claim, results, predict)
    component = result["per_source"][0]["part_assessments"][0]
    assert result["verdict"] == "Inconclusive"
    assert component["model_label"] == "SUPPORTS"
    assert component["contributed"] is False
    assert "reverse motion relationship" in component["status"]


def test_model_support_cannot_override_explicit_earth_moves_around_sun_wording():
    claim = "The Sun revolves around the Earth."
    passage = "Earth moves around the Sun in an elliptical orbit."
    result = assess_evidence_nli(claim, [tavily_result(1, passage)],
                                 Mock(return_value=prediction("ENTAILMENT")))
    component = result["per_source"][0]["part_assessments"][0]
    assert component["model_label"] == "SUPPORTS"
    assert component["label"] == "UNCERTAIN"
    assert "reverse motion relationship" in component["status"]
    assert component["contributed"] is False
    assert result["verdict"] == "Inconclusive"


def test_experimental_reverse_relation_uses_explicit_opposite_direction_as_contradiction():
    claim = "The Sun revolves around the Earth."
    results = [tavily_result(1, "The Earth revolves around the Sun."),
               tavily_result(2, "Earth moves around the Sun in an elliptical orbit.")]
    predictor = Mock(return_value=prediction("ENTAILMENT"))
    production = assess_evidence_nli(claim, results, predictor)
    experimental = assess_evidence_nli(claim, results, predictor, experimental_semantic=True)

    assert production["verdict"] == "Inconclusive"
    assert experimental["verdict"] == "Contradicted"
    assert experimental["original_claim"] == claim
    assert all(row["part_assessments"][0]["label"] == "CONTRADICTS"
               for row in experimental["per_source"])
    assert all("experimental mode" in row["part_assessments"][0]["status"]
               for row in experimental["per_source"])


def test_experimental_reverse_rule_does_not_override_hypothetical_context():
    claim = "The Sun revolves around the Earth."
    results = [tavily_result(1, "Hypothetically, the Earth revolves around the Sun."),
               tavily_result(2, "In a thought experiment, Earth moves around the Sun.")]
    result = assess_evidence_nli(claim, results, Mock(return_value=prediction("ENTAILMENT")),
                                 experimental_semantic=True)
    assert result["verdict"] == "Inconclusive"
    assert all(not row["part_assessments"][0]["contributed"] for row in result["per_source"])


def test_experimental_reverse_rule_preserves_model_support_for_negated_claims():
    claim = "The Sun does not revolve around the Earth."
    results = [tavily_result(1, "The Earth revolves around the Sun."),
               tavily_result(2, "Earth moves around the Sun in an elliptical orbit.")]
    result = assess_evidence_nli(claim, results, Mock(return_value=prediction("ENTAILMENT")),
                                 experimental_semantic=True)
    assert result["original_claim"] == claim
    assert result["verdict"] == "Supported"
    assert all(row["part_assessments"][0]["label"] == "SUPPORTS" for row in result["per_source"])


def test_singly_negated_claim_with_conflicting_passage_predictions_abstains():
    claim = "The Sun does not revolve around the Earth."
    results = [tavily_result(1, "Earth revolves around the Sun."),
               tavily_result(2, "Earth moves around the Sun in an elliptical orbit.")]
    predictor = Mock(side_effect=[prediction("ENTAILMENT"), prediction("CONTRADICTION")])
    result = assess_evidence_nli(claim, results, predictor, experimental_semantic=True)
    assert result["verdict"] == "Inconclusive"
    assert [row["part_assessments"][0]["label"] for row in result["per_source"]] == [
        "SUPPORTS", "CONTRADICTS"]


def test_explicit_negative_passages_can_contradict_positive_claim():
    claim = "The Sun revolves around the Earth."
    results = [tavily_result(1, "The Sun does not revolve around Earth."),
               tavily_result(2, "The Sun does not revolve around the Earth in its yearly path.")]
    result = assess_evidence_nli(claim, results, Mock(return_value=prediction("CONTRADICTION")))
    assert result["verdict"] == "Contradicted"
    assert all(row["part_assessments"][0]["label"] == "CONTRADICTS" for row in result["per_source"])


def test_nli_timing_breakdown_is_opt_in_and_contains_no_claim_or_secret():
    results = [tavily_result(1, "The Eiffel Tower is located in Paris, France."),
               tavily_result(2, "The Eiffel Tower is located in Paris near the Champ de Mars.")]
    timings = {}
    claim = "The Eiffel Tower is located in Paris."
    result = assess_with_optional_nli(claim, results,
                                      lambda: lambda _premise, _hypothesis: prediction("ENTAILMENT"),
                                      timings=timings)
    assert result["verdict"] == "Supported"
    assert {"model_load_ms", "evidence_filtering_ms", "nli_inference_ms",
            "aggregation_ms", "assessment_total_ms", "nli_model_calls"} <= set(timings)
    assert all(value >= 0 for key, value in timings.items() if key.endswith("_ms"))
    assert timings["nli_model_calls"] == 2
    assert claim not in repr(timings)


def test_experimental_reverse_rule_abstains_on_double_negation():
    claim = "The Sun does not not revolve around the Earth."
    results = [tavily_result(1, "Earth revolves around the Sun in its yearly orbit."),
               tavily_result(2, "The Earth moves around the Sun in an elliptical orbit.")]
    result = assess_evidence_nli(claim, results, Mock(return_value=prediction("ENTAILMENT")),
                                 experimental_semantic=True)
    assert result["verdict"] == "Inconclusive"
    assert all(not row["part_assessments"][0]["contributed"] for row in result["per_source"])
    assert all("Multiple negation cues" in row["part_assessments"][0]["status"]
               for row in result["per_source"])


def test_experimental_double_negation_guard_applies_to_raw_contradiction_labels():
    claim = "The Sun does not not revolve around the Earth."
    results = [tavily_result(1, "Earth revolves around the Sun in its yearly orbit."),
               tavily_result(2, "The Earth moves around the Sun in an elliptical orbit.")]
    result = assess_evidence_nli(claim, results, Mock(return_value=prediction("CONTRADICTION")),
                                 experimental_semantic=True)
    assert result["verdict"] == "Inconclusive"
    assert all(row["part_assessments"][0]["label"] == "UNCERTAIN"
               for row in result["per_source"])
    assert all(not row["part_assessments"][0]["contributed"] for row in result["per_source"])


def test_production_path_abstains_on_ambiguous_double_negated_motion_claim():
    claim = "The Sun does not not revolve around the Earth."
    results = [tavily_result(1, "Earth revolves around the Sun in its yearly orbit."),
               tavily_result(2, "The Earth moves around the Sun in an elliptical orbit.")]
    result = assess_evidence_nli(claim, results, Mock(return_value=prediction("CONTRADICTION")))
    assert result["verdict"] == "Inconclusive"
    assert all(not row["part_assessments"][0]["contributed"] for row in result["per_source"])
    assert all("Multiple negation cues" in row["part_assessments"][0]["status"]
               for row in result["per_source"])


def test_experimental_reverse_rule_abstains_when_passage_asserts_both_directions():
    claim = "The Sun revolves around the Earth."
    mixed = "The Sun revolves around Earth, while Earth also revolves around the Sun."
    results = [tavily_result(1, mixed), tavily_result(2, mixed + " Both relations are stated here.")]
    result = assess_evidence_nli(claim, results, Mock(return_value=prediction("ENTAILMENT")),
                                 experimental_semantic=True)
    assert result["verdict"] == "Inconclusive"
    assert all(not row["part_assessments"][0]["contributed"] for row in result["per_source"])
    assert all("both motion directions" in row["part_assessments"][0]["status"]
               for row in result["per_source"])


def test_experimental_motion_parser_normalizes_passive_orbit_wording():
    claim = "The Earth revolves around the Sun."
    result = assess_evidence_nli(
        claim, [tavily_result(1, "The Sun is orbited by Earth.")],
        Mock(return_value=prediction("CONTRADICTION")), experimental_semantic=True)
    component = result["per_source"][0]["part_assessments"][0]
    assert component["label"] == "UNCERTAIN"
    assert component["contributed"] is False
    assert "same motion direction" in component["status"]


def test_experimental_motion_parser_recognizes_passive_reversed_relation():
    claim = "The Sun revolves around the Earth."
    results = [tavily_result(1, "The Sun is orbited by Earth."),
               tavily_result(2, "The Sun is orbited by Earth over the course of a year.")]
    result = assess_evidence_nli(claim, results, Mock(return_value=prediction("ENTAILMENT")),
                                 experimental_semantic=True)
    assert result["verdict"] == "Contradicted"
    assert all(row["part_assessments"][0]["label"] == "CONTRADICTS" for row in result["per_source"])


def test_experimental_passive_same_direction_does_not_become_contradiction():
    claim = "The Earth revolves around the Sun."
    results = [tavily_result(1, "The Sun is orbited by Earth."),
               tavily_result(2, "The Sun is orbited by Earth over a year.")]
    result = assess_evidence_nli(claim, results, Mock(return_value=prediction("CONTRADICTION")),
                                 experimental_semantic=True)
    assert result["verdict"] == "Inconclusive"
    assert all(row["part_assessments"][0]["label"] == "UNCERTAIN" for row in result["per_source"])


def test_experimental_reverse_rule_does_not_run_for_lexically_similar_irrelevance():
    claim = "The Sun revolves around the Earth."
    results = [tavily_result(1, "The Sun revolves around a central fire in an old diagram."),
               tavily_result(2, "Earth has a moon, while the Sun shines on the Solar System.")]
    predictor = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(claim, results, predictor, experimental_semantic=True)
    assert result["verdict"] == "Inconclusive"
    assert result["per_source"][0]["relevance"] in ("Weakly related", "Unrelated")
    predictor.assert_not_called()


def test_experimental_reverse_rule_does_not_run_after_claim_year_mismatch():
    claim = "The Sun revolves around the Earth in 2025."
    results = [tavily_result(1, "Earth revolved around the Sun in 2024."),
               tavily_result(2, "Earth moved around the Sun in 2023 in an elliptical orbit.")]
    predictor = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(claim, results, predictor, experimental_semantic=True)
    assert result["verdict"] == "Inconclusive"
    assert all(row["relevance"] == "Different time period" for row in result["per_source"])
    predictor.assert_not_called()


def test_experimental_reverse_rule_does_not_override_historical_attribution():
    claim = "The Sun revolves around the Earth."
    results = [tavily_result(1, "Historically, people believed Earth revolved around the Sun."),
               tavily_result(2, "In the ancient geocentric debate, scholars described Earth moving around the Sun.")]
    predictor = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(claim, results, predictor, experimental_semantic=True)
    assert result["verdict"] == "Inconclusive"
    assert all(not row["part_assessments"][0]["contributed"] for row in result["per_source"])


def test_experimental_path_keeps_conflicting_source_passages_inconclusive():
    claim = "The Sun revolves around the Earth."
    results = [tavily_result(1, "The Sun revolves around the Earth."),
               tavily_result(2, "Earth revolves around the Sun, not the reverse.")]
    predict = Mock(side_effect=[prediction("SUPPORTS"), prediction("SUPPORTS")])
    result = assess_evidence_nli(claim, results, predict, experimental_semantic=True)
    assert result["verdict"] == "Inconclusive"
    assert [row["part_assessments"][0]["label"] for row in result["per_source"]] == [
        "SUPPORTS", "CONTRADICTS"]


def test_experimental_path_deduplicates_syndicated_passages_across_urls():
    text = "The Sun revolves around the Earth once per year according to this source."
    results = [tavily_result(1, text), tavily_result(2, text)]
    result = assess_evidence_nli("The Sun revolves around the Earth.", results,
                                 Mock(return_value=prediction("SUPPORTS")),
                                 experimental_semantic=True)
    assert result["verdict"] == "Inconclusive"
    assert result["per_source"][0]["part_assessments"][0]["contributed"] is True
    assert result["per_source"][1]["part_assessments"][0]["contributed"] is False


def test_experimental_splitter_preserves_named_entity_lists_and_disjunctions():
    entity_list = "Mars has two moons, Phobos and Deimos."
    joined_entities = "Earth and Mars are planets."
    disjunction = "The satellite is Phobos or Deimos."

    assert _claim_parts(entity_list) == ["Mars has two moons, Phobos", "Deimos"]
    assert _claim_parts_experimental(entity_list) == [entity_list]
    assert _claim_parts_experimental(joined_entities) == [joined_entities]
    assert _claim_parts_experimental(disjunction) == [disjunction]


def test_experimental_splitter_separates_only_independent_and_clauses():
    claim = "Earth revolves around the Sun, and the Moon orbits Earth."
    assert _claim_parts_experimental(claim) == [
        "Earth revolves around the Sun", "the Moon orbits Earth"]


def test_experimental_full_claim_can_be_supported_while_legacy_name_split_abstains():
    claim = "Mars has two moons, Phobos and Deimos."
    results = [tavily_result(1, "Mars has two moons: Phobos and Deimos."),
               tavily_result(2, "Phobos and Deimos are the two moons that orbit Mars.")]

    def predictor(_premise, hypothesis):
        if hypothesis.strip().casefold() == "deimos":
            return prediction("NEUTRAL")
        return prediction("ENTAILMENT")

    production = assess_evidence_nli(claim, results, predictor)
    experimental = assess_evidence_nli(claim, results, predictor, experimental_semantic=True)
    assert production["verdict"] == "Inconclusive"
    assert experimental["verdict"] == "Supported"
    assert experimental["original_claim"] == claim
    assert all(item["claim_part"] == claim for row in experimental["per_source"]
               for item in row["part_assessments"])


def test_experimental_independent_components_still_require_each_to_have_evidence():
    claim = "Earth revolves around the Sun, and the Moon orbits Earth."
    results = [tavily_result(1, "Earth revolves around the Sun."),
               tavily_result(2, "Earth completes an orbit around the Sun each year.")]
    def predictor(_premise, hypothesis):
        return prediction("ENTAILMENT" if "earth revolves" in hypothesis.lower() else "NEUTRAL")
    result = assess_evidence_nli(claim, results, predictor, experimental_semantic=True)
    assert result["original_claim"] == claim
    assert result["verdict"] == "Inconclusive"
    assert [entry["verdict"] for entry in result["part_outcomes"]] == ["Supported", "Inconclusive"]


def test_experimental_compound_components_with_opposite_directions_are_inconclusive():
    claim = "Earth revolves around the Sun, and the Moon orbits Earth."
    results = [
        tavily_result(1, "Earth revolves around the Sun in its yearly orbit."),
        tavily_result(2, "The Sun is orbited by Earth once each year."),
        tavily_result(3, "Earth revolves around the Moon, not the other way around."),
        tavily_result(4, "Earth orbits the Moon in a monthly path."),
    ]

    def predictor(premise, hypothesis):
        if "moon orbits earth" in hypothesis.lower():
            return prediction("CONTRADICTION")
        return prediction("ENTAILMENT")

    result = assess_evidence_nli(claim, results, predictor, experimental_semantic=True)
    assert [item["verdict"] for item in result["part_outcomes"]] == ["Supported", "Contradicted"]
    assert result["verdict"] == "Inconclusive"


def test_explicit_sun_revolves_earth_assertion_remains_eligible_as_support():
    claim = "The Sun revolves around the Earth."
    results = [tavily_result(1, "The Sun revolves around the Earth in this stated proposition.")]
    predict = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(claim, results, predict)
    component = result["per_source"][0]["part_assessments"][0]
    assert component["label"] == "SUPPORTS"
    assert component["contributed"] is True
    assert result["verdict"] == "Inconclusive"


def test_unrelated_scope_phrase_elsewhere_does_not_veto_explicit_assertion():
    claim = "The Earth revolves around the Sun."
    content = ("The Earth revolves in orbit around the Sun. "
               "A separate question asks which revolves around which in other reference frames.")
    predict = Mock(side_effect=[prediction("ENTAILMENT"), prediction("NEUTRAL")])
    result = assess_evidence_nli(claim, [tavily_result(1, content)], predict)
    component = result["per_source"][0]["part_assessments"][0]
    assert component["label"] == "SUPPORTS"
    assert component["contributed"] is True


def test_genuine_independent_opposite_evidence_remains_conflicting():
    claim = "The Sun revolves around the Earth."
    results = [
        tavily_result(1, "The Sun revolves around the Earth."),
        tavily_result(2, "The Earth revolves around the Sun, not the reverse."),
    ]
    predict = Mock(side_effect=[prediction("ENTAILMENT"), prediction("CONTRADICTION")])
    result = assess_evidence_nli(claim, results, predict)
    assert result["verdict"] == "Inconclusive"
    assert [row["part_assessments"][0]["label"] for row in result["per_source"]] == ["SUPPORTS", "CONTRADICTS"]
    assert all(row["part_assessments"][0]["contributed"] for row in result["per_source"])


def test_irrelevant_keyword_overlap_is_not_sent_to_nli():
    results = [
        tavily_result(1, "Paris attracts visitors who enjoy architecture."),
        tavily_result(2, "The Eiffel Tower is a popular tourist attraction."),
    ]
    predict = Mock(return_value=prediction("ENTAILMENT"))
    result = assess_evidence_nli(CLAIM, results, predict)
    assert result["verdict"] == "Inconclusive"
    predict.assert_not_called()


def test_existing_nli_confidence_thresholds_are_preserved():
    assert MIN_CONFIDENCE == 0.70
    assert MIN_MARGIN == 0.15
    assert MIN_DIRECTIONAL_SOURCES == 2


def test_conflicting_nli_predictions_are_inconclusive(mocked_tavily_results):
    predict = Mock(side_effect=[prediction("ENTAILMENT"), prediction("CONTRADICTION")])
    result = assess_evidence_nli(CLAIM, mocked_tavily_results, predict)
    assert result["verdict"] == "Inconclusive"
    assert "conflicts" in result["reasoning"]


def test_conflicting_passages_from_one_source_are_not_mislabeled_unrelated():
    results = [tavily_result(1,
        "The Eiffel Tower is located in Paris. The Eiffel Tower is not located in Paris today.")]
    predict = Mock(side_effect=[prediction("ENTAILMENT"), prediction("CONTRADICTION")])
    result = assess_evidence_nli(CLAIM, results, predict)
    assert result["verdict"] == "Inconclusive"
    assert result["per_source"][0]["relevance"] == "Directly relevant candidate"
    assert "conflict" in result["per_source"][0]["status"].lower()
    assert result["per_source"][0]["part_assessments"][0]["label"] == "CONFLICTING"


def test_low_confidence_and_neutral_are_inconclusive(mocked_tavily_results):
    predict = Mock(side_effect=[prediction("ENTAILMENT", 0.45, 0.02), prediction("NEUTRAL")])
    result = assess_evidence_nli(CLAIM, mocked_tavily_results, predict)
    assert result["verdict"] == "Inconclusive"
    assert [row["label"] for row in result["per_source"]] == ["UNCERTAIN", "NOT ENOUGH INFORMATION"]


def test_regression_earth_orbits_sun_supported():
    claim = "The Earth revolves around the Sun."
    results = [
        tavily_result(1, "NASA states that Earth revolves in orbit around the Sun in 365 days."),
        tavily_result(2, "Earth orbits the Sun, completing one revolution in about one year."),
    ]
    def model_mock(premise, hypothesis):
        assert "earth" in premise.lower() and "sun" in premise.lower()
        assert "earth" in hypothesis.lower() and "sun" in hypothesis.lower()
        assert hypothesis.rstrip(".") == claim.rstrip(".")
        return prediction("ENTAILMENT")
    result = assess_evidence_nli(claim, results, model_mock)
    assert result["verdict"] == "Supported"
    assert all(row["label"] == "SUPPORTS" for row in result["per_source"])


def test_regression_multi_part_geocentric_claim_needs_each_part_contradicted():
    claim = "The Earth is the center of the Solar System, and the Sun revolves around the Earth."
    results = [
        tavily_result(1, "The Sun, not Earth, is at the center of the Solar System. Earth revolves around the Sun, rather than the Sun revolving around Earth."),
        tavily_result(2, "Current astronomy places the Sun, not Earth, at the center of the Solar System. The Sun does not revolve around Earth; Earth revolves around the Sun."),
    ]
    def model_mock(premise, hypothesis):
        # Mock prediction behavior follows the premise/hypothesis relationship, not a claim string lookup.
        if "not earth" in premise.lower() or "does not revolve around earth" in premise.lower():
            return prediction("CONTRADICTION")
        if "earth revolves around the sun" in premise.lower():
            return prediction("CONTRADICTION")
        return prediction("NEUTRAL")
    result = assess_evidence_nli(claim, results, model_mock)
    assert result["verdict"] == "Contradicted"
    assert [item["verdict"] for item in result["part_outcomes"]] == ["Contradicted", "Contradicted"]


def test_compound_claim_one_contradicted_part_does_not_decide_whole_claim():
    claim = "The Earth is the center of the Solar System, and the Sun revolves around the Earth."
    results = [
        tavily_result(1, "The Sun, not Earth, is at the center of the Solar System."),
        tavily_result(2, "The Solar System's center is the Sun rather than Earth."),
    ]
    predict = Mock(return_value=prediction("CONTRADICTION"))
    result = assess_evidence_nli(claim, results, predict)
    assert result["verdict"] == "Inconclusive"
    assert [item["verdict"] for item in result["part_outcomes"]] == ["Contradicted", "Inconclusive"]


def test_regression_unrecorded_private_event_stays_inconclusive():
    claim = "A person in an unrecorded private meeting yesterday promised to launch a new company next week."
    results = [
        tavily_result(1, "A company launch campaign can use email, scarcity, and product announcements."),
        tavily_result(2, "A founder said a company promise helped the team plan its next product launch."),
    ]
    predict = Mock(return_value=prediction("CONTRADICTION"))
    result = assess_evidence_nli(claim, results, predict)
    assert result["verdict"] == "Inconclusive"
    assert "does not establish falsity" in result["reasoning"]
    predict.assert_not_called()


def test_failed_model_load_uses_rule_based_fallback(mocked_tavily_results):
    def broken_loader():
        raise OSError("model download unavailable")
    unrelated = [tavily_result(1, "Paris is a popular destination for travelers."),
                 tavily_result(2, "The Eiffel Tower attracts millions of visitors.")]
    result = assess_with_optional_nli(CLAIM, unrelated, broken_loader)
    assert result["fallback_used"] is True
    assert result["verdict"] == "Inconclusive"
    assert "fallback" in result["method"].lower()
    assert all(row["label"] == "NLI not run" for row in result["per_source"])


def test_no_results_do_not_load_model():
    loader = Mock(side_effect=AssertionError("model should not load without snippets"))
    result = assess_with_optional_nli(CLAIM, [], loader)
    assert result["verdict"] == "Inconclusive"
    assert "no evidence to classify" in result["reasoning"]
    loader.assert_not_called()


def test_tavily_response_is_mocked_offline(monkeypatch):
    response = Mock()
    response.status_code = 200
    response.ok = True
    response.json.return_value = {"results": [dict(tavily_result(1, "A retrieved snippet."), publisher="NASA")]}
    post = Mock(return_value=response)
    monkeypatch.setattr("verifier.requests.post", post)
    results = search_evidence("A test claim", "mock-key")
    assert results[0]["title"] == "Mock source 1"
    assert results[0]["url"] == "https://source-1.example/page"
    assert results[0]["content"] == "A retrieved snippet."
    assert results[0]["publisher"] == "NASA"
    assert results[0]["retrieved_at"].endswith("+00:00")
    assert post.call_args.kwargs["json"]["api_key"] == "mock-key"
    assert post.call_args.kwargs["json"]["query"] == "A test claim"
    post.assert_called_once()


def test_search_preserves_original_snippet_and_deduplicates_tracking_url(monkeypatch):
    original = "  ### Heading\n\nText with   spacing. " + ("Long evidence. " * 140)
    response = Mock()
    response.status_code = 200
    response.ok = True
    response.json.return_value = {"results": [
        {"title": "## Original title", "url": "https://example.com/Case?utm_source=one",
         "content": original, "published_date": "2026-01-02"},
        {"title": "Duplicate", "url": "https://example.com/Case/?utm_source=two",
         "content": original, "published_date": None},
    ]}
    monkeypatch.setattr("verifier.requests.post", Mock(return_value=response))
    results = search_evidence("claim", "mock-key")
    assert len(results) == 1
    assert results[0]["title"] == "## Original title"
    assert results[0]["url"] == "https://example.com/Case?utm_source=one"
    assert results[0]["content"] == original
    assert results[0]["published_date"] == "2026-01-02"
    assert results[0]["retrieved_at"].endswith("+00:00")


def test_search_handles_malformed_optional_metadata_and_bad_entries(monkeypatch):
    response = Mock()
    response.status_code = 200
    response.ok = True
    response.json.return_value = {"results": [
        None,
        {"title": 12, "url": "https://example.com/page", "content": ["not", "text"], "published_date": {}},
        {"title": "bad URL", "url": "javascript:alert(1)", "content": "ignored"},
    ]}
    monkeypatch.setattr("verifier.requests.post", Mock(return_value=response))
    results = search_evidence("claim", "mock-key")
    assert len(results) == 1
    assert results[0]["title"] == ""
    assert results[0]["url"] == "https://example.com/page"
    assert results[0]["content"] == ""
    assert results[0]["published_date"] == ""
    assert results[0]["publisher"] == ""
    assert results[0]["retrieved_at"].endswith("+00:00")
