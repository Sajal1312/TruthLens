"""Tavily search and conservative, explainable claim/evidence assessment."""
import os
import re
from typing import Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

TAVILY_URL = "https://api.tavily.com/search"
TIMEOUT_SECONDS = 20
MAX_RESULTS = 8
NEGATABLE_AUXILIARIES = {
    "am", "are", "can", "could", "did", "do", "does", "has", "have", "is", "may",
    "might", "must", "was", "were", "will", "would",
}


class VerificationError(Exception):
    """Friendly error that is safe to show to the user."""


def get_tavily_key() -> Optional[str]:
    """Read a key from Streamlit secrets when available, then environment."""
    try:
        import streamlit as st
        value = st.secrets.get("TAVILY_API_KEY")
        if value:
            return str(value).strip()
    except Exception:
        pass
    return os.environ.get("TAVILY_API_KEY", "").strip() or None


def search_evidence(claim: str, api_key: str) -> List[Dict[str, str]]:
    payload = {"api_key": api_key, "query": claim, "search_depth": "advanced", "max_results": MAX_RESULTS,
               "include_answer": False, "include_raw_content": False}
    try:
        response = requests.post(TAVILY_URL, json=payload, timeout=TIMEOUT_SECONDS)
    except requests.Timeout as exc:
        raise VerificationError("The web search took too long. Please try again in a moment.") from exc
    except requests.RequestException as exc:
        raise VerificationError("Could not connect to the web search service. Check your internet connection and try again.") from exc
    if response.status_code in (401, 403):
        raise VerificationError("Tavily rejected the API key. Check that it is copied correctly and still active.")
    if response.status_code == 429:
        raise VerificationError("Tavily search limit reached. Wait a little and try again.")
    if response.status_code >= 500:
        raise VerificationError("Tavily is temporarily unavailable. Please try again later.")
    if not response.ok:
        raise VerificationError("Tavily could not complete the search. Check your key and claim, then try again.")
    try:
        data = response.json()
    except ValueError as exc:
        raise VerificationError("The search service returned an unreadable response. Please try again.") from exc
    if not isinstance(data, dict):
        raise VerificationError("The search service returned an unexpected response format. Please try again.")
    # Retrieved page text is data only; never execute or follow instructions contained in it.
    results = data.get("results", [])
    if not isinstance(results, list):
        return []
    clean = []
    seen_results = set()
    for result in results:
        if not isinstance(result, dict):
            continue
        url = result.get("url")
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            continue
        # Keep evidence text byte-for-byte as returned. Display formatting belongs
        # in the UI; the assessor must see the same passage Tavily retrieved.
        content = result.get("content") if isinstance(result.get("content"), str) else ""
        title = result.get("title") if isinstance(result.get("title"), str) else ""
        published_date = result.get("published_date") if isinstance(result.get("published_date"), str) else ""
        dedupe_key = (_normalized_url(url), content)
        if dedupe_key in seen_results:
            continue
        seen_results.add(dedupe_key)
        clean.append({"title": title, "url": url, "content": content,
                      "published_date": published_date})
    return clean[:MAX_RESULTS]


def _words(text: str) -> List[str]:
    """Normalize punctuation while preserving every word and its order."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _contains_phrase(text: str, phrase: List[str]) -> bool:
    """Match a complete ordered phrase inside one sentence, never a bag of words."""
    if not phrase:
        return False
    # Keep sentence boundaries: do not build a match across unrelated sentences.
    for sentence in re.split(r"[.!?;\n]+", text.lower()):
        words = _words(sentence)
        width = len(phrase)
        if any(words[i:i + width] == phrase for i in range(len(words) - width + 1)):
            return True
    return False


def _opposite_phrase(claim_words: List[str]) -> Optional[List[str]]:
    """Recognize only a simple explicit ``auxiliary not`` polarity reversal."""
    if "not" in claim_words:
        # Turn "X is not Y" into "X is Y". Other negation structures are unsupported.
        return claim_words[:claim_words.index("not")] + claim_words[claim_words.index("not") + 1:]
    for index, word in enumerate(claim_words[:-1]):
        if word in NEGATABLE_AUXILIARIES:
            return claim_words[:index + 1] + ["not"] + claim_words[index + 1:]
    return None


def _source_key(item: Dict[str, str]) -> Optional[str]:
    """Normalize a URL for source identity without changing its display/open URL."""
    url = item.get("url", "")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (TypeError, ValueError):
        return None
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    if scheme not in ("http", "https") or not host:
        return None
    if port and not (scheme == "http" and port == 80) and not (scheme == "https" and port == 443):
        host = "{0}:{1}".format(host, port)
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
             if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}]
    return urlunsplit((scheme, host, parsed.path.rstrip("/") or "/", urlencode(sorted(query)), ""))


def _normalized_url(url: str) -> str:
    return _source_key({"url": url}) or url


def assess_evidence(claim: str, results: List[Dict[str, str]]) -> Dict[str, object]:
    """Assess only exact proposition wording and a narrow explicit-negation pattern.

    This does not establish entailment. It avoids turning related keywords into a
    verdict and leaves paraphrases, different values, and ambiguous text inconclusive.
    """
    if not results:
        return {"verdict": "Inconclusive", "method": "Conservative rule-based evidence matching",
                "reasoning": "No usable search sources were returned, so there is not enough evidence to assess this claim.",
                "evidence_used": [], "limitations": _limitations()}

    claim_words = _words(claim)
    if not claim_words:
        return {"verdict": "Inconclusive", "method": "Exact-proposition text matching",
                "reasoning": "The claim did not contain recognizable words, so it could not be compared with the results.",
                "evidence_used": [], "limitations": _limitations()}

    opposite_words = _opposite_phrase(claim_words)
    supporting_sources: Dict[str, str] = {}
    contradicting_sources: Dict[str, str] = {}
    seen_urls = set()
    for item in results:
        key = _source_key(item)
        if not key or key in seen_urls:
            continue
        seen_urls.add(key)
        title = item.get("title") or key
        content = item.get("content") or ""
        # Titles are not evidence: only retrieved snippet text can match a claim.
        exact_claim = _contains_phrase(content, claim_words)
        exact_opposite = bool(opposite_words and _contains_phrase(content, opposite_words))
        if exact_claim:
            supporting_sources[key] = title
        if exact_opposite:
            contradicting_sources[key] = title
    support_count = len(supporting_sources)
    contradiction_count = len(contradicting_sources)
    evidence_used = []
    evidence_used.extend("Exact claim wording: " + title for title in supporting_sources.values())
    evidence_used.extend("Explicit opposite wording: " + title for title in contradicting_sources.values())

    if support_count and contradiction_count:
        verdict = "Inconclusive"
        reasoning = ("The retrieved snippets contain both the claim wording and a narrowly recognized opposite wording. "
                     "The available text conflicts, so TruthLens cannot choose a direction.")
    elif support_count >= 2:
        verdict = "Supported"
        reasoning = ("At least two distinct retrieved URLs state the claim's complete wording in their snippets, "
                     "and no recognized opposite wording was found. This is textual corroboration only; it does not "
                     "show that the sources are reliable or that they independently establish the claim.")
    elif contradiction_count >= 2:
        verdict = "Contradicted"
        reasoning = ("At least two distinct retrieved URLs contain the narrowly recognized opposite of the claim, "
                     "and no exact claim wording was found. This is a limited text comparison, not proof that the claim is false.")
    elif support_count or contradiction_count:
        verdict = "Inconclusive"
        reasoning = ("Only one distinct retrieved URL matched the complete claim or its narrowly recognized opposite. "
                     "One result is insufficient for a directional assessment.")
    else:
        verdict = "Inconclusive"
        reasoning = ("The retrieved snippets did not state the complete claim or its narrowly recognized opposite. "
                     "Related words alone are insufficient, so there is not enough direct textual evidence to assess it.")
    return {"verdict": verdict, "method": "Exact-proposition text matching with a limited explicit-negation check",
            "reasoning": reasoning, "evidence_used": evidence_used, "limitations": _limitations()}


def _limitations() -> str:
    return ("This method does not understand meaning or establish that evidence entails a claim. It recognizes only "
            "complete wording and a limited 'not' reversal after a supported auxiliary; paraphrases, different dates or "
            "numbers, quoted/debunked statements, and nuanced negation can be missed or misread. It does not assess source "
            "credibility or independence, and snippets may omit context. Open the linked sources and verify them yourself.")
