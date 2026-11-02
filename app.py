"""TruthLens Streamlit interface. Assessment logic lives in verifier.py and nli_assessor.py."""
import html
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import streamlit as st

from verifier import (VerificationError, assess_evidence, get_tavily_key,
                      search_evidence, search_evidence_with_metrics)
from nli_assessor import (MIN_CONFIDENCE, MIN_DIRECTIONAL_SOURCES, MIN_MARGIN,
                          assess_with_optional_nli)
from evidence_quality import (provenance_diagnostics, source_category_order,
                              source_context)
from explainability import build_explanation, highlighted_evidence


st.set_page_config(page_title="TruthLens | Evidence check", page_icon="◉", layout="wide")

st.markdown("""
<style>
:root {
  --page: #0b1220;
  --panel: #111c2b;
  --panel-soft: #152235;
  --line: #2c3d52;
  --text: #eef4fb;
  --muted: #b1bfd0;
  --teal: #74e4ce;
  --amber: #ffdb83;
  --rose: #ffabb5;
}
.stApp {
  background: var(--page);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.main .block-container { max-width: 1080px; padding: 2rem 1.5rem 3.5rem; }
[data-testid="stHeader"] { background: rgba(11, 18, 32, .96); }
[data-testid="stSidebar"] { background: var(--page); }
h1, h2, h3, h4 { color: var(--text) !important; letter-spacing: -.02em; }
h1 { font-size: clamp(2rem, 4vw, 2.85rem) !important; line-height: 1.12 !important; }
h2 { font-size: 1.55rem !important; margin: 0 0 .35rem !important; }
h3 { font-size: 1.22rem !important; }
p, li, label, [data-testid="stMarkdownContainer"] { color: var(--text); }
.brand { color: #dbe8f6; font-size: .88rem; font-weight: 750; letter-spacing: .13em; }
.brand b { color: var(--teal); }
.eyebrow { color: var(--teal); font-size: .76rem; font-weight: 750; letter-spacing: .15em; text-transform: uppercase; margin: 1.5rem 0 .55rem; }
.intro { color: var(--muted); max-width: 680px; font-size: 1.04rem; line-height: 1.6; }
.section-kicker { color: var(--muted); font-size: .9rem; }
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--panel);
  border-color: var(--line) !important;
  border-radius: 16px !important;
}
div.stButton > button[kind="primary"] {
  background: var(--teal); color: #07151a; border: 1px solid var(--teal);
  border-radius: 10px; font-weight: 750; min-height: 3rem;
}
div.stButton > button[kind="primary"]:hover { background: #a1f2e3; border-color: #a1f2e3; color: #07151a; }
div.stButton > button:focus-visible, a:focus-visible, textarea:focus-visible {
  outline: 3px solid #fff !important; outline-offset: 2px !important;
}
[data-testid="stTextArea"] textarea {
  background: #0e1928 !important; color: var(--text) !important;
  border-color: #43566e !important; border-radius: 10px !important; line-height: 1.55;
}
[data-testid="stTextArea"] textarea::placeholder { color: #a8b7c9 !important; opacity: 1; }
.verdict-badge {
  display: inline-flex; align-items: center; gap: .45rem; padding: .45rem .9rem;
  border-radius: 999px; font-size: 1rem; font-weight: 800; letter-spacing: .01em;
  border: 1px solid currentColor;
}
.verdict-supported { color: #a8f0df; background: #123a36; }
.verdict-contradicted { color: #ffc0c7; background: #42252e; }
.verdict-inconclusive { color: #ffe2a0; background: #40351f; }
.source-link { color: var(--teal) !important; overflow-wrap: anywhere; font-size: .86rem; text-decoration-thickness: 1px; }
.fine-print { color: var(--muted); font-size: .86rem; line-height: 1.55; }
.evidence-excerpt { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.65; margin: .6rem 0; }
.evidence-excerpt mark { padding: .12rem .25rem; border-radius: 4px; box-decoration-break: clone; }
.evidence-support { background: #123a36; color: #a8f0df; }
.evidence-contradiction { background: #42252e; color: #ffc0c7; }
.evidence-neutral { background: #253348; color: #eef4fb; }
div[data-testid="stExpander"] { border-color: var(--line); border-radius: 10px; }
[data-testid="stText"] pre {
  white-space: pre-wrap !important;
  overflow-wrap: anywhere !important;
  word-break: normal !important;
  font-family: inherit !important;
  color: var(--text) !important;
  line-height: 1.55 !important;
  margin: 0 !important;
}
@media (max-width: 700px) {
  .main .block-container { padding: 1.25rem .85rem 2.5rem; }
  .eyebrow { margin-top: 1.1rem; }
  [data-testid="stVerticalBlockBorderWrapper"] { border-radius: 12px !important; }
}
</style>
""", unsafe_allow_html=True)


def _clean_display_text(value):
    """Remove common Markdown decoration for display without changing source data."""
    if not isinstance(value, str):
        return ""
    text = value
    # Strip conventional headings at physical line starts.
    text = re.sub(r"(?m)^([ \t]{0,3})#{1,6}[ \t]+", r"\1", text)
    # Tavily sometimes flattens page headings into the middle of a snippet line.
    # Remove repeated heading markers there too, keeping the heading text intact.
    text = re.sub(r"(?<!\S)#{2,}[ \t]+", "", text)
    # A single hash can also be a flattened heading after sentence/metadata punctuation.
    text = re.sub(r"(?<=[.!?:])\s+#[ \t]+(?=[A-Z])", " ", text)
    # Clean a heading at the start of a source title embedded in an evidence line.
    text = re.sub(r":\s+#{1,6}[ \t]+", ": ", text)
    # Remove paired emphasis/code markers but keep all enclosed words and punctuation.
    text = re.sub(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1", r"\2", text)
    text = re.sub(r"(?<!`)`([^`\n]+)`(?!`)", r"\1", text)
    text = re.sub(r"~~(?=\S)(.+?)(?<=\S)~~", r"\1", text)
    # Limit excessive blank space while retaining paragraph breaks.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _badge(label):
    """Render a text-labelled verdict/assessment badge with adequate contrast."""
    normalized = str(label).strip().lower()
    if normalized == "supported":
        style = "verdict-supported"
    elif normalized == "contradicted":
        style = "verdict-contradicted"
    else:
        style = "verdict-inconclusive"
    st.markdown(
        '<span class="verdict-badge {0}">{1}</span>'.format(style, html.escape(str(label))),
        unsafe_allow_html=True,
    )


def _source_link(url):
    """Show the retrieved URL itself as the link destination and visible domain."""
    try:
        parsed = urlsplit(url)
    except (TypeError, ValueError):
        return
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return
    safe_url = html.escape(url, quote=True)
    domain = html.escape(parsed.netloc)
    st.markdown(
        '<a class="source-link" href="{0}" target="_blank" rel="noopener noreferrer">{1}</a>'.format(
            safe_url, domain
        ),
        unsafe_allow_html=True,
    )


def _component_evidence(assessment, results):
    """Show which actual result URLs contributed to each NLI claim component."""
    components = assessment.get("part_outcomes") or []
    per_source = assessment.get("per_source") or []
    if not components:
        return

    with st.expander("Claim-component evidence", expanded=False):
        for component in components:
            part = component.get("claim_part", "Claim component")
            st.markdown("**{0}**".format(html.escape(part)))
            outcome = component.get("verdict", "Inconclusive")
            _badge("Conflicting evidence" if outcome == "conflicting" else outcome)
            found = False
            for index, source_row in enumerate(per_source):
                if index >= len(results):
                    continue
                retrieved = results[index]
                for part_row in source_row.get("part_assessments", []):
                    if part_row.get("claim_part") != part or not part_row.get("contributed"):
                        continue
                    found = True
                    title = _clean_display_text(retrieved.get("title") or "Retrieved source")
                    url = retrieved.get("url") or ""
                    st.text("{0}: {1}".format(part_row.get("label", "Assessment"), title))
                    _source_link(url)
            if not found:
                st.caption("No source met the relevance and confidence requirements for this component.")
            st.markdown(" ")


def _evidence_role_groups(assessment, results):
    """Build display groups from assessor output, preserving input URLs/text."""
    groups = {"Supporting passages": [], "Contradicting passages": [],
              "Relevant but inconclusive passages": [], "Excluded or not matched": []}
    rows = assessment.get("per_source") or []
    for index, item in enumerate(results):
        row = rows[index] if index < len(rows) else {}
        title = _clean_display_text(item.get("title") or "Retrieved source")
        url = item.get("url", "")
        date = _clean_display_text(item.get("published_date") or "")
        parts = row.get("part_assessments") or []
        if parts:
            for part in parts:
                label = str(part.get("label") or "NOT ENOUGH INFORMATION").upper()
                status = str(part.get("status") or row.get("status") or "No assessment details")
                relevance = row.get("relevance")
                if (status.startswith("Excluded") or "not counted" in status.lower()
                        or relevance in ("Weakly related", "Different time period", "Unrelated")):
                    group = "Excluded or not matched"
                elif label == "SUPPORTS" and part.get("contributed"):
                    group = "Supporting passages"
                elif label == "CONTRADICTS" and part.get("contributed"):
                    group = "Contradicting passages"
                elif relevance == "Directly relevant candidate":
                    group = "Relevant but inconclusive passages"
                else:
                    group = "Excluded or not matched"
                groups[group].append({"title": title, "url": url, "date": date,
                                      "passage": part.get("passage") or item.get("content", ""),
                                      "label": part.get("label", "Not assessed"),
                                      "reason": status, "claim_part": part.get("claim_part", "")})
            continue

        label = str(row.get("label") or "").upper()
        if label == "SUPPORTS" and row.get("contributed"):
            group = "Supporting passages"
        elif label == "CONTRADICTS" and row.get("contributed"):
            group = "Contradicting passages"
        elif label in ("CONFLICTING", "NOT ENOUGH INFORMATION") and row.get("relevance") == "Directly relevant candidate":
            group = "Relevant but inconclusive passages"
        else:
            group = "Excluded or not matched"
        groups[group].append({"title": title, "url": url, "date": date,
                              "passage": item.get("content", ""),
                              "label": row.get("label", "Not assessed"),
                              "reason": row.get("status", "No passage-level assessment was returned"),
                              "claim_part": ""})
    return groups


def _render_evidence_roles(assessment, results):
    groups = _evidence_role_groups(assessment, results)
    with st.expander("Evidence by assessment role", expanded=False):
        st.caption("These groups reflect the assessment output. They do not establish source accuracy or independence.")
        for heading, entries in groups.items():
            st.markdown("**{0} ({1})**".format(heading, len(entries)))
            if not entries:
                st.caption("No passages in this group.")
                continue
            for entry in entries:
                st.text("{0}{1} — {2}".format(
                    entry["title"],
                    " · " + entry["claim_part"] if entry["claim_part"] else "",
                    entry["label"],
                ))
                _source_link(entry["url"])
                if entry["date"]:
                    st.text("Published: " + entry["date"])
                st.text(_clean_display_text(entry["passage"]) or "No snippet was returned.")
                st.caption(entry["reason"])


def _render_timing_summary(timings):
    with st.expander("Performance timing (local diagnostic)", expanded=False):
        st.caption("Wall-clock measurements for this run only. No claim text, URL list, or API key is logged. Total ends after assessment and excludes rendering. Model-load, filtering, inference, and aggregation timings are separate stages.")
        labels = (
            ("search_request_ms", "Search request and response wait"),
            ("response_processing_ms", "Response parsing and result cleanup"),
            ("model_load_ms", "Local model load"),
            ("evidence_filtering_ms", "Evidence filtering and candidate processing"),
            ("nli_inference_ms", "NLI model inference"),
            ("aggregation_ms", "Verdict aggregation and explanation"),
            ("rule_assessment_ms", "Rule-based assessment"),
            ("assessment_total_ms", "Assessment total"),
            ("total_verification_ms", "Total verification (retrieval + assessment)"),
        )
        for key, label in labels:
            if key in timings:
                st.text("{0}: {1:.2f} ms".format(label, timings[key]))
        if "nli_model_calls" in timings:
            st.text("NLI model calls: {0}".format(timings["nli_model_calls"]))
        if "nli_cache_hits" in timings:
            st.text("Same-run cached NLI assessments: {0}".format(timings["nli_cache_hits"]))


def _render_temporal_analysis(analysis):
    st.markdown("**Temporal Evidence Analysis**")
    st.caption("Diagnostic only — these observations do not override the verdict or change evidence votes.")
    context = analysis["claim"]
    st.text("Claim temporal classification: " + context["classification"].replace("_", " "))
    st.text("Reference date supplied by this verification (UTC): " + (context["reference_date"] or "Unavailable"))

    def show_expressions(expressions):
        for expression in expressions:
            period = ("{0} to {1} ({2})".format(expression["start_date"], expression["end_date"], expression["precision"])
                      if expression["status"] == "resolved" else expression["status"])
            st.text("{0}: {1} → {2}".format(expression["role"].replace("_", " "), expression["text"], period))

    show_expressions(context["expressions"])
    if not context["expressions"]:
        st.caption("No explicit date or supported relative expression detected. Present tense alone does not make a statement time-sensitive.")
    for unresolved in context["unresolved"]:
        st.text("Unresolved claim context: " + unresolved)
    for source in analysis["sources"]:
        with st.container(border=True):
            st.text("Source {0}: {1}".format(source["source_index"] + 1, _clean_display_text(source["title"])))
            _source_link(source["url"])
            for label, parsed in source["metadata"].items():
                st.text("{0}: {1} ({2}{3})".format(
                    label.replace("_", " ").capitalize(), _clean_display_text(str(parsed["raw"])) if parsed["raw"] is not None else "Not returned",
                    parsed["status"], ", " + parsed["precision"] + " precision" if parsed["precision"] else ""))
            show_expressions(source["context"]["expressions"])
            for warning in source["warnings"]:
                st.text("{0}: {1}".format(warning["severity"].capitalize(), warning["message"]))
    for warning in analysis["warnings"]:
        if warning["source_index"] is None:
            st.text("Temporal warning: " + warning["message"])
    st.caption(analysis["limitations"])


def _render_independence_analysis(analysis):
    st.markdown("**Evidence Independence Analysis**")
    st.caption("Diagnostic only. Multiple publications do not necessarily provide multiple independent confirmations; these groups do not alter evidence votes.")
    counts = analysis["counts"]
    st.text("Retrieved passage entries: {0} ({1} nonempty) · Distinct valid source URLs: {2} · Missing/invalid URLs: {3}".format(
        counts["retrieved_passages"], counts["nonempty_passages"], counts["distinct_source_urls"], counts["invalid_or_missing_urls"]))
    st.text("Exact duplicate pairs: {0} ({1} repeated passage entries) · Near-duplicate pairs: {2}".format(
        counts["exact_duplicate_pairs"], counts["repeated_passage_entries"], counts["near_duplicate_pairs"]))
    st.text("Explicit shared-reference pairs: {0} · Other possible dependency pairs: {1}".format(
        counts["explicit_dependency_pairs"], counts["possible_dependency_pairs"]))
    st.caption("Counts are pairs, not independent confirmations; different signals can overlap. Exact means matching whitespace-normalized text. Near-duplicate means wording similarity only.")
    table = []
    for relationship in analysis["relationships"]:
        if relationship["category"] == "Independence not established":
            continue
        for signal in relationship["signals"]:
            table.append({"Passages": "S{0} ↔ S{1}".format(relationship["left"] + 1, relationship["right"] + 1),
                          "Relationship": relationship["category"], "Basis type": signal["kind"],
                          "Recorded basis": signal["message"]})
    if table:
        # Dataframe cells are plain text; no retrieved text enters HTML/Markdown.
        st.dataframe(table, hide_index=True, use_container_width=True)
    else:
        st.caption("No dependency signal was detected. This does not establish independence.")
    st.caption("The relationship table distinguishes observed matches/references from heuristic suspicions. Citations are not endorsements. Groups can overlap and must not be summed as independent evidence.")
    for group in analysis["groups"]:
        with st.container(border=True):
            st.text("{0}: {1}".format(group["id"], ", ".join("S" + str(index + 1) for index in group["members"])))
            st.text(group["reason"])
            for index in group["members"]:
                source = analysis["sources"][index]
                st.text("S{0}: {1}".format(index + 1, _clean_display_text(source["title"])))
                _source_link(source["url"])
            for signal in group["basis"]:
                st.text("{0}: {1}".format(signal["kind"].capitalize(), _clean_display_text(signal["message"])))
    for source in analysis["sources"]:
        for attribution in source["attributions"]:
            st.text("S{0} · {1}: {2}".format(source["index"] + 1, attribution["kind"].replace("_", " "),
                                             _clean_display_text(attribution["text"])))
        for warning in source["warnings"]:
            st.text("S{0}: {1}".format(source["index"] + 1, warning))
    st.caption(analysis["limitations"])


def _render_numerical_analysis(analysis):
    st.markdown("**Numerical and Quantifier Analysis**")
    st.caption("Diagnostic comparisons only. Compatible does not mean proven; potential mismatch does not override the verdict.")

    def show_extracted(extracted, label):
        st.text(label)
        if not extracted["quantities"]:
            st.caption("No supported digit-based quantity found; absence is not a contradiction.")
        for index, quantity in enumerate(extracted["quantities"]):
            if quantity["status"] != "resolved":
                st.text("Q{0}: {1} — unresolved: {2}".format(index + 1, quantity["text"], quantity["reason"]))
                continue
            bounds = "{0}{1}, {2}{3}".format("[" if quantity["lower"] is not None and quantity["lower_inclusive"] else "(",
                quantity["lower"] if quantity["lower"] is not None else "−∞",
                quantity["upper"] if quantity["upper"] is not None else "+∞",
                "]" if quantity["upper"] is not None and quantity["upper_inclusive"] else ")")
            st.text("Q{0}: {1} → {2} {3} ({4}{5})".format(index + 1, quantity["text"], bounds,
                quantity["normalized_unit"] or "dimensionless/count", quantity["comparator"],
                "; approximate, tolerance " + quantity["tolerance"] if quantity["approximate"] else ""))
        for quantifier in extracted["quantifiers"]:
            st.text("Quantifier: {0} ({1}{2})".format(quantifier["text"], quantifier["kind"].replace("_", " "),
                "; preceded by negation" if quantifier["negated"] else ""))
        if extracted["dates"]:
            st.text("Time expressions kept separate from quantities: " + ", ".join(row["text"] for row in extracted["dates"]))

    show_extracted(analysis["claim"], "Extracted claim quantities and scope")
    for source in analysis["sources"]:
        with st.container(border=True):
            st.text("Source {0}: {1}".format(source["source_index"] + 1, _clean_display_text(source["title"])))
            _source_link(source["url"])
            show_extracted(source["extracted"], "Extracted evidence quantities and scope")
            for comparison in source["comparisons"]:
                references = "Claim {0} · Evidence {1}".format(
                    "Q" + str(comparison["claim_quantity"] + 1) if comparison["claim_quantity"] is not None else "scope",
                    "Q" + str(comparison["evidence_quantity"] + 1) if comparison["evidence_quantity"] is not None else "unmatched")
                st.text("{0} — {1}: {2}".format(references, comparison["status"].replace("_", " ").capitalize(), comparison["reason"]))
            for warning in source["quantifier_warnings"]:
                st.text("Quantifier warning: " + warning)
    st.caption(analysis["tolerance_policy"])
    st.caption(analysis["limitations"])


def _render_uncertainty_analysis(analysis):
    st.markdown("**Evidence Sufficiency and Uncertainty**")
    st.caption("Recorded decision explanations and additional diagnostic warnings have different roles. These warnings do not change the verdict or establish probabilities of truth.")
    primary = analysis["primary_reason"]
    st.text("Primary uncertainty reason from the decision trace: " + (primary["text"] or "Not determined"))
    st.caption(primary["note"])
    st.text("Categories: " + ", ".join(analysis["categories"]))
    st.text("Availability: {0} · Agreement: {1}".format(analysis["availability"].replace("_", " "), analysis["agreement"].replace("_", " ")))
    counts = analysis["counts"]
    st.text("Retrieved entries: {0} · Nonempty snippets: {1} · Directly relevant source labels: {2} · Diagnostic URL count: {3}".format(
        counts["retrieved_entries"], counts["nonempty_passages"], counts["directly_relevant_source_labels"],
        counts["distinct_diagnostic_urls"] if counts["distinct_diagnostic_urls"] is not None else "Unavailable"))
    st.text("Trace records — supporting: {0} · contradicting: {1} · conflicting: {2} · not counted: {3} · unknown contribution: {4} · Unmatched trace sources: {5}".format(
        counts["supporting_records"], counts["contradicting_records"], counts["conflicting_records"],
        counts["not_counted_records"], counts["unknown_contribution_records"], counts["unmatched_trace_sources"]))
    st.caption("Records can include multiple components per source. These are not independent votes. The existing NLI minimum is {0} qualifying directional sources; this summary does not recompute eligibility.".format(analysis["minimum_directional_sources_setting"]))
    for finding in analysis["findings"]:
        st.text("{0} · {1} · {2}: {3}".format(finding["category"], finding["basis"].replace("_", " "), finding["origin"].replace("_", " "), finding["message"]))
    if analysis["unknown_information"]:
        st.text("Unavailable or unresolved information: " + ", ".join(code.replace("_", " ") for code in analysis["unknown_information"]))
    if analysis["suggestions"]:
        st.markdown("**What additional evidence would help?**")
        for suggestion in analysis["suggestions"]:
            st.text("• " + suggestion)
    st.caption(analysis["limitations"])


def _render_verdict_explanation(claim, assessment, results):
    explanation = build_explanation(claim, results, assessment,
                                    reference_date=datetime.now(timezone.utc).date())
    with st.expander("Why did TruthLens reach this verdict?", expanded=False):
        st.text("Claim: " + explanation["claim"])
        st.text("Verdict: " + explanation["verdict"])
        st.text("Method: " + explanation["method"])
        st.text(explanation["reasoning"])
        st.caption("This is a trace of recorded evidence decisions, not an explanation of the model's internal reasoning. Sentence selection uses word overlap only as a reading aid; it never changes a verdict.")
        st.caption("Teal: counted support · Rose: counted contradiction · Gray: not counted or non-directional. Colors describe recorded source/component decisions, not individual words.")
        if explanation["has_nli_decisions"]:
            st.caption("Existing NLI acceptance settings: top model score ≥ {0:.2f}, score margin ≥ {1:.2f}; at least {2} qualifying directional sources, with duplicate/context checks and component aggregation. Scores are model class preferences, not calibrated probabilities or probabilities that a claim is true.".format(
                MIN_CONFIDENCE, MIN_MARGIN, MIN_DIRECTIONAL_SOURCES))
        _render_uncertainty_analysis(explanation["uncertainty"])
        if explanation["components"]:
            st.markdown("**Recorded component outcomes**")
            for component in explanation["components"]:
                st.text("{0}: {1}".format(component.get("claim_part", ""), component.get("verdict", "Not recorded")))
        if explanation["evidence_used"]:
            st.markdown("**Evidence recorded by the aggregator**")
            for evidence in explanation["evidence_used"]:
                st.text(_clean_display_text(evidence))
        if not explanation["entries"]:
            st.info("No retrieved evidence is available. Absence of evidence does not establish that the claim is false.")
        for entry in explanation["entries"]:
            with st.container(border=True):
                st.text("Source {0}: {1}".format(entry["source_index"] + 1, _clean_display_text(entry["title"])))
                _source_link(entry["url"])
                st.text("URL: " + entry["url"])
                st.text("Publisher metadata: " + _clean_display_text(entry["publisher"]))
                st.text("Publication date: " + (_clean_display_text(entry["published_date"]) or "Not returned"))
                st.text("Update date: " + (_clean_display_text(entry["updated_date"]) or "Not returned"))
                st.text("Claim/component: " + entry["claim_part"])
                st.text("Recorded assessment: {0} · {1}".format(
                    entry["label"], "Counted toward aggregation" if entry["contributed"] is True else
                    "Not counted toward aggregation" if entry["contributed"] is False else
                    "Source-level contribution not recorded by this method"))
                if entry["passage_label"] != entry["label"]:
                    st.text("Individual passage assessment: " + entry["passage_label"])
                if entry["model_label"]:
                    st.text("Raw NLI prediction: " + entry["model_label"])
                st.text("Decision reason: " + entry["status"])
                if entry["confidence"] is not None:
                    st.text("Top model score: {0:.3f} · score margin: {1}".format(
                        entry["confidence"], "Not recorded" if entry["margin"] is None else "{0:.3f}".format(entry["margin"])))
                excerpt = entry["excerpt"]
                if excerpt["text"]:
                    st.markdown(highlighted_evidence(_clean_display_text(excerpt["text"]), entry["tone"]), unsafe_allow_html=True)
                    st.caption(excerpt["basis"] + (". Short excerpt; consult the source card's full snippet for context." if excerpt["shortened"] else "."))
                else:
                    st.caption("No evidence text was returned for this source.")
                for warning in entry["warnings"]:
                    st.text(_clean_display_text(warning))
        _render_temporal_analysis(explanation["temporal"])
        _render_independence_analysis(explanation["independence"])
        _render_numerical_analysis(explanation["numerical"])
        st.markdown("**Assessment limitations**")
        st.text(explanation["limitations"] or "No additional limitations were recorded.")
        st.caption("Source categories and URL differences do not establish accuracy or independent reporting. This preliminary evidence assessment is not an authoritative fact-check.")


def _summary_card(assessment, results, use_nli, claim=""):
    with st.container(border=True):
        left, right = st.columns([1.35, 5])
        with left:
            _badge(assessment.get("verdict", "Inconclusive"))
        with right:
            st.markdown("**Assessment method**")
            st.write(assessment.get("method", "Evidence assessment"))

        st.markdown("**Reasoning**")
        st.write(assessment.get("reasoning", "The available evidence was insufficient for an assessment."))

        if assessment.get("original_claim"):
            st.caption("Claim assessed: " + _clean_display_text(assessment["original_claim"]))

        if assessment.get("fallback_used"):
            st.warning("The local NLI model could not load. This result uses the existing rule-based fallback; NLI labels were not produced.")
        elif use_nli:
            st.caption("NLI labels describe the model’s reading of relevant snippets. Model scores are not probabilities that the claim is true.")

        _render_verdict_explanation(claim, assessment, results)
        _render_evidence_roles(assessment, results)
        if assessment.get("evidence_used"):
            with st.expander("Evidence counted toward the assessment", expanded=False):
                for evidence in assessment["evidence_used"]:
                    st.text(_clean_display_text("• {0}".format(evidence)))
        elif results:
            if use_nli and not assessment.get("fallback_used"):
                st.info("No retrieved source met the NLI relevance and confidence requirements for a directional assessment. Review the source cards below.")
            else:
                st.info("The snippets did not match the complete claim or a recognized opposite statement. Related words alone are insufficient.")

        _component_evidence(assessment, results)
        with st.expander("Limitations", expanded=False):
            st.write(assessment.get("limitations", "This is a preliminary evidence assessment, not an authoritative fact-check."))
            st.caption("TruthLens is a preliminary evidence-assessment tool, not an authoritative fact-checking service. Read the sources and use your judgment.")


def _source_cards(results, assessment, use_nli):
    st.subheader("Retrieved sources")
    st.caption("Each link opens the URL returned by the search service. Snippets may omit context.")
    if not results:
        st.info("The search returned no usable sources. Try a more specific claim or search again later.")
        return

    per_source = assessment.get("per_source", [])
    provenance = provenance_diagnostics(results)
    nli_active = use_nli and not assessment.get("fallback_used")
    paired_rows = list(enumerate(results))

    def presentation_key(pair):
        index, _item = pair
        row = per_source[index] if index < len(per_source) else {}
        relevance_rank = {"Directly relevant candidate": 0, "Weakly related": 1,
                          "Different time period": 2, "Unrelated": 3}.get(row.get("relevance"), 4)
        clear_scores = [part.get("confidence", 0.0) for part in row.get("part_assessments", [])
                        if part.get("contributed")]
        strongest_clear_score = max(clear_scores) if clear_scores else 0.0
        independence_rank = 1 if "not independently counted" in row.get("independence", "").lower() else 0
        context = row.get("source_context") or source_context(_item.get("url", ""))
        category_rank = source_category_order(context.get("category", "Unknown"))
        publication_signal = row.get("publication_date_signal", "")
        time_sensitive = "time-sensitive claim" in publication_signal
        date_rank = 0 if time_sensitive and "available" in publication_signal else 1
        # Transparent lexicographic presentation ordering, not a verdict score.
        return (relevance_rank, -strongest_clear_score, independence_rank, date_rank, category_rank, index)

    paired_rows.sort(key=presentation_key)
    for index, item in paired_rows:
        title = _clean_display_text(item.get("title") or "Untitled source")
        url = item.get("url") or ""
        content = item.get("content") or ""
        date = _clean_display_text(item.get("published_date") or "")
        source_row = per_source[index] if index < len(per_source) else {}
        quality = source_row.get("source_context") or source_context(url)

        with st.container(border=True):
            st.text(title)
            _source_link(url)
            category = quality.get("category", "Unknown")
            relevance = source_row.get("relevance", "Not assessed")
            independence = source_row.get("independence", "Not assessed")
            date_relevance = source_row.get("date_relevance", "No explicit claim year")
            publication_signal = source_row.get("publication_date_signal", "Publication date not assessed")
            st.caption("Relevance: {0} · Source category: {1} · {2} · {3} · {4}. Category is context, not verification.".format(
                relevance, category, independence, date_relevance, publication_signal
            ))
            if date:
                st.text("Published: {0}".format(date))

            provenance_row = provenance[index] if index < len(provenance) else {}
            with st.expander("Source provenance notes", expanded=False):
                st.text("Domain: {0}".format(provenance_row.get("domain", "Unknown domain")))
                st.text("Publisher: {0}".format(provenance_row.get("publisher", "Not provided")))
                st.caption(provenance_row.get("publisher_basis", "Publisher identity not assessed"))
                if provenance_row.get("retrieved_at"):
                    st.text("Retrieved: {0}".format(provenance_row["retrieved_at"]))
                st.caption(provenance_row.get("independence", "Independence unknown"))
                st.caption(provenance_row.get("origin_relationship", "Shared original reporting not assessed"))
                for relationship in provenance_row.get("relationships", []):
                    other_index = relationship.get("other_index")
                    other = results[other_index] if isinstance(other_index, int) and other_index < len(results) else {}
                    other_title = _clean_display_text(other.get("title") or "Retrieved source")
                    st.text("Compared with: {0}".format(other_title))
                    observations = relationship.get("observations") or []
                    if observations:
                        for observation in observations:
                            kind = observation.get("kind", "unknown").replace("_", " ").title()
                            st.caption("{0}: {1} — {2}".format(
                                kind,
                                observation.get("label", "Relationship observed"),
                                observation.get("basis", "Basis not recorded"),
                            ))
                    else:
                        # Older diagnostic records may only carry the legacy notes list.
                        for note in relationship.get("notes", []):
                            st.caption(note)

            display_content = _clean_display_text(content)
            short_snippet = display_content
            if len(short_snippet) > 520:
                short_snippet = short_snippet[:520].rsplit(" ", 1)[0].rstrip() + "…"
            st.text(short_snippet or "Tavily did not provide a snippet for this source.")
            if len(display_content) > len(short_snippet):
                with st.expander("Show full retrieved snippet"):
                    st.text(display_content)

            if nli_active:
                st.markdown("**NLI model assessment**")
                part_rows = source_row.get("part_assessments", [])
                if part_rows:
                    if len(part_rows) == 1:
                        _badge(part_rows[0].get("label", "NOT ENOUGH INFORMATION"))
                    else:
                        component_labels = {part_row.get("label", "UNCERTAIN") for part_row in part_rows}
                        summary_label = next(iter(component_labels)) if len(component_labels) == 1 else "MIXED COMPONENTS"
                        _badge(summary_label)
                        st.caption("Open the component details for each claim-part label.")
                else:
                    _badge(source_row.get("label", "UNCERTAIN"))

                with st.expander("NLI diagnostics and model scores"):
                    if part_rows:
                        for part_row in part_rows:
                            st.markdown("**{0} — {1}**".format(
                                html.escape(part_row.get("claim_part", "Claim component")),
                                html.escape(part_row.get("label", "UNCERTAIN")),
                            ))
                            st.caption(part_row.get("status", "No status details"))
                            if part_row.get("inference_cache_hit"):
                                st.caption("NLI prediction reused for identical passage and claim text within this verification; source-specific checks were applied again.")
                            if part_row.get("confidence") is not None:
                                st.write("Top model score: {0:.1%} · score margin: {1:.1%}".format(
                                    part_row["confidence"], part_row.get("margin", 0.0)))
                            if part_row.get("scores"):
                                st.json(part_row["scores"])
                    else:
                        st.caption(source_row.get("status", "No NLI details were returned for this source."))


st.markdown('<div class="brand">◉ TRUTH<b>LENS</b></div>', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">Evidence before certainty</div>', unsafe_allow_html=True)
st.title("Check a claim against the evidence.")
st.markdown('<p class="intro">Search real sources, inspect how they relate to a claim, and see what remains uncertain.</p>', unsafe_allow_html=True)

with st.container(border=True):
    claim = st.text_area(
        "Claim to verify",
        placeholder="Example: The Eiffel Tower is in Paris.",
        height=110,
        max_chars=500,
        label_visibility="visible",
    )
    left, right = st.columns([1.3, 3])
    with left:
        verify = st.button("Verify claim", type="primary", use_container_width=True)
    with right:
        st.caption("Use one clear, checkable statement. Up to 500 characters.")
    use_nli = st.checkbox(
        "Use local NLI model (experimental)",
        value=False,
        help="Loads the local model when first enabled; it may take a minute. If it cannot load, TruthLens uses the existing rule-based fallback.",
    )
    collect_timings = st.checkbox(
        "Show per-run performance timing (diagnostic)",
        value=False,
        help="Shows local timing measurements for this verification only. Nothing is written to logs or sent to Tavily.",
    )

with st.expander("Try illustrative demo examples"):
    st.info("These examples explain the interface only. They use no live sources and do not represent real fact-checks.")
    first, second = st.columns(2)
    with first:
        st.code('"Water freezes at 0°C at standard pressure."')
    with second:
        st.code('"The Moon is made of cheese."')

if verify:
    normalized = " ".join(claim.split())
    if len(normalized) < 12:
        st.warning("Please enter a full claim (at least 12 characters) so the search has enough context.")
    elif normalized.count(".") + normalized.count("?") + normalized.count("!") > 2:
        st.warning("Please check one claim at a time. Split multiple statements into separate checks.")
    else:
        key = get_tavily_key()
        if not key:
            st.error("Tavily API key not found. Add it to `.streamlit/secrets.toml` or your `TAVILY_API_KEY` environment variable, then restart the app. See README.md for steps.")
        else:
            try:
                verification_started = time.perf_counter()
                search_timings = {}
                with st.spinner("Searching sources and assessing evidence…"):
                    if collect_timings:
                        results, search_timings = search_evidence_with_metrics(normalized, key)
                    else:
                        results = search_evidence(normalized, key)
                    assessment_timings = {}
                    if use_nli:
                        assessment = assess_with_optional_nli(
                            normalized, results,
                            cache_predictions=True,
                            timings=assessment_timings if collect_timings else None,
                        )
                    else:
                        assessment_started = time.perf_counter()
                        assessment = assess_evidence(normalized, results)
                        if collect_timings:
                            assessment_timings["rule_assessment_ms"] = (
                                time.perf_counter() - assessment_started) * 1000
                            assessment_timings["assessment_total_ms"] = assessment_timings["rule_assessment_ms"]
                    if collect_timings:
                        assessment_timings.update(search_timings)
                        assessment_timings["total_verification_ms"] = (
                            time.perf_counter() - verification_started) * 1000

                st.divider()
                st.subheader("Assessment")
                _summary_card(assessment, results, use_nli, normalized)
                if collect_timings:
                    _render_timing_summary(assessment_timings)
                st.markdown(" ")
                _source_cards(results, assessment, use_nli)
            except VerificationError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error("Something unexpected went wrong ({0}). Please try again. If it continues, check your internet connection and Tavily key.".format(type(exc).__name__))

st.divider()
st.caption("TruthLens · Search results are clues to examine, not proof by themselves.")
