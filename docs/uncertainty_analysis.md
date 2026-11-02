# Evidence Sufficiency and Uncertainty Intelligence — diagnostic summary

Open **Why did TruthLens reach this verdict? → Evidence Sufficiency and
Uncertainty**. This summary appears before the detailed evidence and diagnostic
panels. It displays the recorded uncertainty reason where available, categories,
trace-record counts, limitations, unavailable information, and suggestions for
additional evidence. Supported and Contradicted results keep their verdicts and
show any remaining limitations.

## Integration and data reuse

`uncertainty_analysis.analyze_uncertainty()` consumes the original assessment and
retrieved result records plus the already-computed `independence`, `temporal` and
`numerical` views. `build_explanation()` computes each of those views once and
passes the same objects into the summary. The summary does not rerun any search,
model, extraction, similarity, URL normalization, threshold check or aggregation.

The output contains `categories`, structured `findings`, `availability`,
`agreement`, observational `counts`, `primary_reason`, `unknown_information`,
dimension summaries, suggestions and limitations. Input objects remain unchanged.
Each finding records a stable code, category, basis, origin, original detail
references and an explicit `additional_diagnostic_only` relationship to the verdict.

### Attribution boundary

For an Inconclusive verdict with a nonempty `assessment.reasoning`, the primary
reason is **that exact string**, labeled as the recorded decision explanation.
It is not independently verified causal reasoning. Without that string, no
primary reason is invented. A decisive verdict never receives a newly inferred
uncertainty cause, even when numerical/time/provenance warnings are present.

Additional diagnostics are never promoted to verdict causes. Recorded per-passage
exclusions can be described as exclusions, but are not independently asserted to
have caused the final result. A numerical mismatch detected after aggregation,
for example, did not cause an earlier Inconclusive verdict. Suggestions describe
what could improve evidence, not what a model must conclude.

## Taxonomy and epistemic basis

| Category | Trigger examples | Boundary |
|---|---|---|
| Insufficient evidence | No results; recorded irrelevant/weak relevance; recorded minimum shortfall; unresolved component or no counted direction | No evidence is not falsity; semantic relevance is not inferred from exact-wording failures |
| Conflicting evidence | Recorded conflicting passages or accepted opposing component directions | Distinct components are not necessarily contradictory propositions; excluded conflicts are not reintroduced as votes |
| Uncertain provenance | Reported duplicates, shared references, possible dependency, unknown independence | Different domains and absent dependency signals do not prove independence |
| Temporal uncertainty | Unknown dates, unresolved time expressions, time-period/recency/prediction warnings | Missing dates do not invalidate evidence; a predicted outcome is not a completed event |
| Numerical ambiguity | Existing potential mismatches, unresolved comparisons and scope warnings | No new arithmetic or contradiction decision is made |
| Model assessment limitation | Raw/effective label differences, exclusions, fallback, unavailable/misaligned trace/views | This includes decision-information limitations; it does not necessarily indicate a model error |
| No identified diagnostic issue | Bounded fallback/quiet dimension label | Never certification of reliability, sufficiency or independence |

Findings distinguish **observed** supplied records, **rule-based** diagnostic
classifications, **heuristic** suspicions and **unknown** information. “Observed”
means present in supplied data/trace, not verified truth of a webpage assertion.
Near-duplicate and context interpretations remain heuristic. Shared citations
are observed references, not proven copying or exclusive reliance.

The existing provenance engine never establishes source independence. Consequently
every nonempty result set retains a provenance limitation in this implementation;
an overall “no identified issue” example is not manufactured for evaluation.
Temporal/numerical dimensions can report no identified issue while provenance
remains unknown. Missing views instead say unavailable. No probability of truth,
calibrated confidence or numerical independence score is produced.

## Counts, agreement and missing traces

Counts describe retrieved entries, nonempty snippets, source relevance labels,
source/component trace records, accepted-direction flags, conflicting records,
explicit exclusions, raw/effective differences and unknown contribution fields.
The distinct-URL count is reused from the independence view and is unavailable
when that value was not supplied. Missing numerical views produce unknown (`null`)
numeric-warning counts rather than zeros.

One source can have several components, and raw `contributed` flags are not an
independently reconstructed set of final votes. Counts therefore must not be
compared to the two-source minimum to invent a new insufficiency cause. Minimum
shortfall classification only recognizes known wording in the original decision
explanation; that adapter can miss future wording changes. Component outcomes
and absence of recorded directional flags are separately described as recorded.

Agreement distinguishes supporting-only, contradicting-only, within-component
mixed directions, mixed directions across components, recorded internal conflicts,
no recorded direction, and unknown direction. Unknown contribution flags are not
converted to false. In particular, the existing rule-based fallback can retain a
decisive verdict while lacking per-source contribution flags.

Source trace URLs must align with retrieved URLs before their labels are
attributed. Missing/malformed diagnostic projections, source-list misalignment
and contradictory reported counts are flagged without repairing the inputs or
recomputing upstream analyses. A decisive result with accepted same-component
conflict merits trace inspection; a legitimately excluded internal conflict does
not create that accepted-conflict warning. Misaligned diagnostic views are marked
unavailable and their findings are not attached to the current evidence.

Dynamic explanations, titles and suggestions are rendered through plain text.
Existing source links and evidence highlights retain their escaping mechanisms.
An HTML-like string in a saved explanation stays literal text in this section.

## Separate synthetic challenge and metrics

`evaluation/uncertainty_challenge.json` contains **24 developer-authored snapshot
cases and 37 synthetic source entries**. These are **minimal saved-data
projections**, not actual Tavily/model runs, real citations, pilot records,
independent annotations or gold factual verdicts. The materializer supplies
aligned reserved `.example` identifiers and quiet metadata; non-default trace
and diagnostic signals and expected labels are explicitly authored in the JSON.
It never invokes upstream detectors to generate these snapshots.

Cases cover missing/irrelevant evidence, one qualifying direction, cross-source
and internal conflicts, duplicates, uncertain provenance, missing/ambiguous
dates, temporal mismatch, prediction/outcome concerns, numerical mismatch,
unresolved comparisons, quantifier warnings, combined categories, fallback,
missing/misaligned views, contradictory traces and decisive results with warnings.

Each case specifies an ID/category/rationale, source count, saved verdict/reason,
projected trace, optional diagnostic signals, expected category set, and a boolean
decision/view-information-gap label. Expected categories are inclusion limitations,
not truth labels. The two source-free cases do not require nonexistent source traces.

Run without network, models or holdouts:

```sh
.venv/bin/python -m evaluation.evaluate_uncertainty
```

`--output path/to/new_report.json` writes a new report and refuses overwrite. The
runner reads only this challenge file. Per-category TP/FP/FN/TN, precision, recall,
F1 and false-positive rate are reported. Micro metrics pool case/category decisions;
macro-F1 averages only categories present in expected labels. Exact-set accuracy
requires every label for a case to match. Undefined metrics are `null`.

Decision/view-information-gap detection specifically concerns unavailable or
misaligned traces/views and contradictory counts. Unknown dates and provenance
are evaluated through their categories instead. Incorrect-attribution measurement
checks the structural contract: a primary explanation must be a verbatim
Inconclusive trace reason and additional findings must not claim verdict causation.
This is **not independently annotated causal correctness or model faithfulness**.

## Actual results — 2 November 2026

Saved output: [uncertainty_challenge_2026-11-02.json](../evaluation/results/uncertainty_challenge_2026-11-02.json).

| Measurement | Result | Denominator |
|---|---:|---|
| Category micro precision / recall / F1 | 1.000 / 1.000 / 1.000 | 59 expected positive labels |
| Category macro-F1 | 1.000 | 6 categories with expected support |
| Exact category-set match | 1.000 | 24/24 cases |
| False-positive warnings, supported categories | 0.000 | 0/85 negative case/category decisions |
| Decision/view-information-gap precision / recall | 1.000 / 1.000 | 5 positive, 19 negative cases |
| Attribution-contract violations | 0.000 | 0/24 cases |

Expected category supports: insufficient 12, conflicting 4, provenance 22,
temporal 5, numerical 4, model/trace limitation 12. “No identified diagnostic issue”
has zero global expected support; its precision/recall/F1 are undefined and it is
excluded from macro-F1. The report also shows micro metrics across all seven
labels (including 24 extra negatives for that absent category); the table above
uses only supported categories for its false-positive denominator.

These perfect snapshot matches are contract/aggregation checks authored alongside
the code, not a generalization result. Common provenance labels and overlapping
categories affect the aggregate metrics. The fixtures do not test whether an
upstream temporal, numerical, provenance or NLI assessment is correct. Their
previous standalone evaluations remain separate and retain their known errors.

The selected regression suite passed **330 targeted tests** (277 baseline plus
53 added checks). It includes real offline rule/NLI-mock/fallback paths, safe UI
rendering, stable ordering, direct reuse of diagnostic objects, unavailable data
and accepted-versus-excluded conflict distinctions. The existing urllib3/LibreSSL
warning remains. No held-out/annotation suites, live Tavily requests or real-model
inference were used.
Syntax compilation passed for 13 relevant Python files and `git diff --check`
passed. The uncertainty, temporal, provenance and numerical reports reproduced
exactly. Streamlit's main page and health endpoint returned HTTP 200, and the
temporary server was stopped. SHA-256 checks verified that 30 protected assessor,
diagnostic, pilot/import and sealed-approval files were unchanged.

## Limitations and next step

The summary trusts supplied trace/view contents and can only detect some structural
inconsistencies. Legacy traces may omit exact final vote counts, and known reason
phrases can change. A recorded explanation can itself be incomplete or misleading;
copying it is trace attribution, not proof of causal faithfulness. Some generic
warning groups can be broad, and suggestions are not guarantees of a decisive result.

The next research step is independently reviewed uncertainty-category and
attribution annotations on realistic saved verification runs, with separate labels
for upstream detector error and summary error. Evaluate omissions, inappropriate
warnings, user understanding and causal wording before any production decision
policy changes. Existing pilot records and approvals were not used or modified.
