"""Conservative, read-only quantity diagnostics, never stance or verdict rules.

Comparisons require a matching explicit wording frame; lexical overlap is not a
context matcher. Interval compatibility is not entailment or factual verification.
"""
from decimal import Decimal, InvalidOperation
import re

from nli_assessor import _CLAUSE_NEGATION, _QUANTIFIER_SCOPE_CUES
from temporal_reasoning import classify_temporal_context, extract_temporal_expressions, parse_temporal_date


APPROX_RELATIVE_TOLERANCE = Decimal("0.02")
APPROX_ABSOLUTE_FLOORS = {"number": Decimal("1"), "length": Decimal("0.01"),
                          "mass": Decimal("0.001"), "temperature": Decimal("0.5"),
                          "percentage": Decimal("0.5"), "percentage_point": Decimal("0.5")}
ARITHMETIC_EPSILON = Decimal("0.000000001")
STATUSES = ("compatible", "potential_mismatch", "comparison_unresolved")
_NUMBER = r"[+\-−]?(?:\d(?:[\d,]*\d)?(?:\.\d+)?|\.\d+)"
_UNIT = (r"(?:percentage[ -]points?|percent(?:age)?|per\s+cent|%|"
         r"degrees?\s+(?:Celsius|Fahrenheit)|°\s*[CF]|Celsius|Fahrenheit|"
         r"kilomet(?:er|re)s?|met(?:er|re)s?|kilograms?|grams?|km|kg|m|g)(?![a-zA-Z])")
_PREFIX_TOKEN = (r"(?:approximately|roughly|about|around|at\s+least|at\s+most|"
                 r"no\s+(?:more|fewer|less)\s+than|(?:greater|more|less|fewer)\s+than|"
                 r"exactly|over|under|>=|<=|≥|≤|>|<)")
_PREFIX = r"(?P<prefix>(?:" + _PREFIX_TOKEN + r"\s*){0,2})"
_FIRST = r"(?P<first>" + _NUMBER + r")\s*(?P<unit1>" + _UNIT + r")?"
_SECOND = r"(?P<second>" + _NUMBER + r")\s*(?P<unit2>" + _UNIT + r")?"
_PATTERNS = [
    re.compile(r"(?<![\w.])" + _PREFIX + r"between\s+" + _FIRST + r"\s+and\s+" + _SECOND, re.I),
    re.compile(r"(?<![\w.])" + _PREFIX + r"(?:from\s+)?" + _FIRST + r"\s*(?:to\b|[–—-])\s*" + _SECOND, re.I),
    re.compile(r"(?<![\w.])" + _PREFIX + _FIRST, re.I),
]
_COUNTS = re.compile(r"^\s*(?:samples?|participants?|people|persons?|students?|sensors?|items?|employees?|researchers?|respondents?|observations?|records?|units?)\b", re.I)
_APPROX = re.compile(r"\b(?:about|roughly|approximately|around)\b", re.I)
_COMPARATORS = {"at least": "ge", "no fewer than": "ge", "no less than": "ge", ">=": "ge", "≥": "ge",
                "at most": "le", "no more than": "le", "<=": "le", "≤": "le",
                "greater than": "gt", "more than": "gt", "over": "gt", ">": "gt",
                "less than": "lt", "fewer than": "lt", "under": "lt", "<": "lt", "exactly": "eq"}
_FRAME_STOP = set("a an the is are was were has have had of in at on to for by with and or its it this that value amount number measured measures measurement".split())
LIMITATIONS = (
    "Diagnostic only: interval overlap is compatibility, not proof or entailment. "
    "Matching wording frames are context candidates, not verified semantic event identity. "
    "Different values require the same entity, property, population, baseline and time. "
    "Paraphrases, pronouns, complex scope, unsupported units and missing context remain unresolved. "
    "Missing quantities never establish falsity. Approximation bands are a documented display policy, not scientific uncertainty. "
    "Production verdicts, NLI thresholds and experimental guard settings are unchanged."
)


def _decimal(text):
    text = text.replace("−", "-")
    if "," in text and not re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", text):
        raise ValueError("Ambiguous comma formatting")
    return Decimal(text.replace(",", ""))


def _canonical(value):
    return format(value.normalize(), "f") if value else "0"


def _unit(raw):
    value = re.sub(r"[\s-]+", "", raw.casefold())
    if value in {"%", "percent", "percentage"}:
        return "percentage", "%", Decimal(1), Decimal(0)
    if value.startswith("percentagepoint"):
        return "percentage_point", "percentage points", Decimal(1), Decimal(0)
    if value.startswith("kilomet") or value == "km":
        return "length", "m", Decimal(1000), Decimal(0)
    if value.startswith("met") or value == "m":
        return "length", "m", Decimal(1), Decimal(0)
    if value.startswith("kilogram") or value == "kg":
        return "mass", "kg", Decimal(1), Decimal(0)
    if value.startswith("gram") or value == "g":
        return "mass", "kg", Decimal("0.001"), Decimal(0)
    if value in {"°c", "celsius", "degreecelsius", "degreescelsius"}:
        return "temperature", "°C", Decimal(1), Decimal(0)
    if value in {"°f", "fahrenheit", "degreefahrenheit", "degreesfahrenheit"}:
        return "temperature", "°C", Decimal(5) / Decimal(9), -Decimal(32) * Decimal(5) / Decimal(9)
    return "number", "", Decimal(1), Decimal(0)


def detect_quantifiers(text):
    """Use the existing guard's exact cue inventory; enrich only display labels."""
    text = text if isinstance(text, str) else ""
    output = []
    for match in _QUANTIFIER_SCOPE_CUES.finditer(text):
        value = " ".join(match.group().casefold().split())
        negated = bool(re.search(r"\bnot\s+$", text[max(0, match.start() - 8):match.start()], re.I))
        kind = ("negated_universal" if negated and value in {"all", "every", "each"} else
                "negated_existential" if negated and value == "some" else
                "universal" if value in {"all", "every", "each"} else
                "existential" if value == "some" else
                "cardinal_comparator" if value in {"at least", "at most"} or value == "no" and re.match(r"\s+(?:more|fewer|less)\s+than", text[match.end():], re.I) else
                "negative_quantifier" if value in {"none", "no", "never"} else "scope_sensitive")
        output.append({"text": match.group(), "start": match.start(), "end": match.end(), "kind": kind, "negated": negated})
    return output


def _quantity_date(text, row):
    # Reuse temporal extraction but do not mistake a year-shaped count/measure
    # for a calendar year. Full calendar dates remain dates regardless of suffix.
    if row.get("precision") not in {"year", "year_range"}:
        return False
    suffix = text[row["end"]:]
    return bool(re.match(r"\s*" + _UNIT, suffix, re.I) or _COUNTS.match(suffix))


def extract_quantities(text, reference_date=None):
    """Extract digit-based quantities, intervals and dates with exact offsets."""
    text = text if isinstance(text, str) else ""
    dates = [row for row in extract_temporal_expressions(text, reference_date) if not _quantity_date(text, row)]
    rows = []
    for pattern in _PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.start(), match.end()
            # Optional suffix whitespace must not consume a sentence boundary.
            while end > start and text[end - 1].isspace():
                end -= 1
            if any(start < row["end"] and end > row["start"] for row in dates + rows):
                continue
            row = {"text": text[start:end], "start": start, "end": end, "status": "resolved",
                   "reason": "", "approximate": bool(_APPROX.search(match.group("prefix"))),
                   "comparator": "eq", "lower": None, "upper": None,
                   "lower_inclusive": True, "upper_inclusive": True, "normalized_unit": "", "dimension": "number"}
            try:
                first, second = _decimal(match.group("first")), None
                if match.groupdict().get("second"):
                    second = _decimal(match.group("second"))
                raw1, raw2 = match.group("unit1") or "", match.groupdict().get("unit2") or ""
                unit1 = _unit(raw1 or raw2)
                unit2 = _unit(raw2 or raw1)
                if unit1[0] != unit2[0]:
                    raise ValueError("Range endpoints use incompatible units")
                dimension, normalized, factor, offset = unit1
                lower = first * factor + offset
                upper = second * unit2[2] + unit2[3] if second is not None else lower
                if lower > upper:
                    raise ValueError("Reversed interval endpoints")
                prefix = _APPROX.sub("", match.group("prefix"))
                prefix = " ".join(prefix.casefold().split())
                comparator = _COMPARATORS.get(prefix, "eq") if prefix else "eq"
                if prefix and prefix not in _COMPARATORS:
                    raise ValueError("Unresolved comparator combination")
                if second is not None and comparator != "eq":
                    raise ValueError("Comparator applied to a range needs scope review")
                if row["approximate"] and comparator != "eq":
                    raise ValueError("Approximate inequality needs domain-specific interpretation")
                tolerance = Decimal(0)
                if row["approximate"]:
                    tolerance = max(max(abs(lower), abs(upper)) * APPROX_RELATIVE_TOLERANCE if dimension != "temperature" else Decimal(0), APPROX_ABSOLUTE_FLOORS[dimension])
                    lower -= tolerance
                    upper += tolerance
                row.update(dimension=dimension, normalized_unit=normalized, comparator="range" if second is not None else comparator,
                           original_unit=raw1 or raw2, tolerance=_canonical(tolerance))
                if comparator in {"ge", "gt"}:
                    upper = None
                    row["lower_inclusive"] = comparator == "ge"
                elif comparator in {"le", "lt"}:
                    lower = None
                    row["upper_inclusive"] = comparator == "le"
                row.update(lower=_canonical(lower) if lower is not None else None, upper=_canonical(upper) if upper is not None else None)
                if (raw1 or raw2) and re.match(r"\s*(?:/|\^|[²³]|per\b)", text[end:], re.I):
                    raise ValueError("Compound or powered units are unsupported")
                # Unknown suffixes may be units or magnitudes. Do not silently
                # treat pounds, million, etc. as dimensionless equivalents.
                following = re.match(r"\s*([a-zA-Z]+)", text[end:])
                if not (raw1 or raw2) and following and not _COUNTS.match(text[end:]) and following.group(1).casefold() not in {"in", "on", "at", "of", "and", "or", "for", "with", "per"}:
                    raise ValueError("Possible unsupported unit or count noun: " + following.group(1))
                if re.search(r"[$€£]\s*$", text[:start]):
                    raise ValueError("Currency normalization is unsupported")
            except (InvalidOperation, ValueError) as error:
                row.update(status="unresolved", reason=str(error))
            rows.append(row)
    rows.sort(key=lambda row: row["start"])
    # A local sentence is the unit of context. Other values stay in the frame,
    # preventing a changed baseline/population size from being silently erased.
    boundaries = [0] + [match.end() for match in re.finditer(r"[;!?\n]|(?<!\d)\.(?=\s|$)|(?<=\d)\.(?!\d)(?=\s|$)", text)] + [len(text)]
    for target in rows:
        lo = max(point for point in boundaries if point <= target["start"])
        hi = min(point for point in boundaries if point >= target["end"])
        parts, cursor = [], lo
        for other in rows:
            if not lo <= other["start"] < hi:
                continue
            parts.append(text[cursor:other["start"]])
            parts.append(" NUMTARGET " if other is target else " OTHER{0}:{1}:{2} ".format(other["dimension"], other["lower"], other["upper"]))
            cursor = other["end"]
        parts.append(text[cursor:hi])
        frame = " ".join(re.findall(r"[\w]+|[:+-]", "".join(parts).casefold()))
        local_dates = [row for row in dates if lo <= row["start"] < hi]
        time_resolved = all(row["status"] == "resolved" for row in local_dates)
        if local_dates and time_resolved:
            frame += " timeframes " + " ".join(row["start_date"] + ":" + row["end_date"] for row in local_dates)
        words = {word for word in re.findall(r"[a-z]+", frame) if not word.startswith("other")} - _FRAME_STOP - {"numtarget"}
        words -= {"timeframes"}
        target.update(context_frame=frame, context_explicit=time_resolved and len(words) >= 2 and not re.search(r"\b(?:it|its|this|that|they|their)\b", frame) and not re.search(r"<[^>]+>", text[lo:hi]),
                      negated_context=bool(_CLAUSE_NEGATION.search(frame)))
    return {"quantities": rows, "dates": dates, "quantifiers": detect_quantifiers(text)}


def compare_quantities(claim, evidence):
    """Compare normalized sets only after a strict local wording-frame match."""
    reason = None
    if claim["status"] != "resolved" or evidence["status"] != "resolved":
        reason = "Unsupported or ambiguous quantity representation"
    elif claim["negated_context"] or evidence["negated_context"]:
        reason = "Negation scope prevents treating these numbers as affirmative measurements"
    elif not claim["context_explicit"] or not evidence["context_explicit"]:
        reason = "Entity/property/population or temporal context is not explicit/resolved enough"
    elif claim["context_frame"] != evidence["context_frame"]:
        reason = "Entity, property, population, baseline, other values or time wording differs; no context identity established"
    elif claim["dimension"] != evidence["dimension"]:
        reason = "Incompatible measurement units/concepts; percentages and percentage points require a baseline, not direct equality"
    if reason:
        return {"status": "comparison_unresolved", "reason": reason}
    cl, cu, el, eu = [Decimal(value) if value is not None else None for value in (claim["lower"], claim["upper"], evidence["lower"], evidence["upper"])]
    if cl == cu and el == eu and cl is not None and el is not None and abs(cl - el) <= ARITHMETIC_EPSILON:
        overlap = True
    else:
        lower = max(value for value in (cl, el) if value is not None) if cl is not None or el is not None else None
        upper = min(value for value in (cu, eu) if value is not None) if cu is not None or eu is not None else None
        overlap = lower is None or upper is None or lower < upper
        if lower is not None and upper is not None and lower == upper:
            overlap = ((cl != lower or claim["lower_inclusive"]) and (el != lower or evidence["lower_inclusive"]) and
                       (cu != upper or claim["upper_inclusive"]) and (eu != upper or evidence["upper_inclusive"]))
    return {"status": "compatible" if overlap else "potential_mismatch",
            "reason": ("Intervals overlap under a matching explicit wording frame; compatibility does not establish the claim" if overlap else
                       "Normalized intervals are disjoint under a matching wording frame; review context before interpreting this as disagreement")}


def analyze_numerical_evidence(claim, results, reference_date=None):
    claim_data = extract_quantities(claim, reference_date)
    current = "current_status" in classify_temporal_context(claim, reference_date)["facets"]
    sources = []
    for index, source in enumerate(results):
        evidence = extract_quantities(source.get("content"), source.get("temporal_reference_date"))
        comparisons = []
        for cq_index, quantity in enumerate(claim_data["quantities"]):
            matched = [(eq_index, candidate) for eq_index, candidate in enumerate(evidence["quantities"]) if candidate["context_frame"] == quantity["context_frame"]]
            if len(matched) != 1:
                comparisons.append({"claim_quantity": cq_index, "evidence_quantity": None, "status": "comparison_unresolved",
                                    "reason": "No unique matching measurement context; missing quantities are not contradictions"})
                continue
            eq_index, candidate = matched[0]
            result = compare_quantities(quantity, candidate)
            if current:
                reference = parse_temporal_date(reference_date)
                anchor = parse_temporal_date(source.get("temporal_reference_date") or source.get("event_date"))
                if reference["status"] != "resolved" or anchor["status"] != "resolved" or reference["precision"] != "day" or anchor["precision"] != "day" or not (anchor["start_date"] <= reference["start_date"] <= anchor["end_date"]):
                    result = {"status": "comparison_unresolved", "reason": "Current-status measurement has no matching explicit source time anchor; publication/update dates are not event dates"}
            comparisons.append(dict(result, claim_quantity=cq_index, evidence_quantity=eq_index))
        warnings = []
        claim_kinds = {row["kind"] for row in claim_data["quantifiers"]}
        evidence_kinds = {row["kind"] for row in evidence["quantifiers"]}
        if "universal" in claim_kinds and "existential" in evidence_kinds:
            warnings.append("Some alone neither establishes nor disproves all; population, scope and possible counterexamples remain unresolved")
        if "negative_quantifier" in claim_kinds and "existential" in evidence_kinds:
            warnings.append("None/no versus some uses different scopes; review population identity and negation before drawing a direction")
        if (claim_kinds | evidence_kinds) - {"cardinal_comparator"}:
            warnings.append("Quantifier cues reused from the existing experimental guard; logical scope and population identity are not solved and the guard is not enabled")
        if not claim_data["quantities"] and claim_data["quantifiers"]:
            comparisons.append({"claim_quantity": None, "evidence_quantity": None, "status": "comparison_unresolved",
                                "reason": "Quantifier wording alone is not a numeric contradiction or proof; scope needs semantic review"})
        sources.append({"source_index": index, "title": source.get("title") or "Untitled source", "url": source.get("url") or "",
                        "extracted": evidence, "comparisons": comparisons, "quantifier_warnings": warnings})
    return {"diagnostic_only": True, "claim": claim_data, "sources": sources, "limitations": LIMITATIONS,
            "tolerance_policy": "Approximate values: ±max(2% of normalized magnitude, floor). Floors: 1 dimensionless/count unit, 0.01 m, 0.001 kg, 0.5 percentage points; temperature uses ±0.5°C only. Arithmetic roundoff epsilon 1e-9 base units; inequalities retain open/closed boundaries."}
