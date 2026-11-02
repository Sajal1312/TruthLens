# Numerical and Quantifier Intelligence — diagnostic mode

Open **Why did TruthLens reach this verdict? → Numerical and Quantifier
Analysis**. The section shows extracted claim/evidence quantities, normalized
intervals, claim-to-evidence quantity references, compatible comparisons,
potential mismatches, unresolved comparisons and quantifier warnings. All
dynamic content is rendered as plain text. No numerical output changes a vote,
verdict, model threshold or experimental setting.

## Integration and reuse

`numerical_reasoning.py` is called only by the explanation layer. It reads
retrieved text and optional explicit source time metadata. It never searches,
loads a model, reads a credential or accesses annotations/holdouts.

Quantifier extraction directly reuses `nli_assessor._QUANTIFIER_SCOPE_CUES`, the
exact pattern used by the existing experimental guard. Negation context uses
the existing `_CLAUSE_NEGATION` pattern. The display adapter distinguishes
universal, existential, negative, negated-universal, negated-existential and
cardinal-comparator uses; it does not implement another abstention guard.
The production assessor and its guard defaults are unchanged.

Temporal expression extraction and metadata date parsing reuse
`temporal_reasoning.py`. Calendar dates/years stay separate from measurements.
An immediately recognized unit or count noun disambiguates a year-shaped number
such as **2020 samples** locally. This does not rewrite the existing temporal
panel or its known quantity/year ambiguity.

`build_explanation()` returns the additional view under `numerical`, preserving
all original assessment data. Source IDs, links, snippets and model inputs remain
unchanged. The app uses the same supplied UTC reference date as the temporal panel.

## Extraction and normalization

The extractor records exact text/offsets, status/reason, comparator, approximation
flag, original unit, normalized dimension/unit, lower/upper bounds, open/closed
boundaries, tolerance and a local context frame. It supports:

- Digit-based integers, signed decimals and Unicode minus; English thousands
  grouping such as `1,000`. An unspecified comma decimal such as `1,5` is unresolved.
- Inclusive ranges using `between … and`, `from … to`, hyphens/en dashes and `to`,
  including compatible mixed-unit endpoints.
- `greater than`, `less than`, `at least`, `at most`, equivalent symbols and
  selected `no more/fewer/less than` variants. Open bounds stay open.
- `about`, `roughly`, `approximately` and `around`. Approximate inequalities and
  ambiguous nested comparator/range scope remain unresolved.
- Percentages and percentage points as separate dimensions. No baseline-free
  conversion is made between relative percentage change and percentage-point change.
- Kilometers/meters → meters; kilograms/grams → kilograms; Celsius/Fahrenheit →
  Celsius. Celsius/Fahrenheit conversion is affine, not just multiplication.

Unsupported units/magnitudes, currency, compound/powered units, reversed ranges,
and ambiguous formatting remain visible as unresolved quantities. Missing
numbers are not converted to zero or treated as contradictions. Number words
such as “ten” are not currently extracted. Count integrality, nonnegativity and
physical domain constraints are not inferred; intervals are a real-valued
arithmetic diagnostic, not a cardinality or physics validator.

## Explicit approximation policy

For an approximate value, use a symmetric normalized interval with radius:

`max(0.02 × absolute normalized magnitude, absolute floor)`.

For ranges, magnitude is the larger absolute endpoint. Temperature uses only
the absolute floor, because percentages of a Celsius coordinate are not a
meaningful physical uncertainty model.

| Dimension | Absolute floor in normalized units |
|---|---:|
| Dimensionless/count | 1 |
| Length | 0.01 m |
| Mass | 0.001 kg |
| Percentage / percentage-point value | 0.5 percentage points |
| Temperature | 0.5 °C, with no relative component |

Thus “about 30%” becomes `[29.4, 30.6]`; “approximately 0°C” becomes
`[-0.5, 0.5]`. These are declared **diagnostic display tolerances**, not scientific
confidence intervals, observed measurement uncertainty, domain standards or NLI
probabilities. They must not be used to justify production verdicts. Domain-specific
tolerances would require evidence and separate validation.

Decimal arithmetic is used internally. A `1e-9` base-unit roundoff allowance
applies only to exact point equality after conversion; it does not relax strict
inequality boundaries. Overlapping sets are compatible, but do not imply that
the evidence establishes the claim. For example, “at least 10” is compatible with
“exactly 10”, while “more than 10” excludes exactly 10.

## Context policy

The module never matches contexts using token overlap. It requires a unique,
complete normalized **wording frame** within a local sentence: the target
quantity becomes a placeholder while all entity/property/population/time words
remain. Other quantities remain as normalized dimension/bound values so a changed
baseline cannot disappear. At least two substantive context words are required;
pronouns, HTML-like markup and linguistic negation prevent an affirmative numeric
comparison. A negative numeric sign is not linguistic negation.

Only one exact candidate frame can match a claim quantity. Paraphrases, property
reordering, other-value changes and missing context can therefore produce false
abstentions. A matched frame is a **same-context candidate**, not independently
verified semantic event identity. “Potential mismatch” always remains conditional
on checking that context; it never means Contradicted.

Dates in each measurement sentence retain their resolved intervals in its frame.
Unresolved local time expressions block comparison. The same “last year” wording
under different supplied reference dates cannot be silently matched. Relative
source expressions require `temporal_reference_date`; retrieval/publication/update
dates do not automatically anchor them. Current-status measurements require a
matching day-precision source time anchor. A year-only event date is insufficient.

Incompatible dimensions remain unresolved. Percent versus percentage points
requires baseline information. Different populations, years or entity/property
wording stay unresolved even when the numbers differ dramatically. Quantifier
warnings preserve “all versus some” and negation scope: some alone neither proves
nor disproves all, and none/no is not automatically converted into a count of zero.

## Separate challenge set and evaluation

`evaluation/numerical_challenge.json` contains **36 synthetic developer-authored
cases, 36 constructed evidence records and 38 comparison targets**. It has no real
source URLs, pilot approvals, independent annotations or gold factual verdicts.
Each case records ID, challenge category, exact claim/evidence text, expected
quantity strings, ordered expected comparison statuses and a rationale.

Statuses are `compatible`, `potential_mismatch` and `comparison_unresolved`.
Expected labels express the authored measurement context. Hard paraphrase and
multiple-changing-value cases retain semantic compatibility/mismatch expectations,
so lexical-frame false abstentions are counted as errors rather than relabeled
to make results better. Number-word “ten” is also an expected quantity despite the
current digit-only extractor.

Run without network or a model:

```sh
.venv/bin/python -m evaluation.evaluate_numerical
```

`--output path/to/new_report.json` saves a report and refuses overwrite. The runner
reads only this separate challenge file. It does not load any existing holdout.
The final measured output is
[numerical_challenge_final_2026-11-02.json](../evaluation/results/numerical_challenge_final_2026-11-02.json).
The earlier `numerical_challenge_2026-11-02.json` report is retained from before
the relative-anchor safety refinement; use the final report for this implementation.

Metrics have separate denominators:

- Exact quantity-string/occurrence precision and recall are computed for claims
  and evidence separately, then pooled. Date exclusions are reflected. Normalized
  interval correctness is checked by unit tests, not this extraction metric.
- Comparison metrics include all 38 authored targets and a three-class confusion
  matrix. An absent comparison maps to unresolved with an explicit missing-output
  flag; it is never silently removed.
- Potential-mismatch recall includes missed mismatches that became unresolved.
  False-positive rate divides false mismatch flags by authored non-mismatches.
- Coverage is the fraction resolved as compatible or potential mismatch.
  Resolved-only accuracy is reported with coverage; it must not be presented
  alone as general accuracy. Undefined metrics are `null`. Macro-F1 averages
  classes present in expected labels; all three are present here.

## Actual preliminary results — 2 November 2026

| Measurement | Result | Counts |
|---|---:|---|
| Quantity extraction precision / recall | 1.000 / 0.986 | 68 TP, 0 FP, 1 FN |
| Potential-mismatch precision / recall | 1.000 / 0.800 | 8 TP, 0 FP, 2 FN |
| False-positive mismatch rate | 0.000 | 0/28 negative targets |
| Three-class accuracy / macro-F1 | 0.895 / 0.896 | 34/38 targets correct |
| Resolved coverage | 0.500 | 19/38 targets |
| Unresolved rate | 0.500 | 19/38 targets |
| Resolved-only accuracy | 1.000 | 19/19 resolved targets |

Expected class counts: compatible 13, potential mismatch 10, unresolved 15.
Four authored comparisons became extra unresolved results: both changing values
in one sentence, a paraphrased property description, and a spelled-out number.
These are small code-adjacent fixtures, not independent benchmark results. The
results do not measure real-world factual verification, NLI truth accuracy or
human comprehension.

The selected suite passed **277 targeted tests** (217 baseline plus 60 added
checks). Tests cover conversions, bounds, approximation, quantifier inventory
reuse, negation, time anchors, ambiguity, HTML-safe rendering and unchanged
rule/NLI verdicts. The existing urllib3/LibreSSL warning remains. No held-out or
annotation suites, live Tavily requests or real-model inference were used.
Syntax compilation passed for 11 relevant Python files, and `git diff --check`
passed. Streamlit's main page and health endpoint returned HTTP 200; the temporary
server was stopped. The final numerical report and previous temporal/provenance
reports reproduced exactly. SHA-256 checks verified 29 protected production,
diagnostic, pilot/import and sealed-approval files were unchanged.

## Remaining research work

Context identity is deliberately narrow and cannot solve coreference, logical
scope, implicit baselines, all measurement domains, number words, rate denominators
or arbitrary units. Unrecognized count nouns can still make year-shaped values
ambiguous. The numerical date disambiguation is local and does not repair the
older temporal classifier. Domain-specific approximation and count constraints
need separate annotations and policy review.

The next step is independently annotated quantity spans, normalized units,
entity/property/population/time links and scope relations across realistic
paraphrases, followed by measured calibration of approximation bands. No existing
pilot records or production evidence rules should be changed based on these
developer-authored scores alone.
