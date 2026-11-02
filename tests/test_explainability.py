"""Developer-authored explanation checks; synthetic evidence, no live sources.

These check trace/display agreement with the pipeline, not model truth accuracy.
"""
from copy import deepcopy
from unittest.mock import Mock

import pytest

from explainability import build_explanation, evidence_excerpt, highlighted_evidence
from nli_assessor import assess_evidence_nli, assess_with_optional_nli
from verifier import assess_evidence


CLAIM = "The Eiffel Tower is located in Paris."
SUPPORT = [
    "The Eiffel Tower is located in Paris, France.",
    "The Eiffel Tower is located in Paris near the Champ de Mars.",
]
CONTRADICTION = [
    "The Eiffel Tower is not located in Paris, France.",
    "The Eiffel Tower is not located in Paris according to this fictional guide.",
]


def sources(passages):
    return [{"title": "Synthetic source {0}".format(index),
             "url": "https://source-{0}.example/page".format(index),
             "content": text, "published_date": ""} for index, text in enumerate(passages)]


@pytest.mark.parametrize("passages, labels, verdict, tones", [
    (SUPPORT, ["SUPPORTS", "SUPPORTS"], "Supported", ["support", "support"]),
    (CONTRADICTION, ["CONTRADICTS", "CONTRADICTS"], "Contradicted", ["contradiction", "contradiction"]),
    (SUPPORT[:1], ["SUPPORTS"], "Inconclusive", ["support"]),
    (SUPPORT[:1], ["NOT ENOUGH INFORMATION"], "Inconclusive", ["neutral"]),
    ([SUPPORT[0], CONTRADICTION[1]], ["SUPPORTS", "CONTRADICTS"], "Inconclusive", ["support", "contradiction"]),
    (["The Eiffel Tower attracts visitors from Paris."], [], "Inconclusive", ["neutral"]),
    ([], [], "Inconclusive", []),
])
def test_explanation_matches_actual_pipeline_decisions_without_mutation(passages, labels, verdict, tones):
    results = sources(passages)
    predictor = Mock(side_effect=[{"label": label, "confidence": .92, "margin": .60} for label in labels])
    assessment = assess_evidence_nli(CLAIM, results, predictor)
    before = deepcopy((results, assessment))
    explanation = build_explanation(CLAIM, results, assessment)

    assert explanation["verdict"] == assessment["verdict"] == verdict
    assert explanation["reasoning"] == assessment["reasoning"]
    assert explanation["evidence_used"] == assessment["evidence_used"]
    assert [entry["tone"] for entry in explanation["entries"]] == tones
    assert len(explanation["entries"]) == len(results)
    for entry, row, source in zip(explanation["entries"], assessment["per_source"], results):
        assert entry["contributed"] == row["part_assessments"][0]["contributed"]
        assert entry["status"] == row["part_assessments"][0]["status"]
        assert entry["excerpt"]["text"] in source["content"]
        assert entry["url"] == source["url"]
    assert (results, assessment) == before
    assert predictor.call_count == len(labels)


@pytest.mark.parametrize("content, confidence, expected_reason", [
    ("Ancient people believed the Eiffel Tower is located in Paris.", .92, "Historical"),
    ("What if the Eiffel Tower is located in Paris?", .92, "hypothetical"),
    (SUPPORT[0], .60, "below threshold"),
])
def test_rejected_raw_support_never_appears_as_counted_support(content, confidence, expected_reason):
    results = sources([content])
    assessment = assess_evidence_nli(CLAIM, results, Mock(return_value={
        "label": "SUPPORTS", "confidence": confidence, "margin": .55}))
    entry = build_explanation(CLAIM, results, assessment)["entries"][0]
    assert entry["model_label"] == "SUPPORTS"
    assert entry["tone"] == "neutral"
    assert entry["contributed"] is False
    assert expected_reason in entry["status"]


def test_within_source_conflict_preserves_both_passages_without_votes():
    results = sources([SUPPORT[0] + " " + CONTRADICTION[0]])
    assessment = assess_evidence_nli(CLAIM, results, Mock(side_effect=[
        {"label": "SUPPORTS", "confidence": .95, "margin": .70},
        {"label": "CONTRADICTS", "confidence": .94, "margin": .65}]))
    explanation = build_explanation(CLAIM, results, assessment)
    assert explanation["verdict"] == "Inconclusive"
    assert len(explanation["entries"]) == 2
    assert {entry["passage_label"] for entry in explanation["entries"]} == {"SUPPORTS", "CONTRADICTS"}
    assert all(entry["label"] == "CONFLICTING" and not entry["contributed"] for entry in explanation["entries"])
    assert all(entry["excerpt"]["recorded_passage_located"] for entry in explanation["entries"])


def test_duplicate_passage_exclusion_and_provenance_are_visible():
    results = sources([SUPPORT[0], SUPPORT[0]])
    assessment = assess_evidence_nli(CLAIM, results, Mock(return_value={
        "label": "SUPPORTS", "confidence": .92, "margin": .60}))
    explanation = build_explanation(CLAIM, results, assessment)
    assert [entry["tone"] for entry in explanation["entries"]] == ["support", "neutral"]
    assert "Repeated passage" in explanation["entries"][1]["status"]
    assert any("identical" in warning for warning in explanation["entries"][1]["warnings"])


def test_publication_update_and_retrieval_dates_are_never_interchanged():
    results = sources(SUPPORT[:1])
    results[0].update(updated_date="2026-10-01", retrieved_at="2026-11-02T00:00:00Z")
    assessment = assess_evidence(CLAIM, results)
    entry = build_explanation(CLAIM, results, assessment)["entries"][0]
    assert entry["published_date"] == ""
    assert entry["updated_date"] == "2026-10-01"
    del results[0]["updated_date"]
    entry = build_explanation(CLAIM, results, assessment)["entries"][0]
    assert entry["updated_date"] == ""


def test_highlight_escapes_script_html_markdown_and_attribute_payloads():
    payload = '<script>alert("x")</script><img src=x onerror="alert(1)"> ## Heading & evidence'
    rendered = highlighted_evidence(payload, 'support" onclick="evil')
    assert '<script' not in rendered and '<img' not in rendered
    assert '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;' in rendered
    assert 'class="evidence-neutral"' in rendered
    assert '## Heading &amp; evidence' in rendered
    assert rendered.count('<mark ') == 1


def test_excerpt_is_exact_source_span_even_when_window_normalized_line_breaks():
    content = "Background sentence.\nThe Eiffel Tower\n is located in Paris."
    selected = evidence_excerpt(content, CLAIM, "The Eiffel Tower is located in Paris.")
    assert selected["recorded_passage_located"]
    assert selected["text"] == "The Eiffel Tower\n is located in Paris."
    assert selected["text"] in content
    long_excerpt = evidence_excerpt("Word " * 200, CLAIM)
    assert len(long_excerpt["text"]) <= 360 and long_excerpt["shortened"]


def test_missing_trace_or_mismatched_source_is_reported_without_inventing_votes():
    results = sources(SUPPORT[:1])
    assessment = {"verdict": "Inconclusive", "per_source": [{
        "url": "https://different.example/page", "label": "SUPPORTS", "contributed": True}]}
    entry = build_explanation(CLAIM, results, assessment)["entries"][0]
    assert entry["contributed"] is None
    assert entry["tone"] == "neutral"
    assert "mismatch" in entry["status"]
    assessment["per_source"] = [{"url": results[0]["url"], "label": "SUPPORTS", "contributed": True,
                                 "passage": "Invented passage that was never retrieved"}]
    entry = build_explanation(CLAIM, results, assessment)["entries"][0]
    assert not entry["excerpt"]["recorded_passage_located"]
    assert entry["tone"] == "neutral"
    assert entry["excerpt"]["text"] in results[0]["content"]


def test_fallback_uses_recorded_reason_and_does_not_invent_per_source_votes():
    results = sources(SUPPORT)
    assessment = assess_with_optional_nli(CLAIM, results, model_loader=Mock(side_effect=RuntimeError))
    explanation = build_explanation(CLAIM, results, assessment)
    assert explanation["verdict"] == "Supported"
    assert explanation["reasoning"] == assessment["reasoning"]
    assert all(entry["contributed"] is None for entry in explanation["entries"])
    assert all(entry["model_label"] == "" for entry in explanation["entries"])


def test_partial_compound_evidence_keeps_original_claim_and_each_component_trace():
    claim = "The Eiffel Tower is located in Paris and Berlin is located in Germany."
    results = sources(SUPPORT)
    assessment = assess_evidence_nli(claim, results, Mock(return_value={
        "label": "SUPPORTS", "confidence": .92, "margin": .60}))
    explanation = build_explanation(claim, results, assessment)
    assert explanation["claim"] == claim
    assert explanation["verdict"] == "Inconclusive"
    assert explanation["components"] == assessment["part_outcomes"]
    assert [part["verdict"] for part in explanation["components"]] == ["Supported", "Inconclusive"]
    berlin = [entry for entry in explanation["entries"] if "Berlin" in entry["claim_part"]]
    assert len(berlin) == 2
    assert all(entry["tone"] == "neutral" and entry["contributed"] is False for entry in berlin)


def test_time_exclusion_has_no_invented_nli_prediction():
    claim = "The Eiffel Tower is located in Paris in 2026."
    results = sources(["In 2019, the Eiffel Tower is located in Paris."])
    predictor = Mock(side_effect=AssertionError("date-excluded text must not reach inference"))
    assessment = assess_evidence_nli(claim, results, predictor)
    entry = build_explanation(claim, results, assessment)["entries"][0]
    assert entry["tone"] == "neutral"
    assert entry["model_label"] == ""
    assert "different year" in entry["status"]
    predictor.assert_not_called()
