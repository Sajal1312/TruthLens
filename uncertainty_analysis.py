"""Read-only sufficiency summary of existing traces and diagnostic views.

No search, model, date/quantity extraction, similarity, vote counting or verdict
aggregation is performed here. Findings never assert a new cause of a verdict.
"""
from nli_assessor import MIN_DIRECTIONAL_SOURCES


CATEGORIES = ("Insufficient evidence", "Conflicting evidence", "Uncertain provenance",
              "Temporal uncertainty", "Numerical ambiguity", "Model assessment limitation",
              "No identified diagnostic issue")
BASES = ("observed", "rule_based", "heuristic", "unknown")
LIMITATIONS = (
    "This is a summary of supplied decision traces and diagnostic findings, not a new verification result. "
    "Only the verbatim recorded explanation is attributed to the existing decision trace. Additional warnings "
    "are not asserted causes of the verdict. Trace record counts are not independent votes or calibrated truth probabilities. "
    "Missing warnings do not establish evidence reliability, sufficiency or independence."
)
_MINIMUM_PHRASES = ("Only one distinct URL", "Only one distinct retrieved URL",
                    "lacks two distinct relevant", "One result is insufficient")


def _string(value):
    return value if isinstance(value, str) else ""


def analyze_uncertainty(assessment, results, *, independence=None, temporal=None, numerical=None):
    """Consume already-computed views. Missing data remains unknown, never zero."""
    verdict = _string(assessment.get("verdict")) or "Not recorded"
    explanation = _string(assessment.get("reasoning"))
    findings = []

    def add(code, category, basis, origin, message, *, details=None, suggestion=None):
        findings.append({"code": code, "category": category, "basis": basis, "origin": origin,
                         "verdict_relation": "additional_diagnostic_only", "message": message,
                         "details": details or [], "suggestion": suggestion})

    rows = assessment.get("per_source")
    rows = rows if isinstance(rows, list) else []
    records, relevance, missing_sources = [], [], set()
    for index, source in enumerate(results):
        row = rows[index] if index < len(rows) and isinstance(rows[index], dict) else None
        if row is None or row.get("url") != source.get("url", ""):
            missing_sources.add(index)
            continue
        relevance.append(_string(row.get("relevance")))
        parts = row.get("part_assessments") or [row]
        if not isinstance(parts, list):
            missing_sources.add(index)
            continue
        for part in parts:
            if not isinstance(part, dict):
                missing_sources.add(index)
                continue
            flag = part.get("contributed") if type(part.get("contributed")) is bool else None
            raw = {part["model_label"]} if isinstance(part.get("model_label"), str) and part["model_label"] else set()
            raw.update(passage["model_label"] for passage in part.get("passages") or []
                       if isinstance(passage, dict) and isinstance(passage.get("model_label"), str) and passage["model_label"])
            records.append({"source_index": index, "component": _string(part.get("claim_part")),
                            "label": _string(part.get("label")), "contributed": flag,
                            "raw_labels": sorted(raw), "status": _string(part.get("status")) or _string(row.get("status"))})
    support = [row for row in records if row["contributed"] is True and row["label"] == "SUPPORTS"]
    contradict = [row for row in records if row["contributed"] is True and row["label"] == "CONTRADICTS"]
    conflicting = [row for row in records if row["label"] == "CONFLICTING"]
    unknown_flags = [row for row in records if row["contributed"] is None]
    by_component = {}
    for row in support + contradict:
        by_component.setdefault(row["component"], set()).add(row["label"])
    component_conflict = any(len(labels) > 1 for labels in by_component.values())
    if conflicting:
        agreement = "conflict_recorded"
    elif component_conflict:
        agreement = "mixed_within_component"
    elif support and contradict:
        agreement = "mixed_across_components"
    elif missing_sources or unknown_flags:
        agreement = "direction_unknown"
    elif support:
        agreement = "supporting_only_as_recorded"
    elif contradict:
        agreement = "contradicting_only_as_recorded"
    else:
        agreement = "no_directional_evidence_as_recorded"

    trace_complete = not missing_sources and not unknown_flags and len(rows) == len(results)
    directly_relevant = sum(value == "Directly relevant candidate" for value in relevance)
    if not results:
        availability = "no_retrieved_evidence"
        add("no_evidence", CATEGORIES[0], "observed", "retrieval", "No retrieved evidence is available; absence does not establish falsity.",
            suggestion="Retrieve traceable passages that directly address the complete claim.")
    elif trace_complete and relevance and all(value in {"Unrelated", "Weakly related"} for value in relevance):
        availability = "no_directly_relevant_evidence_as_recorded"
        add("no_relevant_evidence", CATEGORIES[0], "observed", "decision_trace", "All available source relevance labels are unrelated or weakly related; this is the assessor's recorded filtering result.",
            suggestion="Find evidence addressing the proposition, not just the same entities or keywords.")
    elif verdict == "Inconclusive" and directly_relevant:
        availability = "relevant_evidence_with_unresolved_outcome"
    elif not trace_complete or relevance and all(value.startswith("Not semantically") or not value for value in relevance):
        availability = "semantic_relevance_unknown"
    else:
        availability = "evidence_available"
    if verdict == "Inconclusive" and any(phrase.casefold() in explanation.casefold() for phrase in _MINIMUM_PHRASES):
        add("minimum_requirement_reported", CATEGORIES[0], "observed", "decision_trace", "The recorded decision explanation reports a minimum-evidence shortfall. No new threshold check was performed.",
            details=[explanation], suggestion="Obtain additional qualifying directional passages for every unresolved component, checking provenance rather than adding URL copies.")
    elif verdict == "Inconclusive" and assessment.get("part_outcomes") and any(part.get("verdict") == "Inconclusive" for part in assessment["part_outcomes"]):
        add("unresolved_component", CATEGORIES[0], "observed", "decision_trace", "At least one component is recorded as Inconclusive; its precise shortfall is not independently reconstructed.",
            suggestion="Inspect the unresolved components and find evidence for each independently checkable part.")
    elif results and verdict == "Inconclusive" and trace_complete and not support and not contradict and not conflicting:
        add("no_counted_direction", CATEGORIES[0], "observed", "decision_trace", "No directional contribution is recorded in the available trace. This does not establish irrelevance or falsity.",
            suggestion="Find direct evidence for the whole claim and retain the assessor's relevance and inclusion trace.")
    if conflicting or support and contradict:
        add("directional_conflict", CATEGORIES[1], "observed", "decision_trace",
            "The trace records conflicting passages or mixed component directions. Different component directions are not necessarily contradictions about one proposition; excluded conflicts are not reintroduced as votes.",
            details=[dict(row) for row in conflicting + support + contradict],
            suggestion="Inspect each component, scope and source context; resolve the disagreement with original evidence rather than a majority of URLs.")
    if verdict in {"Supported", "Contradicted"} and (component_conflict or any(row["contributed"] is True for row in conflicting)):
        add("trace_tension", CATEGORIES[5], "rule_based", "decision_trace", "A decisive verdict coexists with recorded accepted conflict for a component. Inspect the supplied trace; the verdict has not been reinterpreted.",
            suggestion="Check source/component alignment and the original aggregation record.")
    raw_differences = [row for row in records if row["raw_labels"] and any(label != row["label"] for label in row["raw_labels"])]
    if raw_differences:
        add("raw_effective_difference", CATEGORIES[5], "observed", "decision_trace", "Some raw NLI predictions differ from effective assessments. This does not itself establish a model error or the cause of the final verdict.",
            details=raw_differences, suggestion="Review the effective label, score/margin and exclusion reason alongside each raw prediction.")
    exclusions = [row for row in records if row["status"].startswith(("Excluded", "Not counted", "Repeated passage", "Snippet discusses a different year"))]
    if exclusions:
        add("recorded_exclusions", CATEGORIES[5], "observed", "decision_trace", "Existing safeguards explicitly excluded or did not count some evidence. These recorded passage decisions are not new filtering rules.",
            details=exclusions, suggestion="Read the recorded exclusions and seek evidence with compatible context, dates, scope and source identity.")
    if results and (not trace_complete or any(not row["label"] or not row["status"] for row in records)) or not explanation:
        add("decision_trace_unavailable", CATEGORIES[5], "unknown", "decision_trace", "Some relevance/contribution/status or aggregate-explanation information is unavailable. Missing trace data is not assumed to mean evidence was rejected.",
            details=[{"source_indices": sorted(missing_sources), "unknown_contribution_records": len(unknown_flags)}],
            suggestion="Preserve the original assessment trace before interpreting evidence counts or exclusion causes.")
    if assessment.get("fallback_used"):
        add("nli_fallback", CATEGORIES[5], "observed", "decision_trace", "The assessment explicitly reports rule-based fallback; semantic model labels and some source-level contribution details may be unavailable.",
            suggestion="Distinguish fallback wording matches from semantic assessment; inspect model availability separately.")

    required_views = {"independence": (independence, {"counts": dict, "sources": list, "relationships": list}),
                      "temporal": (temporal, {"claim": dict, "sources": list, "warnings": list}),
                      "numerical": (numerical, {"claim": dict, "sources": list})}
    missing_views = [name for name, (view, required) in required_views.items()
                     if not isinstance(view, dict) or any(not isinstance(view.get(key), kind) for key, kind in required.items())]
    for name, (view, _required) in required_views.items():
        if name in missing_views:
            continue
        malformed = any(not isinstance(source, dict) for source in view["sources"])
        if name == "temporal":
            malformed = malformed or any(not isinstance(warning, dict) for warning in view["warnings"])
        if name == "numerical":
            malformed = malformed or any(not isinstance(source.get("comparisons", []), list) or any(not isinstance(item, dict) for item in source.get("comparisons", [])) for source in view["sources"] if isinstance(source, dict))
        if malformed:
            missing_views.append(name)
    misaligned_views = [name for name, (view, _required) in required_views.items()
                        if isinstance(view, dict) and isinstance(view.get("sources"), list) and len(view["sources"]) != len(results)]
    if missing_views and results:
        add("diagnostic_views_unavailable", CATEGORIES[5], "unknown", "diagnostic_views", "Already-computed diagnostic views are unavailable; they were not rerun or assumed clear.",
            details=missing_views, suggestion="Generate the original diagnostic views through the explanation pipeline.")
    if misaligned_views:
        add("diagnostic_views_misaligned", CATEGORIES[5], "unknown", "diagnostic_views", "Some diagnostic source lists do not align with this run's retrieved entries; no missing source decisions were invented.",
            details=misaligned_views, suggestion="Keep assessment and diagnostic outputs from the same verification run.")
    independence_counts = independence.get("counts") if isinstance(independence, dict) else None
    independence_counts = independence_counts if isinstance(independence_counts, dict) else {}
    declared_count = independence_counts.get("retrieved_passages")
    if "independence" in missing_views or "independence" in misaligned_views:
        independence_counts = {}
    for key, code, basis, message in (
        ("exact_duplicate_pairs", "exact_duplicates", "observed", "Matching passage text was reported; repeated publications are not independent confirmations."),
        ("near_duplicate_pairs", "near_duplicates", "heuristic", "Near-duplicate wording was reported; authorship and copying remain unverified."),
        ("explicit_dependency_pairs", "shared_reference", "observed", "Explicit shared references were reported in snippets; endorsement and exclusive reliance are not established."),
        ("possible_dependency_pairs", "possible_dependency", "heuristic", "Possible shared-source/metadata relationships were reported; these are suspicions, not confirmed copying.")):
        value = independence_counts.get(key)
        if type(value) is int and value > 0:
            add(code, CATEGORIES[2], basis, "independence", message, details=[{"pair_count": value}],
                suggestion="Inspect the cited originating reports and reporting chains; different domains alone do not establish independence.")
    if results:
        add("independence_not_established", CATEGORIES[2], "unknown", "independence", "The available diagnostic engine does not establish editorial or observational independence, even when no dependency was detected.",
            suggestion="Document distinct original observations or reporting chains with source-level provenance evidence.")
    if declared_count is not None and (type(declared_count) is not int or declared_count != len(results)):
        add("diagnostic_count_mismatch", CATEGORIES[5], "unknown", "diagnostic_views", "The supplied provenance passage count differs from the retrieved input. No counts were silently repaired.",
            suggestion="Check that all diagnostic views belong to the same verification run.")

    temporal_missing = []
    temporal_warnings = []
    if isinstance(temporal, dict) and "temporal" not in missing_views and "temporal" not in misaligned_views:
        temporal_claim = temporal.get("claim") or {}
        if temporal_claim.get("unresolved"):
            temporal_missing.extend(temporal_claim["unresolved"])
        for warning in temporal.get("warnings") or []:
            code = _string(warning.get("code"))
            if warning.get("severity") == "warning":
                temporal_warnings.append(warning)
            elif ((code.startswith("publication_date_") and not code.endswith("available"))
                  or code.endswith(("_invalid", "_ambiguous")) or code == "unresolved_evidence_expressions"):
                temporal_missing.append(warning)
            elif code == "event_period_unknown" and temporal_claim.get("classification") != "timeless_candidate":
                temporal_missing.append(warning)
        if temporal_missing:
            add("temporal_information_unknown", CATEGORIES[3], "unknown", "temporal", "Some relevant date metadata or temporal expressions are missing, ambiguous or unresolved. Missing dates alone do not invalidate a source.",
                details=temporal_missing, suggestion="Establish publication, update and actual event dates separately, with an explicit reference for relative expressions.")
        if temporal_warnings:
            add("temporal_review", CATEGORIES[3], "heuristic", "temporal", "Existing temporal diagnostics flag possible time-period, recency, metadata or prediction/outcome concerns. They did not override the verdict.",
                details=temporal_warnings, suggestion="Check the same event/time period and seek confirmed outcomes rather than plans or predictions.")
            if any(warning.get("code") == "prediction_not_confirmed_outcome" for warning in temporal_warnings):
                add("future_outcome_unconfirmed", CATEGORIES[3], "heuristic", "temporal", "Prediction/intent wording was detected; an eventual outcome has not been established by that wording.",
                    suggestion="Find a dated record of the completed outcome, or keep the future claim unresolved.")
    numerical_mismatch, numerical_unresolved, quantifier_warnings = [], [], []
    if isinstance(numerical, dict) and "numerical" not in missing_views and "numerical" not in misaligned_views:
        for source in numerical.get("sources") or []:
            for comparison in source.get("comparisons") or []:
                item = dict(comparison, source_index=source.get("source_index"))
                if comparison.get("status") == "potential_mismatch":
                    numerical_mismatch.append(item)
                elif comparison.get("status") == "comparison_unresolved":
                    numerical_unresolved.append(item)
            quantifier_warnings.extend(source.get("quantifier_warnings") or [])
        if numerical_mismatch:
            add("quantity_mismatch", CATEGORIES[4], "rule_based", "numerical", "Existing numerical diagnostics report conditional quantity mismatches; these are not new Contradicted verdicts.",
                details=numerical_mismatch, suggestion="Align entity, property, population, units, baseline and time before interpreting a value difference.")
        if numerical_unresolved:
            add("quantity_comparison_unresolved", CATEGORIES[4], "unknown", "numerical", "Some quantity/scope comparisons are unresolved; missing quantities do not establish falsity.",
                details=numerical_unresolved, suggestion="Obtain explicit values, units, population, baseline and matching time context.")
        if quantifier_warnings:
            add("quantifier_scope", CATEGORIES[4], "heuristic", "numerical", "Existing diagnostics flag quantifier or negation scope. Some alone does not disprove all; scope warnings are not directional evidence.",
                details=quantifier_warnings, suggestion="Clarify universal/existential scope and the relevant population; inspect genuine counterexamples where appropriate.")

    order = {category: index for index, category in enumerate(CATEGORIES)}
    findings.sort(key=lambda row: (order[row["category"]], row["code"]))
    categories = [category for category in CATEGORIES if any(row["category"] == category for row in findings)]
    if not categories:
        categories = [CATEGORIES[-1]]  # Absence of findings is never certification.
    suggestions = list(dict.fromkeys(row["suggestion"] for row in findings if row["suggestion"]))
    dimensions = {name: ("Unavailable" if name in missing_views or name in misaligned_views else
                         "Findings reported" if any(row["origin"] == name for row in findings) else "No identified diagnostic issue")
                  for name in ("independence", "temporal", "numerical")}
    return {
        "diagnostic_only": True, "verdict": verdict, "recorded_explanation": explanation or None,
        "primary_reason": {"text": explanation if verdict == "Inconclusive" and explanation else None,
                           "origin": "recorded_explanation" if verdict == "Inconclusive" and explanation else "not_determined",
                           "note": "Verbatim decision explanation, not independently established causality" if verdict == "Inconclusive" and explanation else
                                   "No primary uncertainty cause inferred; inspect the recorded explanation and additional limitations"},
        "categories": categories, "availability": availability, "agreement": agreement,
        "counts": {"retrieved_entries": len(results), "nonempty_passages": sum(bool(_string(source.get("content")).strip()) for source in results),
                   "trace_records": len(records), "directly_relevant_source_labels": directly_relevant,
                   "supporting_records": len(support), "contradicting_records": len(contradict),
                   "conflicting_records": len(conflicting), "not_counted_records": sum(row["contributed"] is False for row in records),
                   "unknown_contribution_records": len(unknown_flags), "unmatched_trace_sources": len(missing_sources),
                   "recorded_exclusions": len(exclusions), "raw_effective_differences": len(raw_differences),
                   "distinct_diagnostic_urls": independence_counts.get("distinct_source_urls"),
                   "numerical_mismatch_records": len(numerical_mismatch) if "numerical" not in missing_views + misaligned_views else None,
                   "numerical_unresolved_records": len(numerical_unresolved) if "numerical" not in missing_views + misaligned_views else None},
        "minimum_directional_sources_setting": MIN_DIRECTIONAL_SOURCES,
        "trace_complete": trace_complete, "findings": findings, "dimensions": dimensions,
        "unknown_information": [row["code"] for row in findings if row["basis"] == "unknown"],
        "suggestions": suggestions, "limitations": LIMITATIONS,
    }
