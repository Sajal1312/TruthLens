# Evidence Independence and Provenance Engine — diagnostics

After verifying a claim, open **Why did TruthLens reach this verdict? → Evidence
Independence Analysis**. This subsection shows passage and URL counts, duplicate
pair counts, shared-reference signals, a relationship table, evidence groups,
literal attributions, and limitations. No numerical independence score is used.
The existing verdict, evidence-counting rules and model settings are unchanged.

## Architecture and data

`evidence_independence.py` reads the existing result fields `title`, `url`,
`content`, and optional `publisher`. It never fetches citations or reads keys,
models, annotations or evaluation holdouts. `explainability.build_explanation()`
exposes its output under `independence`; the application renders this after the
temporal diagnostics. Neither assessor imports or calls the new engine.

It reuses `evidence_quality.passage_similarity()`, the existing 3-word-shingle
Jaccard threshold **0.80**, and `source_context()`. The previous provenance notes
remain available. Publisher labels are supplied metadata, not verified ownership.

A separate diagnostic URL profile is necessary because the existing production
normalizer strips non-root trailing slashes and sorts semantic query parameters.
Changing that production helper would alter existing evidence counts. The new
comparison instead preserves those potentially meaningful distinctions.

## URL identity

Comparison lowercases scheme/host, normalizes IDNA host representation and
default ports, treats an empty path as `/`, and removes `utm_*`, `fbclid` and
`gclid` query parameters. Semantic query keys, values, order, duplicate keys,
path case, non-root trailing slashes, percent encodings, HTTP/HTTPS, and
www/non-www distinctions remain significant.

Only recognized document anchors (`top`, `bottom`, `content`, numbered
`section`/`paragraph`) are removed. Unknown fragments and application routes are
preserved. Missing/malformed URLs, credentials, raw control/unsafe characters,
invalid hosts/ports and malformed percent escapes do not produce identities.
Original URLs and retrieved snippets remain unchanged and source links use the
original URL. This conservative profile can miss equivalent URL variants; it
does not follow redirects or inspect canonical-link metadata. Even recognized
tracking/anchor conventions are assumptions, not verified document identity.

## Pair categories and their meanings

| Category | Basis | What it establishes |
|---|---|---|
| Exact duplicate | Nonempty text identical after whitespace normalization; case/punctuation preserved | Matching supplied text, not authorship or copying |
| Near duplicate | Jaccard ≥ 0.80, at least 12 whitespace words in each passage, no detected number/negation/scope difference | Similar wording; heuristic only |
| Explicit shared-source dependency | Shared cited HTTP(S) URL/DOI, or an explicit citation of the other source | A supplied reference, not exclusive dependence or endorsement |
| Possible dependency | Shared institution/title, supplied publisher label/host, uncategorized URL, or cautious similarity signal | A reason for review; not proof of one reporting chain |
| Independence not established | No qualifying relationship found | Unknown independence |

Near-duplicate checks retain differing numbers and simple negation/quantifier
signatures as caution signals instead of merging on wording alone. This is a
grouping safeguard, not semantic stance reasoning, and cannot recognize all
changes in meaning. Short common phrases are not grouped on similarity alone.
Substantial paraphrases can be missed entirely.

Attribution patterns include “according to NASA” and “Reuters reported”, explicit
named-report titles, DOI strings, and URLs in citation context. Every extraction
keeps its exact source text and offsets. Bare navigation URLs remain mentions.
Recognized negated reliance is not promoted to a citation. Generic institution
or report-title matches remain possible dependencies because editions, topics
and document identities are unresolved. Titles themselves are not evidence for
attribution; the extractor reads the snippet content only.

An explicitly repeated report reference is labeled observed **in the supplied
snippets**. The report page, publisher identity and true reporting chain have not
been verified. References can be critical, incidental, quoted or incomplete.
The engine never reports confirmed independence.

## Grouping and visualization

The structured table uses the existing Streamlit dataframe widget and lists
observed versus heuristic bases explicitly. No graph dependency was added.
Retrieved text is rendered through plain text/dataframe cells; original source
links and the existing highlighted excerpts retain their escaping rules.

Groups use direct matching document URLs, exact text, qualifying near-duplicate
wording or explicit identifiable citations. Every member pair must have a direct
qualifying relationship. Seeded groups extend only if this complete-link condition
holds; subsets are removed, and uncovered sources remain singletons. Weaker
shared-host, organization and title clues never create groups. Pair relationships
remain in the table even when they do not qualify for a group.

Groups can overlap. For A→report X, B→reports X and Y, C→report Y, the output
contains AB and BC; it never invents AC or one ABC group. Groups describe observed
or suspected relationships; their count is not a count of independent sources.
The procedure is deterministic for source order and does not claim a unique or
optimal partition of real reporting chains.

Counters distinguish passage entries, nonempty passages, distinct valid comparison
URLs, invalid/missing URLs, exact duplicate **pairs**, repeated passage **entries**,
near-duplicate pairs and explicit-reference pairs. Three identical passages yield
three duplicate pairs but only two repeated entries. Signals can overlap even
though one highest-priority category is displayed (exact, explicit, near, possible,
unknown). Counts are never fed into aggregation.

## Separate synthetic evaluation

`evaluation/independence_challenge.json` contains **19 developer-authored cases,
40 synthetic source entries, and 23 fully annotated pair comparisons**. Its URLs
use reserved `.example` domains; these are fixtures, not public citations.
“NASA” and “Reuters” attribution phrases are constructed text and do not represent
checked real reports. This dataset is separate from pilot records and holdouts.

The cases cover all requested categories, including same-document passages,
different domains, edited and substantially paraphrased copies, report citations,
shared publishers/institutions, unknown provenance, distinct event evidence,
tracking variations, malformed URLs, changed meanings, navigation links, and
weak/explicit relationship bridges.

Each case defines an ID/category/rationale, source records and one annotation per
source pair: `left`, `right`, and boolean `exact`, `near`, `explicit`, `group`
expectations. These are developer-authored diagnostic labels, not independence
or truth labels. Substantial constructed paraphrases count as positive near-copy
examples so the lexical detector's recall limitation is visible. Similar text
with a material scope change is not a positive under this grouping policy.

Reproduce without network or a model:

```sh
.venv/bin/python -m evaluation.evaluate_independence
```

Use `--output path/to/new_report.json` to save a report; existing files are not
overwritten. The runner reads only the separate challenge file. The JSON report
includes confusion matrices, per-class precision/recall/F1 and sample counts.
Metrics use each detection flag separately, rather than hiding overlapping signals
behind the displayed category. Undefined denominators are `null`.

False-positive grouping rate is the number of grouped pairs labeled unsuitable
for grouping divided by all pairs labeled unsuitable. A failure to group a
positive pair is separately reported as a grouping false negative. A label of
“do not group” does not mean independently verified provenance.

## Measured results — 2 November 2026

Preserved output: [independence_challenge_2026-11-02.json](../evaluation/results/independence_challenge_2026-11-02.json).

| Pair detection | Precision | Recall | TP / FP / FN |
|---|---:|---:|---:|
| Exact duplicate | 1.000 | 1.000 | 2 / 0 / 0 |
| Near duplicate | 1.000 | 0.500 | 1 / 0 / 1 |
| Explicit reference dependency | 1.000 | 1.000 | 4 / 0 / 0 |
| Group membership | 1.000 | 0.900 | 9 / 0 / 1 |

False-positive grouping rate: **0/13 = 0.000**. The missed pair is the substantial
paraphrase, which has little shared phrasing. These tiny, code-adjacent synthetic
cases do not establish real-world precision, recall, independence or source
credibility. Pair observations within a case are not statistically independent.

Validation for this change: **217 targeted offline tests passed** (169-test
baseline plus 48 new tests), including safe Streamlit table rendering, unchanged
rule/NLI verdicts, URL distinctions, missing metadata and non-transitive groups.
Syntax compilation passed for 11 relevant Python files; `git diff --check` passed.
The new challenge and existing temporal report reproduced exactly. Streamlit's
main page and health endpoint returned HTTP 200 and the temporary server was
stopped. The existing urllib3/LibreSSL warning remains. SHA-256 checks confirmed
30 protected production, temporal, pilot/import and approval files were unchanged.
No held-out or annotation suites, live Tavily requests, or real-model inference
were used.

## Limitations and next research step

Snippets can omit attribution or repeat boilerplate. Lexical similarity misses
semantic paraphrases and can mistake similarly worded distinct assertions for
related reporting. The simple scope safeguard does not resolve role reversal,
quotation scope, complex negation or all quantities. Attribution extraction is
English/case-sensitive in parts, can miss aliases, and cannot determine whether a
reference supplies the evidence for the claim. Different editions may share titles
or URLs. Common institutional attribution does not identify one original report.

No dependency found means unknown, never independent. Neither a citation nor
similarity is a source credibility score. The next research step is independently
reviewed document-level reporting chains, with explicit original-report identifiers,
attribution spans, negative boilerplate cases and paraphrases, before considering
any influence on production evidence counts.
