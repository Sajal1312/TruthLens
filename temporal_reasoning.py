"""Deterministic temporal diagnostics. Never classify stance or change a verdict.

Text date mentions are not automatically dates of the event being checked.
All warnings describe possible temporal issues requiring contextual review.
"""
import calendar
from datetime import date, datetime, timedelta
import re


CLASSIFICATIONS = ("historical", "current_status", "relative", "future",
                   "explicit", "timeless_candidate")
_MONTHS = {name.casefold(): index for index, name in enumerate(calendar.month_name) if name}
_MONTHS.update({name.casefold(): index for index, name in enumerate(calendar.month_abbr) if name})
_MONTHS["sept"] = 9
_MONTH = "(?:" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + ")"
_DATE_PATTERNS = [
    r"\b\d{4}-\d{1,2}-\d{1,2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?\b",
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+" + _MONTH + r"\s+\d{4}\b",
    r"\b" + _MONTH + r"\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",
    r"\b\d{1,2}/\d{1,2}/\d{4}\b",
    r"\b[12]\d{3}\s*[–-]\s*[12]\d{3}\b",
    r"\b\d{4}-\d{2}\b",
    r"\b" + _MONTH + r"\s+\d{4}\b",
    r"\b[12]\d{3}\b",
]
_RELATIVE = re.compile(
    r"\b(?:last|next|this)\s+(?:year|month|week|winter|spring|summer|autumn|fall)\b|"
    r"\b(?:today|yesterday|tomorrow|currently|recently|soon|now|previously)\b|"
    r"\b(?:at present|these days|a while ago|in the future)\b", re.I)
_CURRENT = re.compile(
    r"\b(?:currently|today|now|at present|these days|current status)\b|"
    r"\bcurrent\s+(?:president|prime minister|ceo|mayor|governor|director)\b|"
    r"\b(?:is|remains|serves as)\s+(?:(?:the|a|an|still)\s+)*"
    r"(?:president|prime minister|ceo|chief executive|mayor|governor|director|operational|available|active|closed|open|in office)\b", re.I)
_HISTORY = re.compile(r"\b(?:historically|historical|ancient|formerly|in the past|used to|once)\b", re.I)
_PAST_EVENT = re.compile(r"\b(?:launched|occurred|released|opened|born|died|founded|signed|was|were|held|became)\b", re.I)
_FUTURE = re.compile(
    r"\b(?:will|shall|predict\w*|forecast\w*)\b|"
    r"\b(?:plans?|planned|intends?|intended|expects?|expected|scheduled)\s+to\b|"
    r"\b(?:next year|next month|next week|tomorrow|soon|in the future)\b", re.I)
MISMATCH_CODES = {
    "publication_predates_claim_period", "different_time_period",
    "historical_evidence_for_current", "prediction_not_confirmed_outcome",
    "conflicting_event_metadata", "mixed_evidence_periods",
}
LIMITATIONS = (
    "Temporal analysis is a diagnostic reading aid and does not alter the verdict. "
    "Date mentions may concern another event; tense, quotation scope and event identity are not semantically resolved. "
    "A publication or update date does not establish an event date or confirm an outcome. "
    "Old evidence is not automatically false, and missing dates are not evidence of falsity. "
    "No explicit time cues means a timeless candidate, not proof of timelessness."
)


def parse_temporal_date(value):
    """Parse known formats into precision-aware intervals; retain the raw value."""
    raw = value.isoformat() if isinstance(value, (date, datetime)) else value
    result = {"raw": raw, "status": "missing", "precision": None,
              "start_date": None, "end_date": None}
    if value is None or value == "":
        return result
    if not isinstance(raw, str):
        return dict(result, status="invalid")
    text = raw.strip()
    if not text:
        return result
    try:
        if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", text):
            return dict(result, status="ambiguous")
        if re.fullmatch(r"\d{4}", text):
            year = int(text)
            start, end, precision = date(year, 1, 1), date(year, 12, 31), "year"
        elif re.fullmatch(r"[12]\d{3}\s*[–-]\s*[12]\d{3}", text):
            first, last = map(int, re.split(r"\s*[–-]\s*", text))
            start, end, precision = date(first, 1, 1), date(last, 12, 31), "year_range"
            if start > end:
                raise ValueError("Reversed range")
        elif re.fullmatch(r"\d{4}-\d{2}", text):
            year, month = map(int, text.split("-"))
            start = date(year, month, 1)
            end, precision = date(year, month, calendar.monthrange(year, month)[1]), "month"
        elif re.fullmatch(_MONTH + r"\s+\d{4}", text, re.I):
            month_name, year_text = text.split()
            year, month = int(year_text), _MONTHS[month_name.casefold()]
            start = date(year, month, 1)
            end, precision = date(year, month, calendar.monthrange(year, month)[1]), "month"
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            start = end = date.fromisoformat(text)
            precision = "day"
        elif re.match(r"^\d{4}-\d{2}-\d{2}T", text):
            start = end = datetime.fromisoformat(text.replace("Z", "+00:00")).date()
            precision = "day"
        else:
            cleaned = re.sub(r"(\d)(?:st|nd|rd|th)\b", r"\1", text, flags=re.I).replace(",", "")
            parts = cleaned.split()
            if len(parts) != 3:
                raise ValueError("Unknown date format")
            if parts[0].isdigit():
                day, month, year = int(parts[0]), _MONTHS[parts[1].casefold()], int(parts[2])
            else:
                month, day, year = _MONTHS[parts[0].casefold()], int(parts[1]), int(parts[2])
            start = end = date(year, month, day)
            precision = "day"
        return dict(result, status="resolved", precision=precision,
                    start_date=start.isoformat(), end_date=end.isoformat())
    except (ValueError, KeyError, OverflowError):
        return dict(result, status="invalid")


def _reference(value):
    parsed = parse_temporal_date(value)
    # A year/month cannot resolve what 'today' means.
    return date.fromisoformat(parsed["start_date"]) if parsed["status"] == "resolved" and parsed["precision"] == "day" else None


def _resolve_relative(expression, reference):
    result = {"status": "unresolved", "precision": None, "start_date": None, "end_date": None}
    key = " ".join(expression.casefold().split())
    vague = key in {"recently", "soon", "previously", "these days", "a while ago", "in the future"} or re.search(r"winter|spring|summer|autumn|fall", key)
    if vague or reference is None:
        return dict(result, note="Duration/season is ambiguous" if vague else "No precise reference date supplied")
    try:
        if key in {"today", "currently", "now", "at present", "yesterday", "tomorrow"}:
            offset = {"yesterday": -1, "tomorrow": 1}.get(key, 0)
            start = end = reference + timedelta(days=offset)
            precision = "day"
        else:
            modifier, unit = key.split()
            offset = {"last": -1, "this": 0, "next": 1}[modifier]
            if unit == "year":
                start, end = date(reference.year + offset, 1, 1), date(reference.year + offset, 12, 31)
            elif unit == "month":
                year, month = divmod(reference.year * 12 + reference.month - 1 + offset, 12)
                month += 1
                start, end = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
            else:
                start = reference - timedelta(days=reference.weekday()) + timedelta(weeks=offset)
                end = start + timedelta(days=6)
            precision = unit
        return {"status": "resolved", "precision": precision, "start_date": start.isoformat(),
                "end_date": end.isoformat(), "note": "Anchored to supplied reference; calendar periods, Monday–Sunday weeks"}
    except (ValueError, OverflowError):
        return dict(result, note="Reference date is outside the supported range")


def extract_temporal_expressions(text, reference_date=None):
    """Extract exact spans without guessing numeric date locale or vague duration."""
    text = text if isinstance(text, str) else ""
    reference = _reference(reference_date)
    expressions = []
    for pattern in _DATE_PATTERNS:
        for match in re.finditer(pattern, text, re.I):
            if any(match.start() < row["end"] and match.end() > row["start"] for row in expressions):
                continue
            # A preceding metadata label keeps its date separate from event mentions.
            prefix = re.split(r"[.;\n]", text[max(0, match.start() - 45):match.start()])[-1]
            role = ("update_mention" if re.search(r"\b(?:updated|modified)\b[^,;]*$", prefix, re.I) else
                    "publication_mention" if re.search(r"\b(?:published|publication)\b[^,;]*$", prefix, re.I) else
                    "date_mention")
            expressions.append(dict(parse_temporal_date(match.group()), text=match.group(),
                                    start=match.start(), end=match.end(), kind="explicit", role=role))
    for match in _RELATIVE.finditer(text):
        expressions.append(dict(_resolve_relative(match.group(), reference), text=match.group(),
                                start=match.start(), end=match.end(), kind="relative", role="date_mention"))
    return sorted(expressions, key=lambda row: row["start"])


def classify_temporal_context(text, reference_date=None):
    text = text if isinstance(text, str) else ""
    expressions = extract_temporal_expressions(text, reference_date)
    reference = _reference(reference_date)
    dated = [row for row in expressions if row["status"] == "resolved"]
    future = bool(_FUTURE.search(text)) or bool(reference and any(row["start_date"] > reference.isoformat() for row in dated))
    historical = bool(_HISTORY.search(text) or _PAST_EVENT.search(text))
    current = bool(_CURRENT.search(text))
    facets = [name for name, present in (
        ("future", future), ("current_status", current), ("historical", historical),
        ("relative", any(row["kind"] == "relative" for row in expressions)),
        ("explicit", any(row["kind"] == "explicit" for row in expressions))) if present]
    unresolved = [row["text"] for row in expressions if row["status"] != "resolved"]
    if current and reference is None and not unresolved:
        unresolved.append("Current status has no precise reference date")
    return {"classification": facets[0] if facets else "timeless_candidate", "facets": facets,
            "expressions": expressions, "reference_date": reference.isoformat() if reference else None,
            "unresolved": unresolved}


def _periods(context):
    return [(row["start_date"], row["end_date"]) for row in context["expressions"]
            if row["status"] == "resolved" and row["role"] == "date_mention"]


def _overlap(left, right):
    return left[0] <= right[1] and right[0] <= left[1]


def temporal_evidence_analysis(claim, results, reference_date=None):
    """Compare date intervals and contextual cues; never mutate assessment data.

    Relative source expressions are unresolved unless an explicit source
    `temporal_reference_date` is supplied. Retrieval/publication/update times do
    not automatically anchor a quoted 'today'.
    """
    claim_context = classify_temporal_context(claim, reference_date)
    claim_periods = _periods(claim_context)
    reference = _reference(reference_date)
    sources, all_warnings = [], []
    for index, source in enumerate(results):
        dates = {key: parse_temporal_date(value) for key, value in (
            ("publication_date", source.get("published_date")),
            ("updated_date", source.get("updated_date") or source.get("last_updated")),
            ("event_date", source.get("event_date")))}
        evidence_context = classify_temporal_context(source.get("content"), source.get("temporal_reference_date"))
        mentions = _periods(evidence_context)
        event = dates["event_date"]
        periods = [(event["start_date"], event["end_date"])] if event["status"] == "resolved" else mentions
        warnings = []

        def add(code, message, severity="warning"):
            warnings.append({"code": code, "severity": severity, "message": message})

        for key, parsed in dates.items():
            if parsed["status"] != "resolved":
                add(key + "_" + parsed["status"], key.replace("_", " ").capitalize() + ": " + parsed["status"] + "; no date inferred", "informational")
        if evidence_context["unresolved"]:
            add("unresolved_evidence_expressions", "Some source time expressions have no unambiguous anchor or format", "informational")
        if not periods:
            add("event_period_unknown", "No explicit event metadata or usable text date mention; event time remains unknown", "informational")
        if event["status"] == "resolved" and mentions and not any(_overlap(periods[0], item) for item in mentions):
            add("conflicting_event_metadata", "Supplied event date and text date mentions do not overlap; check event identity and metadata")
        if claim_periods and periods and not any(_overlap(left, right) for left in claim_periods for right in periods):
            add("different_time_period", "Claim period and evidence event/date-mention periods do not overlap; they may concern different events")
        publication = dates["publication_date"]
        if claim_periods and publication["status"] == "resolved" and publication["end_date"] < min(row[0] for row in claim_periods):
            add("publication_predates_claim_period", "Original publication predates the claim period; it may describe a plan, prediction or subsequently updated text")
        if "current_status" in claim_context["facets"]:
            old_mentions = bool(reference and periods and all(end < str(reference.year) + "-01-01" for _, end in periods))
            old_publication_only = bool(reference and not periods and publication["status"] == "resolved" and publication["end_date"] < str(reference.year) + "-01-01")
            historical_only = "historical" in evidence_context["facets"] and "current_status" not in evidence_context["facets"]
            if old_mentions or old_publication_only or historical_only:
                add("historical_evidence_for_current", "Historical wording or dates from an earlier calendar year may not establish current status; recency/identity needs review")
        if _FUTURE.search(source.get("content") or ""):
            add("prediction_not_confirmed_outcome", "Evidence uses prediction or intention language; it does not by itself confirm the eventual outcome")
        row = {"source_index": index, "title": source.get("title") or "Untitled source",
               "url": source.get("url") or "", "metadata": dates, "context": evidence_context,
               "comparison_periods": periods, "warnings": warnings}
        sources.append(row)
        all_warnings.extend(dict(item, source_index=index) for item in warnings)
    dated_sources = [source for source in sources if source["comparison_periods"]]
    if any(not any(_overlap(a, b) for a in left["comparison_periods"] for b in right["comparison_periods"])
           for i, left in enumerate(dated_sources) for right in dated_sources[i + 1:]):
        all_warnings.append({"code": "mixed_evidence_periods", "severity": "warning", "source_index": None,
                             "message": "Sources contain disjoint date periods; review whether they describe the same event before calling this a factual conflict"})
    return {"claim": claim_context, "sources": sources, "warnings": all_warnings,
            "diagnostic_only": True, "limitations": LIMITATIONS}
