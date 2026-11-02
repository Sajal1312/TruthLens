"""Offline checks for transparent source context and ranking signals."""

from evidence_quality import (NEAR_DUPLICATE_JACCARD_THRESHOLD, passage_similarity,
                              provenance_diagnostics, publication_date_signal,
                              source_context, source_category_order)


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


def test_provenance_diagnostics_show_duplicates_but_never_claim_independence():
    text = ("A long evidence passage about the orbit of Earth around the Sun with enough shared words "
            "to compare source passages through a normalized three word shingle similarity measure, "
            "including details about seasons, orbital distance, annual movement, and planetary motion.")
    results = [
        {"title": "First page", "url": "https://news.example.com/a?utm_source=x",
         "content": text, "published_date": "2026-10-30", "retrieved_at": "2026-11-01T10:00:00+00:00"},
        {"title": "Second page", "url": "https://other.example.org/b",
         "content": text.replace("normalized", "standardized"), "published_date": "", "retrieved_at": "2026-11-01T10:00:00+00:00"},
    ]
    records = provenance_diagnostics(results)
    assert passage_similarity(text, results[1]["content"]) >= NEAR_DUPLICATE_JACCARD_THRESHOLD
    assert records[0]["publisher"] == "Not provided"
    assert records[0]["domain"] == "news.example.com"
    assert records[0]["published_date"] == "2026-10-30"
    assert records[0]["retrieved_at"] == "2026-11-01T10:00:00+00:00"
    assert records[0]["independence"].lower().startswith("unknown;")
    assert any("near-duplicates" in note for note in records[0]["relationships"][0]["notes"])
    near_duplicate = next(item for item in records[0]["relationships"][0]["observations"]
                          if item["type"] == "near_duplicate_snippet")
    assert near_duplicate["kind"] == "heuristic_inference"
    assert "does not establish shared authorship or syndication" in near_duplicate["basis"]
    assert records[0]["origin_relationship"].startswith("Not available")


def test_same_host_is_not_mislabeled_as_same_publisher_or_independent():
    records = provenance_diagnostics([
        {"url": "https://example.com/a", "content": "First unrelated passage."},
        {"url": "https://example.com/b", "content": "Second unrelated passage."},
    ])
    assert any("Same exact host" in note for note in records[0]["relationships"][0]["notes"])
    same_host = next(item for item in records[0]["relationships"][0]["observations"]
                     if item["type"] == "same_exact_host")
    assert same_host["kind"] == "observed"
    assert "host names parsed" in same_host["basis"]
    assert records[0]["publisher"] == "Not provided"
    assert "unknown" in records[0]["independence"].lower()
