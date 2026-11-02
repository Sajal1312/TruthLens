# Explainable Evidence Engine

After verification, open **Why did TruthLens reach this verdict?** inside the
assessment card. The section displays the original claim, recorded verdict and
aggregation reason, component outcomes, and the actual retrieved source links.
Each source/component shows its recorded effective assessment, raw NLI label
when present, inclusion/exclusion reason, model score and margin, dates, and
provenance warnings. Source categories and differing URLs do not prove accuracy
or editorial independence.

## Method and boundaries

`explainability.py` builds a read-only view of the existing assessment object.
It does not classify evidence, recalculate votes, call a model/search service,
or change a threshold. It uses retrieved titles and URLs rather than generating
citations. The original evidence passed to NLI is never edited.

The excerpt selector first locates the assessor's recorded passage in the
retrieved snippet, allowing the window builder's whitespace normalization. Long
passages are shortened to a sentence and, when necessary, a word boundary.
Without a recorded passage, sentence selection uses word overlap as a reading
aid only. This cannot establish support, contradiction, relevance, or causal
model attribution. If a recorded passage cannot be located, that limitation is
shown and the reading aid stays neutral. Full snippets remain in source cards.

Teal and rose excerpts reflect recorded counted support and contradiction,
respectively. Gray denotes excluded, non-directional or unavailable decisions.
Text labels accompany the colors. Conflicting passages on one URL are shown
separately, retaining their individual labels and the pipeline's decision to
exclude their directional votes. Raw NLI labels can differ from effective labels
after safeguards; an excluded raw SUPPORTS prediction remains gray. A single
counted supportive passage can appear under an overall Inconclusive verdict.

All excerpt text is HTML-escaped before fixed highlighting markup is added.
Source titles, reasons, URLs and metadata use plain text or escaped HTTP(S)
links. Retrieved HTML and Markdown are never interpreted as instructions.

Publication dates use only the returned `published_date`. Explicit optional
`updated_date` or `last_updated` metadata is shown separately. Missing dates are
reported as not returned; retrieval timestamps are never substituted. The current
Tavily adapter returns publication metadata but does not supply update metadata,
so live update dates will normally be unavailable.

The existing model-unavailable fallback does not retain complete source-level
vote traces. Its recorded aggregation reason and evidence-used list are shown,
while missing contribution flags are explicitly unavailable. The explanation
layer does not reconstruct those votes. Explanations can expose limitations or
mistakes in the existing pipeline; they cannot independently validate its result.

## Reproducible offline checks

From the project directory:

```sh
.venv/bin/python -m pytest -q tests/test_explainability.py tests/test_app_ui.py tests/test_verifier.py tests/test_nli_assessor.py tests/test_evidence_quality.py
```

The seven parameterized trace cases cover two-source support, two-source
contradiction, insufficient directional evidence, neutral predictions,
cross-source conflict, lexical similarity without the claimed relation, and
missing evidence. They contain nine synthetic source/component decisions, with
explicit expected verdicts and highlight roles. Additional tests exercise raw
versus effective labels, historical/hypothetical exclusions, duplicates,
within-source conflicts, partial compound evidence, time mismatch, HTML
injection, missing dates, unavailable traces, and UI rendering with mocked search
and model outputs. Synthetic `.example` sources are test fixtures, not citations.

These tests measure agreement between the explanation view and recorded pipeline
decisions. They do not measure factual correctness, causal faithfulness to NLI
internals, human comprehension, or generalization. Human evaluation should
separately score attribution accuracy, exclusion-reason correctness, and whether
users understand Inconclusive and score limitations. No independent human
evaluation, agreement score, or live search result is claimed here.

Validation on 2 November 2026: the command above passed **125 tests**, including
21 new explanation/UI checks. All seven parameterized scenarios and their nine
source/component decisions matched the expected verdict/display roles. Syntax
compilation passed for seven relevant Python files. Streamlit's main page and
health endpoint returned HTTP 200; the temporary server was stopped. The existing
urllib3/LibreSSL compatibility warning remains. Held-out and annotation suites
were excluded, and no live search or real-model inference was performed.
