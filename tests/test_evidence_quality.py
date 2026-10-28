"""Offline checks for transparent source context and ranking signals."""

from evidence_quality import publication_date_signal, source_context, source_category_order


def test_known_science_host_is_a_category_not_a_truth_claim():
    context = source_context("https://science.nasa.gov/earth/")
    assert context["category"] == "Scientific institution / publication"
    assert "not verification" in context["note"]


def test_unknown_suffix_does_not_receive_an_automatic_credibility_label():
    context = source_context("https://example.gov/page")
    assert context["category"] == "Government domain (unverified)"
    assert context["basis"] == "domain suffix only"
    assert "not verification" in context["note"]


def test_unknown_domain_and_malformed_url_are_handled_conservatively():
    assert source_context("https://unknown.example/page")["category"] == "Unknown"
    assert source_context("javascript:alert(1)")["category"] == "Unknown"


def test_source_category_order_is_only_a_deterministic_tie_breaker():
    assert source_category_order("Scientific institution / publication") < source_category_order("Unknown")
    assert source_category_order("Unknown") == 7


def test_publication_date_signal_is_contextual_not_a_verdict():
    assert publication_date_signal("The latest report is accurate.", "2026-10-24") == \
        "Publication date available for time-sensitive claim"
    assert publication_date_signal("The Eiffel Tower is in Paris.", "") == "No publication date returned"
