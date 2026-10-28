"""TruthLens Streamlit interface. Assessment logic lives in verifier.py and nli_assessor.py."""
import html
import re
from urllib.parse import urlsplit

import streamlit as st

from verifier import VerificationError, assess_evidence, get_tavily_key, search_evidence
from nli_assessor import assess_with_optional_nli
from evidence_quality import source_category_order, source_context


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


def _summary_card(assessment, results, use_nli):
    with st.container(border=True):
        left, right = st.columns([1.35, 5])
        with left:
            _badge(assessment.get("verdict", "Inconclusive"))
        with right:
            st.markdown("**Assessment method**")
            st.write(assessment.get("method", "Evidence assessment"))

        st.markdown("**Reasoning**")
        st.write(assessment.get("reasoning", "The available evidence was insufficient for an assessment."))

        if assessment.get("fallback_used"):
            st.warning("The local NLI model could not load. This result uses the existing rule-based fallback; NLI labels were not produced.")
        elif use_nli:
            st.caption("NLI labels describe the model’s reading of relevant snippets. Model scores are not probabilities that the claim is true.")

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
                with st.spinner("Searching sources and assessing evidence…"):
                    results = search_evidence(normalized, key)
                    if use_nli:
                        assessment = assess_with_optional_nli(normalized, results)
                    else:
                        assessment = assess_evidence(normalized, results)

                st.divider()
                st.subheader("Assessment")
                _summary_card(assessment, results, use_nli)
                st.markdown(" ")
                _source_cards(results, assessment, use_nli)
            except VerificationError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error("Something unexpected went wrong ({0}). Please try again. If it continues, check your internet connection and Tavily key.".format(type(exc).__name__))

st.divider()
st.caption("TruthLens · Search results are clues to examine, not proof by themselves.")
