"""Transparent, non-authoritative source context for TruthLens evidence cards."""
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_SCIENTIFIC_HOSTS = {
    "nasa.gov", "noaa.gov", "nih.gov", "cdc.gov", "usgs.gov", "esa.int",
    "who.int", "nationalacademies.org", "nature.com", "science.org",
}
_NEWS_HOSTS = {
    "apnews.com", "reuters.com", "bbc.com", "bbc.co.uk", "npr.org",
    "theguardian.com", "nytimes.com", "washingtonpost.com", "afp.com",
}
_REFERENCE_HOSTS = {"britannica.com", "wikipedia.org", "merriam-webster.com", "britannica.co.uk"}
_FORUM_HOSTS = {"reddit.com", "quora.com", "stackoverflow.com", "stackexchange.com", "news.ycombinator.com"}
_BLOG_HOSTS = {"medium.com", "substack.com", "blogspot.com", "wordpress.com", "tumblr.com"}
_TIME_SENSITIVE_CLAIM = re.compile(r"\b(current(?:ly)?|today|latest|recent(?:ly)?|now|this year|last week|next week|yesterday|tomorrow)\b", re.I)
NEAR_DUPLICATE_JACCARD_THRESHOLD = 0.80


def _host_matches(host, domains):
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def source_context(url):
    """Return a source category and its basis, never a credibility score."""
    try:
        parts = urlsplit(url if isinstance(url, str) else "")
        host = (parts.hostname or "").lower().rstrip(".")
    except ValueError:
        host = ""
    if not host:
        return {"domain": "Unknown domain", "category": "Unknown", "basis": "URL unavailable or malformed",
                "note": "Source credibility is not established."}

    if _host_matches(host, _SCIENTIFIC_HOSTS):
        category, basis = "Scientific institution / publication", "recognized host name"
    elif _host_matches(host, _NEWS_HOSTS):
        category, basis = "Established news organization", "recognized host name"
    elif _host_matches(host, _REFERENCE_HOSTS):
        category, basis = "General reference", "recognized host name"
    elif _host_matches(host, _FORUM_HOSTS):
        category, basis = "Forum / community", "recognized platform host"
    elif _host_matches(host, _BLOG_HOSTS):
        category, basis = "Personal or hosted blog", "recognized publishing platform"
    elif host.endswith(".gov") or ".gov." in host:
        category, basis = "Government domain (unverified)", "domain suffix only"
    elif host.endswith(".edu") or ".edu." in host or host.endswith(".ac.uk"):
        category, basis = "Academic domain (unverified)", "domain suffix only"
    else:
        category, basis = "Unknown", "no recognized source category"

    return {"domain": host, "category": category, "basis": basis,
            "note": "Category is contextual metadata, not verification of accuracy, expertise, or independence."}


def source_category_order(category):
    """Stable presentation tie-break only; category never changes evidence votes."""
    order = {
        "Scientific institution / publication": 0,
        "Academic domain (unverified)": 1,
        "Government domain (unverified)": 2,
        "Established news organization": 3,
        "General reference": 4,
        "Personal or hosted blog": 5,
        "Forum / community": 6,
        "Unknown": 7,
    }
    return order.get(category, 7)


def publication_date_signal(claim, published_date):
    """Describe date availability without treating it as evidence of claim truth."""
    has_date = isinstance(published_date, str) and bool(published_date.strip())
    time_sensitive = bool(_TIME_SENSITIVE_CLAIM.search(claim if isinstance(claim, str) else ""))
    if not has_date:
        return "Publication date unavailable" if time_sensitive else "No publication date returned"
    if time_sensitive:
        return "Publication date available for time-sensitive claim"
    return "Publication date available; claim not explicitly time-sensitive"


def passage_shingles(text):
    """Return normalized 3-word shingles for diagnostic duplicate comparison."""
    words = re.findall(r"[a-z0-9]+", text.casefold()) if isinstance(text, str) else []
    if not words:
        return set()
    if len(words) < 3:
        return {tuple(words)}
    return {tuple(words[index:index + 3]) for index in range(len(words) - 2)}


def passage_similarity(left, right):
    """Jaccard similarity of passage shingles; diagnostic, not a verdict score."""
    left_shingles, right_shingles = passage_shingles(left), passage_shingles(right)
    if not left_shingles or not right_shingles:
        return 0.0
    return len(left_shingles & right_shingles) / len(left_shingles | right_shingles)


def _provenance_url_key(url):
    try:
        parts = urlsplit(url if isinstance(url, str) else "")
        host = (parts.hostname or "").lower().rstrip(".")
        if parts.scheme.lower() not in ("http", "https") or not host:
            return ""
        port = parts.port
    except ValueError:
        return ""
    netloc = host
    if port and not (parts.scheme.lower() == "https" and port == 443) and not (parts.scheme.lower() == "http" and port == 80):
        netloc += ":{0}".format(port)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}]
    return urlunsplit((parts.scheme.lower(), netloc, parts.path.rstrip("/") or "/",
                       urlencode(sorted(query)), ""))


def provenance_diagnostics(results):
    """Describe observable source relationships without asserting independence.

    Publisher identity and shared originating reports are left unknown unless
    explicitly supplied. Same-host and text-similarity notes are metadata only.
    """
    records = []
    for index, item in enumerate(results):
        url = item.get("url", "") if isinstance(item, dict) else ""
        context = source_context(url)
        publisher = item.get("publisher") if isinstance(item, dict) else None
        publisher = publisher.strip() if isinstance(publisher, str) and publisher.strip() else "Not provided"
        records.append({
            "index": index,
            "domain": context["domain"],
            "publisher": publisher,
            "publisher_basis": "Tavily metadata" if publisher != "Not provided" else "No publisher identity supplied; domain is not treated as publisher identity",
            "url": url,
            "published_date": item.get("published_date", "") if isinstance(item, dict) else "",
            "retrieved_at": item.get("retrieved_at", "") if isinstance(item, dict) else "",
            "relationships": [],
            "independence": "Unknown; URL and domain differences do not establish independent reporting",
            "origin_relationship": "Not available from the retrieved search metadata",
        })

    for left_index in range(len(results)):
        left = results[left_index] if isinstance(results[left_index], dict) else {}
        for right_index in range(left_index + 1, len(results)):
            right = results[right_index] if isinstance(results[right_index], dict) else {}
            left_key, right_key = _provenance_url_key(left.get("url")), _provenance_url_key(right.get("url"))
            left_host, right_host = source_context(left.get("url", ""))["domain"], source_context(right.get("url", ""))["domain"]
            observations = []
            if left_key and left_key == right_key:
                observations.append({
                    "type": "same_normalized_url",
                    "kind": "observed",
                    "label": "Same normalized URL",
                    "basis": "Parsed HTTP URL matches after tracking parameters and fragments are removed",
                })
            if left_host != "Unknown domain" and left_host == right_host:
                observations.append({
                    "type": "same_exact_host",
                    "kind": "observed",
                    "label": "Same exact host; publisher identity is not verified",
                    "basis": "The host names parsed from both source URLs are identical",
                })
            left_content = left.get("content", "") if isinstance(left.get("content"), str) else ""
            right_content = right.get("content", "") if isinstance(right.get("content"), str) else ""
            if left_content.strip() and left_content.strip().casefold() == right_content.strip().casefold():
                observations.append({
                    "type": "identical_snippet",
                    "kind": "observed",
                    "label": "Passage text is identical",
                    "basis": "Retrieved snippet text matches after trimming outer whitespace and case-folding",
                })
            else:
                similarity = passage_similarity(left_content, right_content)
                if similarity >= NEAR_DUPLICATE_JACCARD_THRESHOLD:
                    observations.append({
                        "type": "near_duplicate_snippet",
                        "kind": "heuristic_inference",
                        "label": "Passages are near-duplicates (3-word-shingle Jaccard {0:.2f})".format(similarity),
                        "basis": "Token-shingle similarity is at least {0:.2f}; this does not establish shared authorship or syndication".format(NEAR_DUPLICATE_JACCARD_THRESHOLD),
                    })
            if observations:
                relationship = {
                    "other_index": right_index,
                    "observations": observations,
                    # Keep the former text field for compatibility with existing callers.
                    "notes": [observation["label"] for observation in observations],
                }
                records[left_index]["relationships"].append(relationship)
                records[right_index]["relationships"].append({
                    "other_index": left_index,
                    "observations": observations,
                    "notes": [observation["label"] for observation in observations],
                })
    return records
