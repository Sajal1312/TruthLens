# Baseline versus enhanced diagnostics: research protocol

This evaluation measures what the five diagnostic views add to a frozen
TruthLens assessment. It does **not** test a different verification algorithm.
Production decisions, NLI revision, safeguards, confidence 0.70, margin 0.15
and minimum two qualifying directional sources remain unchanged. Distinct
passages/URLs are not proof of independent original reporting.

## Reproduce

From the project folder, run:

```sh
.venv/bin/python -m evaluation.compare_systems --output-dir evaluation/results/comparison_NEW_RUN
```

Choose a new destination each time; existing reports are never replaced.
The directory receives `REPORT.md` and `comparison.json`. No extra package,
API key, model loading, model inference, Tavily request or network connection
is required. The runner actively blocks network calls and NLI entry points.
It does not read secret configuration, pilot records, approvals or protected
evaluation datasets. It accepts no arbitrary dataset path or split argument.

`evaluation/comparison_protocol.json` defines protocol version 1.0, a fixed
reference date, dataset provenance, six conditions and unmeasured outcomes.
The reference date is an analysis anchor, not a publication/event/access date.
Each input, archive and relevant Python module has a SHA-256 fingerprint in
the output. The dataset SHA is its exact version. Reports omit wall-clock
timestamps and are deterministic for identical files and Python version.

## Conditions and execution tracks

**Baseline** retains the existing production verdict, source/component trace,
reason, method and limitations. It already has explanations and safeguards.
**Enhanced** adds explainability excerpts, temporal analysis, dependency
analysis, numerical/quantifier analysis and uncertainty summaries. Excerpts
are deterministic reading aids, not internal model rationales. Raw NLI labels,
effective passage assessments and final verdicts remain separate fields.

The production assessment is calculated or loaded once. Both conditions use
the same original claim, ordered passages and frozen assessment. The evaluator
checks that diagnostics do not mutate evidence, assessment or verdict. Gold
labels are used only by scoring functions, never passed to the assessor.

There are two distinct execution tracks, never pooled:

1. **Current production rule-based mode:** call `verifier.assess_evidence` on
   the current development and diagnostic records. This is fresh execution
   of a supported app mode; its results do not measure the NLI model.
2. **Archived production NLI replay:** use only the saved production fields
   from an explicitly allowed report if the split, exact dataset SHA, ordered
   claim/evidence identities, counts, model revision and thresholds match.
   Stale reports are **NOT MEASURED**; no convenient subset is selected. The
   matching development archive has 9 cases. The old 7-case diagnostic archive
   does not match today's 37-case file and is rejected. No model is rerun.

The archive lacks the original source relevance strings, method, limitations,
some component summaries and historical code fingerprints. Those remain
unavailable; the evaluator projects only the saved production trace and marks
missing fields unknown. Enhanced diagnostics on this projection are not a
complete reproduction of the historical UI. Current NLI performance requires
a separately authorized, versioned inference experiment. The older
`run_evaluation.evaluate_cases` is **not** invoked because it also runs
experimental semantic and guard conditions outside this protocol.

## Dataset inventory and independence

| Input | Role | Label provenance |
|---|---|---|
| `data/development.jsonl` | 9 development claims, 13 passages | Developer labels; saved public excerpts mixed with synthetic passages |
| `data/diagnostics.jsonl` | 37 inspected claims, 59 passages | Developer diagnostic labels; not a blind benchmark |
| `temporal_challenge.json` | 25 cases, 26 evidence records | Developer-authored synthetic expectations |
| `independence_challenge.json` | 19 cases, 40 source entries, 23 labeled pairs | Synthetic dependency expectations; not verified reporting chains |
| `numerical_challenge.json` | 36 cases, 36 evidence records, 38 comparison targets | Synthetic numerical/scope expectations |
| `uncertainty_challenge.json` | 24 snapshots, 37 source entries | Declared synthetic diagnostic/decision projections; tests mapping only |

The six explicit permitted paths are checked against a fixed allowlist. The
two protected held-out files are neither opened nor hashed. Their scores,
contents and sample counts are not used in this comparison. Development and
diagnostics were inspected during implementation and cannot support claims of
independent generalization. Source checks recorded in existing fixtures are
not refreshed by this offline run.

No independent human-annotated evaluation dataset is supplied here. The five
imported unannotated pilot claims represent collection progress; human approval
for inclusion is not a gold stance/verdict annotation. The pilot is excluded
from scoring. Existing synthetic `.invalid` identifiers remain explicitly
synthetic adapter identifiers, never real source citations.

## Metrics and denominators

Reuse `evaluation.metrics` and the four existing component evaluators.
Never add their denominators or treat component scores as paired-case scores.

| Metric | Definition / eligible labels |
|---|---|
| Verdict accuracy | Correct final labels / cases with both reference and prediction |
| Per-class precision, recall, F1 | `TP/(TP+FP)`, `TP/(TP+FN)`, harmonic mean; supports and confusion matrix included |
| Macro-F1 | Mean F1 across labels present in gold, including zero for a present but missed class; included/absent labels disclosed |
| Selective accuracy | Correct verdicts / directional predictions with reference labels |
| Coverage / abstention | Directional / available predictions; Inconclusive / available predictions |
| Explanation coverage | Nonempty original explanation fields and enhanced excerpt availability; recorded fields have their own denominators |
| Excerpt containment | Selected nonempty excerpts found as exact substrings / selected nonempty excerpts |
| Diagnostic quality | Precision/recall/F1 on each existing task's own labeled units: temporal evidence, dependency pairs, quantity comparisons, uncertainty categories |
| Warning false-positive rate | `FP/(FP+TN)` for the stated positive warning and its own eligible negative targets |
| Unresolved rate | Numerical unresolved comparisons / all comparisons; temporal cases with unresolved claim expressions / all temporal cases; no pooled cross-module rate |
| Uncertainty quality | Exact category-set accuracy plus per-label and micro/macro metrics; labels can overlap |

Missing references are never converted to Inconclusive. Scoring helpers count
missing gold and predictions and exclude incomplete pairs. Prediction coverage
over all available predictions is separate from selective scoring on labeled
pairs. Existing JSONL fixtures have required developer labels; the runner does
not silently import unannotated pilot records into that format. Empty or
undefined quantities are JSON `null`, not zero or perfect performance. With
zero paired cases, verdict equality is unknown rather than vacuously true.
Unrecorded archive explanation fields are unknown rather than missing app
features. Confusion matrices use rows = gold, columns = prediction.

The baseline has no new diagnostic views by definition. Their quality is
**NOT MEASURED** for baseline, not precision/recall zero. Existing production
safeguards still operate. Structural containment is not semantic evidence
selection correctness, usefulness, comprehension or causal faithfulness.
Those outcomes need independent human judgments and remain **NOT MEASURED**.
The uncertainty attribution check tests a structural contract (verbatim
recorded reason, no invented causal claims), not faithful model reasoning.
No NLI confidence is interpreted as a probability of truth.

## Ablation interpretation

The six conditions expose baseline only, temporal only, independence only,
numerical only, uncertainty only, or all five views. Each condition retains
identical verdicts and stored evidence. The runner computes a shared view
cache once per case and masks which views are presented. It reports visible
and required modules, cases with findings, findings and unresolved items with
their units. Singleton provenance groups are not dependency findings.

Uncertainty summarizes temporal, independence and numerical diagnostics, so
its upstream views remain required even when hidden. This is a **presentation
ablation**, not independent algorithm isolation or a speed benchmark. Warning
counts overlap; missing-date notices are included in descriptive temporal
counts. More warnings do not imply better performance. Baseline/enhanced
warning usefulness on paired claims cannot be scored without corresponding
annotations. Component fixture scores are separate supporting measurements.

## Error analysis and threats to validity

The generated report retains wrong predictions and unresolved comparisons,
lists component errors and records per-case raw/effective assessment traces.
Do not alter production logic or challenge labels to improve this report.
Small, clustered, developer-authored convenience samples are susceptible to
selection bias, correlated cases and label/implementation coupling. No
significance test, independent accuracy, real source independence, retrieval
quality, runtime improvement or UI validation is established.

Recommended next experiment: collect two independent annotations, adjudicate
without replacing originals, freeze the protocol, and conduct a randomized,
counterbalanced baseline/enhanced explanation study. Obtain blinded ratings
for evidence-selection correctness, warning relevance, explanation usefulness
and comprehension, plus measured review time. Keep diagnostic category labels
separate from claim verdicts. Report inter-annotator agreement and uncertainty
before making general usefulness claims; keep protected test data untouched.

## Report-ready methodology

“A paired offline comparison held the production claim assessment and stored
evidence constant while varying the diagnostic views presented. Current
rule-based assessments and checksum-matched archived production NLI outcomes
were analyzed separately. Four existing developer-authored challenge sets
measured component behavior using their own label units. Verdict performance,
structural explanation coverage and diagnostic warning quality were reported
separately, with explicit missing-label and abstention denominators. The
diagnostics did not change verdicts. Results are preliminary synthetic and
developer-labeled findings; human usefulness and independent generalization
were not measured.”
