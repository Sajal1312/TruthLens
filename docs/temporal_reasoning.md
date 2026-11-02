# Temporal Intelligence Engine — diagnostic mode

Open **Why did TruthLens reach this verdict? → Temporal Evidence Analysis**
after verification. The section shows the claim classification, reference date,
detected time expressions, source dates with precision, possible temporal
mismatches, and unknown dates. It does not change a verdict, NLI label, vote,
threshold, or experimental-mode setting.

## Integration and reference dates

`temporal_reasoning.py` uses only Python standard libraries. The existing
`build_explanation()` adds its output under `temporal`. The app supplies the UTC
date at explanation rendering as the claim reference and displays it explicitly.
The diagnostic module never reads the clock, credentials, models, pilot data,
evaluation holdouts or network. A caller can provide a fixed reference date:

```python
from temporal_reasoning import temporal_evidence_analysis
analysis = temporal_evidence_analysis(claim, retrieved_results,
                                      reference_date="2026-11-02")
```

Without an exact supplied reference date, relative expressions remain unresolved.
Evidence wording such as “today” has a separate anchor: it stays unresolved unless
the source record explicitly supplies `temporal_reference_date`. Publication,
update and retrieval timestamps do not automatically anchor quoted relative text.

## Representation and classification

The returned object contains `claim`, `sources`, a combined `warnings` list,
`diagnostic_only: true`, and limitations. Each expression records its exact text
and character offsets, kind, role, status, precision, and an interval when
resolvable. Year/month boundaries represent precision, not an assertion of a
specific event day. Supported formats include ISO dates/timestamps, English named
months, calendar years and year ranges. Slash dates remain ambiguous because no
day/month locale is assumed. Invalid dates are not repaired or re-extracted as
valid years.

Primary classification uses this documented priority when cues overlap:
future/prediction, current status, historical, relative, explicit date/year, then
timeless candidate. All detected facets remain available. For example, “opened
last year” is primarily historical and also relative. Historical verbs and a
small set of changing-status role phrases are lexical heuristics. A present-tense
scientific statement is not automatically called time-sensitive. The fallback
label means no supported temporal cues were found; it does not prove timelessness.

Relative calendar years/months are resolved against the supplied date. Calendar
weeks run Monday–Sunday. “Recently”, “soon”, vague durations and seasons stay
unresolved rather than assigning an arbitrary interval or hemisphere.

## Date separation and review warnings

Sources preserve these separate channels:

| Channel | Input | Interpretation |
|---|---|---|
| Publication | `published_date` | Original publication metadata, if supplied |
| Update | `updated_date` or `last_updated` | Explicit update metadata, if supplied |
| Event | `event_date` | Explicitly supplied event metadata, never inferred from publication |
| Text mention | Dates found in `content` | Mentioned dates; event identity is unverified |

Dates explicitly introduced by “published” or “updated” inside text are tagged
as publication/update mentions and are not used as candidate event periods.
Otherwise dates mentioned in text are tentative comparison periods. This limited
association can fail on complex sentences; no semantic event coreference is
performed. When explicit event metadata exists, it takes precedence, with a
warning if the text's dates are disjoint.

Warnings cover disjoint claim/evidence periods, pre-period publication, older
evidence for current status, prediction/intent versus confirmed outcome,
conflicting event metadata, and disjoint periods across sources. The last case
is a request to check event identity, not proof of a factual contradiction.
“Older” means an earlier calendar year than the supplied current reference,
not a validated source freshness policy. Missing, malformed and ambiguous
metadata produce informational notices, not falsehood judgments. A recent update
does not erase older underlying event dates; a recent publication can legitimately
discuss an older event.

The current Tavily adapter supplies publication metadata and text, but does not
return update/event fields. The diagnostic supports those optional fields when
available; it normally reports them as missing for live retrieval. No adapter
or production NLI filter was changed. The older production year/context checks
remain separate, so diagnostics can disagree with their filtering decisions.

All dynamic source text is displayed with Streamlit plain text. The existing
escaped highlight mechanism remains in the explanation panel.

## Separate challenge set and reproducibility

`evaluation/temporal_challenge.json` contains **25 synthetic developer-authored
claims and 26 constructed evidence records**. These are not real source citations,
independent annotations, pilot records, training data or a blind benchmark. Each
case has an ID, challenge category, supplied reference date (or null), exact
claim, expected primary classification, expected claim-expression strings,
rationale, and evidence. Each evidence record has a developer-authored
`expected_mismatch` boolean. Sources contain no public citation URLs.

Here “mismatch” means **a temporal concern warranting review**, including a
pre-event publication or an unconfirmed future plan; it does not mean evidence
was proven wrong. Informational missing-date notices are excluded. The binary
metric counts a source as positive when any code in `MISMATCH_CODES` is emitted.
Multiple warnings from one source do not create multiple observations. Global
cross-source observations are reported separately from per-source metrics.

Run without any model or API:

```sh
.venv/bin/python -m evaluation.evaluate_temporal
```

Use `--output path/to/new_report.json` to save a new report. The command refuses
to overwrite an existing file. It only opens this separate challenge set and
never loads either existing holdout. The report provides per-class counts,
precision, recall, F1 and a confusion matrix. Macro-F1 averages classes present
in expected labels; undefined values are JSON `null`.

Expression detection compares exact strings and occurrence counts in claims
only; it does not score source-expression extraction or normalized interval
correctness. Date resolution has separate deterministic unit tests. Classification
accuracy uses one primary label per claim. Mismatch precision/recall uses one
observation per evidence record. The timeless false-positive warning rate uses
expected timeless claims, excluding missing-date informational notices.

## Measured preliminary results — 2 November 2026

Actual output is preserved in
[`temporal_challenge_2026-11-02.json`](../evaluation/results/temporal_challenge_2026-11-02.json).

| Measurement | Result | Denominator |
|---|---:|---|
| Primary classification accuracy | 0.960 | 24/25 claims |
| Classification macro-F1 | 0.921 | 6 expected classes |
| Claim-expression precision / recall / F1 | 0.947 / 1.000 / 0.973 | 18 TP, 1 FP, 0 FN |
| Temporal concern precision / recall | 1.000 / 1.000 | 7 positives, 19 negatives |
| Warnings on expected timeless claims | 0.000 | 0/4 claims |

Expected class counts are historical 11, current status 5, relative 2, future 2,
explicit 1 and timeless candidate 4. There are too few examples per class for
reliable generalization. The false positive is the number **2020** in “The array
contains 2020 samples.” It was treated as a year, producing explicit rather than
timeless classification; no mismatch warning followed. This known ambiguity is
retained and reported rather than masking the evaluation error.

The selected offline suite passed **169 tests** (baseline 125). No live search
or real-model inference was used. The existing urllib3/LibreSSL warning remains.
Neither the annotation suites nor held-out data were used.
Syntax compilation passed for 10 relevant Python files, and `git diff --check`
passed. Streamlit's main page and health endpoint returned HTTP 200; the
temporary server was stopped. Production assessor, pilot and sealed-approval
files matched their pre-change SHA-256 checksums.

## Remaining research limits

Lexical date and tense cues cannot resolve arbitrary event identity, quoted
speech, negation scope, hypothetical time, date locale, quantity-versus-year
ambiguity or historical forecasts reliably. Common current-status wording
outside the documented cue patterns can be missed. Date absence does not imply
temporal compatibility. Dates appearing together do not prove they describe the
same event, and publication-before-event does not itself invalidate a later
updated page. No predictions are promoted to facts.

The challenge was authored alongside the implementation. Its measured performance
describes these fixtures only and is not factual verification accuracy. The next
research step is independently annotated temporal expressions and event links,
with normalized date-resolution labels and broader changing-status/quantity
examples, before considering any effect on production evidence decisions.
