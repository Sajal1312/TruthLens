"""Diagnostic provenance relationships only; no votes or independence scores.

An explicit citation is an observed reference in supplied text, not a verified
reporting chain. Absence of detected dependence never establishes independence.
"""
from itertools import combinations
import re
from urllib.parse import unquote, urlsplit, urlunsplit

from evidence_quality import NEAR_DUPLICATE_JACCARD_THRESHOLD, passage_similarity, source_context


CATEGORIES = ("Exact duplicate", "Near duplicate", "Explicit shared-source dependency",
              "Possible dependency", "Independence not established")
MIN_NEAR_DUPLICATE_WORDS = 12  # Display diagnostic only; production dedup is unchanged.
_TRACKING = {"fbclid", "gclid"}
_CITATION_CUE = re.compile(r"\b(?:according to|reported by|sources?|cites?|cited|citing|report|study|survey|research|original|data|doi)\b", re.I)
_ORG = r"(?:[A-Z][A-Z0-9&-]{1,14}|[A-Z][a-z]+)(?:[ \t]+(?:[A-Z][\w&'-]*|of|the|and|for|on)){0,6}"
_ATTRIBUTIONS = [
    re.compile(r"(?i:\baccording to|\bas reported by|\bciting)\s+(?i:the\s+)?(?P<name>" + _ORG + ")"),
    re.compile(r"\b(?P<name>" + _ORG + r")\s+(?i:reported|reports|stated|said|announced|found)\b"),
]
_REPORTS = [
    re.compile(r'(?i:\b(?:report|study|survey)\s+(?:titled|called|named)\s+)["“](?P<title>[^"”\n]{3,120})["”]'),
    re.compile(r'["“](?P<title>[^"”\n]{3,120})["”]\s+(?i:report|study|survey)\b'),
]
_SCOPE_WORDS = re.compile(
    r"\b(?:not|no|never|none|without|cannot|can't|isn't|wasn't|doesn't|didn't|"
    r"all|some|every|most|only|increase\w*|decrease\w*|higher|lower|above|below|before|after|"
    r"at least|at most)\b", re.I)
_ALIASES = {"national aeronautics and space administration": "nasa",
            "associated press": "ap", "world health organization": "who"}
LIMITATIONS = (
    "No independence is established by this analysis. Matching URLs or passages are observations; "
    "text similarity, shared host/publisher metadata and institution mentions are limited signals. "
    "An explicit shared citation establishes a reference in the snippets, not endorsement, copying "
    "or exclusive reliance on that report. Citation pages and publisher ownership have not been checked. "
    "Different URLs or no detected relationship do not prove independent confirmation. "
    "These diagnostics do not change verdicts or production evidence counts."
)


def _text(value):
    return value if isinstance(value, str) else ""


def normalize_source_url(value):
    """Strict comparison key; preserve article identifiers, query order and routes.

    Unlike the older production comparison, non-root trailing slashes and query
    order remain significant. HTTP/HTTPS and www/non-www are not assumed equal.
    The original URL is never replaced in the retrieved evidence or source link.
    """
    if not isinstance(value, str) or not value or re.search(r"[\s\x00-\x20\x7f\\<>\"'{}]", value):
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname or parts.username is not None or parts.password is not None:
            return None
        host = parts.hostname.encode("idna").decode("ascii").lower()
        if any(char in host for char in '<>"\'{}%') or (":" not in host and any(not label or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label) for label in host.rstrip(".").split("."))):
            return None
        port = parts.port
        host = "[" + host + "]" if ":" in host else host
        if port is not None and not ((parts.scheme.lower() == "https" and port == 443) or (parts.scheme.lower() == "http" and port == 80)):
            host += ":" + str(port)
        # Keep semantic query keys/values byte-for-byte and in their original order.
        query = []
        for component in parts.query.split("&") if parts.query else []:
            key = unquote(component.split("=", 1)[0]).casefold()
            if key.startswith("utm_") or key in _TRACKING:
                continue
            query.append(component)
        if re.search(r"%(?![0-9a-fA-F]{2})", parts.path + parts.query + parts.fragment):
            return None
        # Only known document-anchor shapes are discarded. Unknown fragments may
        # identify application routes and are retained rather than merged.
        fragment = "" if re.fullmatch(r"(?:top|bottom|content|section(?:[-_]?\d+)?|paragraph(?:[-_]?\d+)?)", parts.fragment, re.I) else parts.fragment
        return urlunsplit((parts.scheme.lower(), host, parts.path or "/", "&".join(query), fragment))
    except (ValueError, UnicodeError):
        return None


def _trim_citation(value):
    value = value.rstrip(".,;")
    while value.endswith(")") and value.count(")") > value.count("("):
        value = value[:-1]
    return value


def extract_attributions(content):
    """Return literal attribution/citation spans, without following their URLs."""
    content = _text(content)
    findings = []
    for pattern in _ATTRIBUTIONS:
        for match in pattern.finditer(content):
            if re.search(r"\b(?:not|never)\s+$", content[max(0, match.start() - 12):match.start()], re.I):
                continue
            name = re.sub(r"\s+(?:of|the|and|for|on)$", "", match.group("name")).strip()
            key = _ALIASES.get(name.casefold(), name.casefold())
            findings.append({"kind": "organization_attribution", "key": key, "target": name,
                             "text": match.group(), "start": match.start(), "end": match.end()})
    for pattern in _REPORTS:
        for match in pattern.finditer(content):
            title = match.group("title").strip()
            findings.append({"kind": "report_title", "key": title.casefold(), "target": title,
                             "text": match.group(), "start": match.start(), "end": match.end()})
    for match in re.finditer(r'https?://[^\s<>"\']+', content, re.I):
        target = _trim_citation(match.group())
        key = normalize_source_url(target)
        if key:
            prefix = re.split(r"[.!?;\n]", content[max(0, match.start() - 180):match.start()])[-1]
            negative = re.search(r"\b(?:not|never)\s+(?:based on|citing|according to|from|using|relying on)\b", prefix, re.I)
            kind = "citation_url" if _CITATION_CUE.search(prefix) and not negative else "mentioned_url"
            findings.append({"kind": kind, "key": key, "target": target,
                             "text": target, "start": match.start(), "end": match.start() + len(target)})
    for match in re.finditer(r'\b10\.\d{4,9}/[^\s<>"\']+', content, re.I):
        target = _trim_citation(match.group())
        findings.append({"kind": "doi", "key": target.casefold(), "target": target,
                         "text": target, "start": match.start(), "end": match.start() + len(target)})
    return sorted(findings, key=lambda row: (row["start"], row["kind"]))


def _scope_signature(text):
    return (tuple(re.findall(r"\b\d+(?:[.,]\d+)*(?:%)?", text)),
            tuple(sorted(match.group().casefold() for match in _SCOPE_WORDS.finditer(text))))


def _groups(count, relationships):
    """Overlapping complete-link groups: every member pair has a direct strong link.

    Seed each eligible pair and extend only when all pairwise links exist.
    Weak possible-dependency links are never used, and uncovered nodes are
    singletons. Overlapping groups must not be summed as independent evidence.
    """
    edges = {(row["left"], row["right"]): row for row in relationships if row["group_eligible"]}
    candidates = set()
    for left, right in edges:
        members = {left, right}
        for node in range(count):
            if node not in members and all(tuple(sorted((node, other))) in edges for other in members):
                members.add(node)
        candidates.add(frozenset(members))
    maximal = [group for group in candidates if not any(group < other for other in candidates)]
    covered = set().union(*maximal) if maximal else set()
    maximal.extend(frozenset([node]) for node in range(count) if node not in covered)
    output = []
    for index, members in enumerate(sorted(maximal, key=lambda group: tuple(sorted(group)))):
        links = [edges[pair] for pair in combinations(sorted(members), 2)]
        output.append({"id": "G" + str(index + 1), "members": sorted(members),
                       "relationship_ids": [link["id"] for link in links],
                       "reason": ("Every member pair has a direct observed reference/document/text match or qualifying inferred wording match" if links else
                                  "No qualifying grouping link was detected; independence remains unknown"),
                       "basis": [reason for link in links for reason in link["signals"]]})
    return output


def analyze_evidence_independence(results):
    """Build relationships and groups without reading an assessment or changing it."""
    sources = []
    for index, item in enumerate(results):
        item = item if isinstance(item, dict) else {}
        text = _text(item.get("content"))
        key = normalize_source_url(item.get("url"))
        sources.append({"index": index, "title": _text(item.get("title")) or "Untitled source",
                        "url": _text(item.get("url")), "normalized_url": key,
                        "domain": source_context(key or "")["domain"],
                        "publisher": _text(item.get("publisher")).strip(), "content": text,
                        "attributions": extract_attributions(text),
                        "warnings": ([] if key else ["Source URL is missing or malformed; identity was not inferred"]) +
                                    ([] if text.strip() else ["No passage text supplied"]),
                        "independence": "Independence not established"})
    relationships = []
    for left, right in combinations(sources, 2):
        signals = []

        def add(kind, code, message):
            signals.append({"kind": kind, "code": code, "message": message})

        same_url = bool(left["normalized_url"] and left["normalized_url"] == right["normalized_url"])
        if same_url:
            add("observed", "same_url", "Same normalized document URL; passages can still differ")
        ltext, rtext = (re.sub(r"\s+", " ", row["content"]).strip() for row in (left, right))
        exact = bool(ltext and ltext == rtext)
        similarity = passage_similarity(ltext, rtext)
        changed_scope = _scope_signature(ltext) != _scope_signature(rtext)
        enough_words = min(len(ltext.split()), len(rtext.split())) >= MIN_NEAR_DUPLICATE_WORDS
        near = not exact and similarity >= NEAR_DUPLICATE_JACCARD_THRESHOLD and enough_words and not changed_scope
        if exact:
            add("observed", "exact_text", "Passage text matches after whitespace normalization; copying or authorship is not established")
        elif similarity >= NEAR_DUPLICATE_JACCARD_THRESHOLD:
            add("heuristic", "near_text" if near else "similar_text_caution",
                "3-word-shingle Jaccard {0:.3f}; {1}".format(similarity,
                    "near-duplicate wording, not proof of copying" if near else
                    "short text or changed numbers/negation/scope prevents near-duplicate grouping"))
        identifiers = []
        for kind in ("citation_url", "doi"):
            lkeys = {row["key"] for row in left["attributions"] if row["kind"] == kind}
            rkeys = {row["key"] for row in right["attributions"] if row["kind"] == kind}
            identifiers.extend((kind, key) for key in sorted(lkeys & rkeys))
            if kind == "citation_url":
                for key in sorted(({left["normalized_url"]} & rkeys) | ({right["normalized_url"]} & lkeys)):
                    if key:
                        identifiers.append(("direct_citation", key))
        explicit = bool(identifiers)
        for kind, key in identifiers:
            add("observed", kind, "Explicit reference in supplied snippet(s): " + key + "; reporting dependence beyond that reference is unverified")
        for kind in ("organization_attribution", "report_title", "mentioned_url"):
            lkeys = {row["key"] for row in left["attributions"] if row["kind"] == kind}
            rkeys = {row["key"] for row in right["attributions"] if row["kind"] == kind}
            for key in sorted(lkeys & rkeys):
                add("heuristic", "shared_" + kind, "Both snippets reference " + key + "; a shared institution/title or uncategorized URL does not identify one originating report or prove copying")
        if left["domain"] != "Unknown domain" and left["domain"] == right["domain"]:
            add("observed", "same_host", "Same exact host; not proof of one publisher, article or reporting chain")
        if left["publisher"] and left["publisher"].casefold() == right["publisher"].casefold():
            add("observed", "same_declared_publisher", "Matching supplied publisher labels; identity/ownership is not independently verified")
        category = ("Exact duplicate" if exact else "Explicit shared-source dependency" if explicit else
                    "Near duplicate" if near else "Possible dependency" if signals else "Independence not established")
        relationships.append({"id": "R{0}-{1}".format(left["index"] + 1, right["index"] + 1),
                              "left": left["index"], "right": right["index"], "category": category,
                              "exact_duplicate": exact, "near_duplicate": near, "explicit_dependency": explicit,
                              "same_document": same_url, "text_similarity": similarity,
                              "scope_difference": changed_scope, "signals": signals,
                              "group_eligible": bool(exact or near or explicit or same_url)})
    normalized_texts = [re.sub(r"\s+", " ", row["content"]).strip() for row in sources if row["content"].strip()]
    return {"diagnostic_only": True, "sources": sources, "relationships": relationships,
            "groups": _groups(len(sources), relationships),
            "counts": {"retrieved_passages": len(sources), "nonempty_passages": len(normalized_texts),
                       "distinct_source_urls": len({row["normalized_url"] for row in sources if row["normalized_url"]}),
                       "invalid_or_missing_urls": sum(row["normalized_url"] is None for row in sources),
                       "exact_duplicate_pairs": sum(row["exact_duplicate"] for row in relationships),
                       "repeated_passage_entries": len(normalized_texts) - len(set(normalized_texts)),
                       "near_duplicate_pairs": sum(row["near_duplicate"] for row in relationships),
                       "explicit_dependency_pairs": sum(row["explicit_dependency"] for row in relationships),
                       "possible_dependency_pairs": sum(row["category"] == "Possible dependency" for row in relationships)},
            "limitations": LIMITATIONS}
