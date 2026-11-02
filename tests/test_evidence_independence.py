"""Synthetic provenance diagnostics; never evidence of real reporting independence."""
from copy import deepcopy
from itertools import combinations
from unittest.mock import Mock

import pytest

from evidence_independence import (analyze_evidence_independence, extract_attributions,
                                   normalize_source_url)
from evidence_quality import passage_similarity
from explainability import build_explanation
from nli_assessor import assess_evidence_nli
from verifier import assess_evidence


LONG = ("A long synthetic evidence passage describes a laboratory sensor with enough shared words "
        "to compare source passages through a normalized three word shingle similarity measure, "
        "including details about calibration, orbital distance, annual movement, seasonal observations, "
        "and the inspection procedure used by technicians.")


def sources(*passages):
    return [{"title": "Synthetic source " + str(index), "url": "https://source-{0}.example/article".format(index),
             "content": passage} for index, passage in enumerate(passages)]


def relationship(*passages):
    return analyze_evidence_independence(sources(*passages))["relationships"][0]


def test_url_normalization_covers_known_harmless_variations_without_editing_sources():
    first = "HTTPS://NEWS.EXAMPLE:443/article?id=7&utm_source=x&fbclid=y#section-2"
    second = "https://news.example/article?id=7#top"
    assert normalize_source_url(first) == normalize_source_url(second) == "https://news.example/article?id=7"
    assert normalize_source_url("https://news.example") == normalize_source_url("https://news.example/")
    rows = sources("First passage", "Second passage")
    rows[0]["url"], rows[1]["url"] = first, second
    before = deepcopy(rows)
    output = analyze_evidence_independence(rows)
    assert output["counts"]["distinct_source_urls"] == 1
    assert output["relationships"][0]["same_document"]
    assert rows == before


@pytest.mark.parametrize("left, right", [
    ("https://news.example/a", "https://news.example/a/"),
    ("https://news.example/Article", "https://news.example/article"),
    ("https://news.example/a?id=1", "https://news.example/a?id=2"),
    ("https://news.example/a?step=1&step=2", "https://news.example/a?step=2&step=1"),
    ("http://news.example/a", "https://news.example/a"),
    ("https://www.news.example/a", "https://news.example/a"),
    ("https://news.example/#/article-1", "https://news.example/#/article-2"),
    ("https://news.example/#post-1", "https://news.example/#post-2"),
    ("https://news.example/a%2Fb", "https://news.example/a/b"),
])
def test_distinct_article_identifiers_routes_and_order_are_preserved(left, right):
    assert normalize_source_url(left) != normalize_source_url(right)


@pytest.mark.parametrize("url", [None, "", "javascript:alert(1)", "https://x.example:wrong/a",
                                   "https://x.example:70000/a", "https://x.example/a b", "https://[broken/a",
                                   "https://user:password@x.example/a", "https://x.example/a%GG",
                                   'https://x.example/a"onclick="bad', "https://bad_host.example/a", {}])
def test_malformed_or_missing_urls_never_form_a_source_identity(url):
    assert normalize_source_url(url) is None


def test_exact_text_normalizes_whitespace_but_does_not_claim_shared_authorship():
    row = relationship("A synthetic passage.\n More context.", "A synthetic passage.   More context.")
    assert row["category"] == "Exact duplicate" and row["exact_duplicate"]
    assert row["group_eligible"]
    assert all(signal["kind"] == "observed" for signal in row["signals"])
    assert "authorship is not established" in row["signals"][0]["message"]
    empty = relationship("", "")
    assert not empty["exact_duplicate"] and not empty["group_eligible"]


def test_near_duplicate_wording_is_heuristic_not_confirmed_copying():
    second = LONG.replace("normalized", "standardized")
    assert passage_similarity(LONG, second) >= .80
    row = relationship(LONG, second)
    assert row["near_duplicate"] and row["category"] == "Near duplicate"
    assert row["signals"][0]["kind"] == "heuristic"
    assert "not proof of copying" in row["signals"][0]["message"]


@pytest.mark.parametrize("score, near", [(.799, False), (.800, True)])
def test_diagnostic_similarity_boundary_is_explicit(monkeypatch, score, near):
    monkeypatch.setattr("evidence_independence.passage_similarity", lambda *_args: score)
    assert relationship(LONG, LONG.replace("normalized", "standardized"))["near_duplicate"] is near


@pytest.mark.parametrize("first, second", [
    (LONG + " The laboratory is safe.", LONG + " The laboratory is not safe."),
    (LONG + " The count is 20.", LONG + " The count is 30."),
    (LONG + " All sensors passed.", LONG + " Some sensors passed."),
])
def test_changed_negation_numbers_or_quantifiers_prevent_similarity_only_groups(first, second):
    assert passage_similarity(first, second) >= .80
    row = relationship(first, second)
    assert row["scope_difference"] and not row["near_duplicate"]
    assert row["category"] == "Possible dependency" and not row["group_eligible"]


def test_short_common_phrases_are_not_grouped_from_similarity_alone():
    row = relationship("A synthetic sensor works.", "A synthetic sensor works!")
    assert row["text_similarity"] == 1.0
    assert not row["near_duplicate"] and not row["group_eligible"]


def test_attribution_extraction_records_literal_spans_without_inventing_origins():
    text = ('According to NASA, a fictional test ended. Reuters reported a fictional budget. '
            'A report titled "Demo Survey" is at https://reports.example/survey.')
    rows = extract_attributions(text)
    assert {row["key"] for row in rows if row["kind"] == "organization_attribution"} == {"nasa", "reuters"}
    assert any(row["kind"] == "report_title" and row["target"] == "Demo Survey" for row in rows)
    assert any(row["kind"] == "citation_url" for row in rows)
    assert all(text[row["start"]:row["end"]] == row["text"] for row in rows)
    assert extract_attributions("NASA is mentioned in this constructed sentence.") == []
    assert extract_attributions("This is not according to NASA.") == []


def test_shared_institution_or_title_is_only_possible_dependency():
    row = relationship('According to NASA, a report titled "Demo Survey" describes staffing.',
                       'According to NASA, a report titled "Demo Survey" describes repairs.')
    assert row["category"] == "Possible dependency"
    assert not row["explicit_dependency"] and not row["group_eligible"]


def test_shared_identifiable_report_or_direct_citation_is_observed_reference_only():
    rows = sources("The original report is at https://reports.example/original.",
                   "A review cites the report at https://reports.example/original.")
    output = analyze_evidence_independence(rows)
    row = output["relationships"][0]
    assert row["explicit_dependency"] and row["category"] == "Explicit shared-source dependency"
    assert any(signal["code"] == "citation_url" and signal["kind"] == "observed" for signal in row["signals"])
    rows[0]["url"] = "https://reports.example/original"
    rows[0]["content"] = "The synthetic survey details a sampling method."
    row = analyze_evidence_independence(rows)["relationships"][0]
    assert any(signal["code"] == "direct_citation" for signal in row["signals"])


def test_doi_reference_is_detected_as_supplied_not_verified():
    row = relationship("A synthetic study DOI 10.0000/demo-fixture describes staffing.",
                       "Another note cites DOI 10.0000/demo-fixture for the sampling method.")
    assert row["explicit_dependency"]
    assert any(signal["code"] == "doi" for signal in row["signals"])


def test_navigation_links_and_negated_reliance_are_not_promoted_to_report_dependency():
    row = relationship("One invented observation. Subscribe at https://portal.example/home.",
                       "Different invented context. Subscribe at https://portal.example/home.")
    assert not row["explicit_dependency"] and not row["group_eligible"]
    rows = extract_attributions("We are not relying on the report at https://reports.example/survey.")
    assert any(row["kind"] == "mentioned_url" for row in rows)
    assert not any(row["kind"] == "citation_url" for row in rows)


def test_same_publisher_different_articles_remain_ungrouped():
    rows = [{"url": "https://org.example/a", "publisher": "Demo Publisher", "content": "Fictional budget discussion."},
            {"url": "https://org.example/b", "publisher": "Demo Publisher", "content": "Synthetic maintenance schedule."}]
    output = analyze_evidence_independence(rows)
    assert output["relationships"][0]["category"] == "Possible dependency"
    assert [row["members"] for row in output["groups"]] == [[0], [1]]
    assert all(row["independence"] == "Independence not established" for row in output["sources"])


def test_complete_link_groups_do_not_create_a_transitive_citation_relationship():
    rows = sources("The first report is at https://reports.example/first.",
                   "The first report is at https://reports.example/first. The second report is at https://reports.example/second.",
                   "The second report is at https://reports.example/second.")
    output = analyze_evidence_independence(rows)
    assert [group["members"] for group in output["groups"]] == [[0, 1], [1, 2]]
    by_pair = {(row["left"], row["right"]): row for row in output["relationships"]}
    for group in output["groups"]:
        assert all(by_pair[pair]["group_eligible"] for pair in combinations(group["members"], 2))
        assert group["relationship_ids"] and group["basis"]


def test_weak_shared_institution_bridge_never_forms_groups():
    output = analyze_evidence_independence(sources("According to NASA, a fictional instrument returned images.",
                                                 "According to NASA, a fictional mission tested signals. Reuters reported a fictional budget.",
                                                 "Reuters reported fictional equipment repairs."))
    assert all(len(group["members"]) == 1 for group in output["groups"])


def test_missing_metadata_empty_inputs_and_counts_are_explicit():
    output = analyze_evidence_independence([{}, None, {"content": "An observation", "url": "invalid"}])
    assert output["counts"]["retrieved_passages"] == 3
    assert output["counts"]["nonempty_passages"] == 1
    assert output["counts"]["distinct_source_urls"] == 0
    assert output["counts"]["invalid_or_missing_urls"] == 3
    assert all(len(group["members"]) == 1 for group in output["groups"])
    assert analyze_evidence_independence([])["groups"] == []
    duplicates = analyze_evidence_independence(sources("Same synthetic text.", "Same synthetic text.", "Same synthetic text."))
    assert duplicates["counts"]["exact_duplicate_pairs"] == 3
    assert duplicates["counts"]["repeated_passage_entries"] == 2


@pytest.mark.parametrize("mode", ["rule", "nli"])
def test_diagnostics_do_not_modify_verdict_counts_original_text_or_model_calls(mode):
    claim = "The Eiffel Tower is located in Paris."
    rows = sources("The Eiffel Tower is located in Paris, France.",
                   "The Eiffel Tower is located in Paris near the Champ de Mars.")
    for row in rows:
        row["publisher"] = "Same declared publisher"
    predictor = Mock(return_value={"label": "SUPPORTS", "confidence": .92, "margin": .60})
    assessment = assess_evidence(claim, rows) if mode == "rule" else assess_evidence_nli(claim, rows, predictor)
    before = deepcopy((rows, assessment))
    explanation = build_explanation(claim, rows, assessment)
    assert explanation["verdict"] == "Supported"
    assert explanation["independence"]["relationships"][0]["category"] == "Possible dependency"
    assert (rows, assessment) == before
    assert predictor.call_count == (0 if mode == "rule" else 2)
