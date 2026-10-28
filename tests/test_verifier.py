"""Offline tests for conservative claim assessment; no network calls are made."""
import pytest

from unittest.mock import Mock

from verifier import VerificationError, assess_evidence, search_evidence


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
