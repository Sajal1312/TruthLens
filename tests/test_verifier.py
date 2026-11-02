"""Offline tests for conservative claim assessment; no network calls are made."""
import pytest
import requests

from unittest.mock import Mock

from verifier import (VerificationError, assess_evidence, search_evidence,
                      search_evidence_with_metrics)


CLAIM = "The Eiffel Tower is located in Paris."


def result(title, url, content):
    return {"title": title, "url": url, "content": content, "published_date": ""}


@pytest.fixture
def supporting_results():
    return [
        result("Eiffel Tower location", "https://source-one.example/eiffel", "The Eiffel Tower is located in Paris, France."),
        result("Visiting the Eiffel Tower", "https://source-two.example/visit", "The Eiffel Tower is located in Paris, near the Champ de Mars."),
    ]


@pytest.fixture
def contradicting_results():
    return [
        result("Eiffel Tower location", "https://source-one.example/eiffel", "The Eiffel Tower is not located in Paris."),
        result("A guide to the Eiffel Tower", "https://source-two.example/guide", "The Eiffel Tower is not located in Paris, according to this fictional test snippet."),
    ]


def test_relevant_supporting_evidence(supporting_results):
    assessment = assess_evidence(CLAIM, supporting_results)
    assert assessment["verdict"] == "Supported"
    assert "two distinct retrieved URLs" in assessment["reasoning"]
    assert len(assessment["evidence_used"]) == 2


def test_relevant_contradicting_evidence(contradicting_results):
    assessment = assess_evidence(CLAIM, contradicting_results)
    assert assessment["verdict"] == "Contradicted"
    assert "opposite" in assessment["reasoning"]
    assert all(item.startswith("Explicit opposite wording:") for item in assessment["evidence_used"])


def test_unrelated_keyword_overlap_is_inconclusive():
    results = [
        result("Eiffel Tower history", "https://source-one.example/history", "The Eiffel Tower attracts millions of visitors."),
        result("Paris travel", "https://source-two.example/paris", "Paris is the capital of France and has many museums."),
    ]
    assessment = assess_evidence(CLAIM, results)
    assert assessment["verdict"] == "Inconclusive"
    assert "Related words alone are insufficient" in assessment["reasoning"]
    assert assessment["evidence_used"] == []


def test_conflicting_evidence_is_inconclusive(supporting_results, contradicting_results):
    assessment = assess_evidence(CLAIM, [supporting_results[0], contradicting_results[1]])
    assert assessment["verdict"] == "Inconclusive"
    assert "both the claim wording" in assessment["reasoning"]
    assert len(assessment["evidence_used"]) == 2


def test_no_results_is_inconclusive():
    assessment = assess_evidence(CLAIM, [])
    assert assessment["verdict"] == "Inconclusive"
    assert "No usable search sources" in assessment["reasoning"]
    assert assessment["evidence_used"] == []


@pytest.mark.parametrize("malformed_payload", [[], None, "unexpected response"])
def test_search_rejects_non_object_json_with_friendly_error(monkeypatch, malformed_payload):
    response = Mock(status_code=200, ok=True)
    response.json.return_value = malformed_payload
    monkeypatch.setattr("verifier.requests.post", Mock(return_value=response))

    with pytest.raises(VerificationError, match="unexpected response format"):
        search_evidence("A sufficiently clear test claim", "mock-key")


def test_search_timeout_has_a_friendly_error(monkeypatch):
    monkeypatch.setattr("verifier.requests.post", Mock(side_effect=requests.Timeout))
    with pytest.raises(VerificationError, match="took too long"):
        search_evidence("A sufficiently clear test claim", "mock-key")


def test_search_timing_reports_request_and_response_stages_without_inputs(monkeypatch):
    response = Mock(status_code=200, ok=True)
    response.json.return_value = {"results": [{
        "title": "A source", "url": "https://example.com/article",
        "content": "The Eiffel Tower is located in Paris.",
        "published_date": "2026-10-01", "publisher": "Example News",
    }]}
    monkeypatch.setattr("verifier.requests.post", Mock(return_value=response))
    claim = "The Eiffel Tower is located in Paris."
    results, timings = search_evidence_with_metrics(claim, "mock-key")
    assert results[0]["publisher"] == "Example News"
    assert results[0]["retrieved_at"].endswith("+00:00")
    assert {"search_request_ms", "response_processing_ms", "retrieval_total_ms"} <= set(timings)
    assert all(value >= 0 for value in timings.values())
    assert claim not in repr(timings) and "mock-key" not in repr(timings)


@pytest.mark.parametrize("status_code, expected", [
    (302, "unexpected redirect"),
    (429, "limit reached"),
    (503, "temporarily unavailable"),
])
def test_search_service_status_errors_are_friendly(monkeypatch, status_code, expected):
    response = Mock(status_code=status_code, ok=False)
    post = Mock(return_value=response)
    monkeypatch.setattr("verifier.requests.post", post)
    with pytest.raises(VerificationError, match=expected):
        search_evidence("A sufficiently clear test claim", "mock-key")
    assert post.call_args.kwargs["allow_redirects"] is False
