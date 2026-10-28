"""Transparent, non-authoritative source context for TruthLens evidence cards."""
import re
from urllib.parse import urlsplit


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
