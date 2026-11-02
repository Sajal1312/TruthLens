# TruthLens: baseline versus enhanced diagnostics

## Research objective and conditions

Measure additional diagnostic information and structural explanation coverage while preserving production verdicts. Baseline includes existing reasoning and safeguards; enhanced adds five read-only views. This is not an accuracy-improvement experiment.

Protocol version: 1.0; fixed reference date: 2026-11-02. Network calls: 0. Model inference calls: 0. Experimental guards: off.

## Datasets

| Dataset | Provenance | Claims/cases | Passages/targets |
|---|---|---:|---:|
| development | developer_authored_development | 9 | 13 |
| diagnostics | developer_authored_diagnostics | 37 | 59 |
| temporal | developer_authored_synthetic | 25 | see component denominators |
| independence | developer_authored_synthetic | 19 | see component denominators |
| numerical | developer_authored_synthetic | 36 | see component denominators |
| uncertainty | developer_authored_synthetic_snapshots | 24 | see component denominators |

Versions are exact SHA-256 values in comparison.json. Development/diagnostic sets contain public excerpts and synthetic fixtures with developer labels. Four challenge sets are synthetic. No pilot, independent annotations or held-out data are scored.

## A. Verdict-level results

| Track | N | Baseline / enhanced accuracy | Baseline / enhanced macro-F1 | Selective accuracy | Coverage | Abstention | Equal verdicts |
|---|---:|---|---|---:|---:|---:|---|
| current_rule_development | 9 | 0.778 / 0.778 | 0.292 / 0.292 | undefined / not measured | 0.000 | 1.000 | True |
| archived_nli_development | 9 | 0.889 / 0.889 | 0.644 / 0.644 | 1.000 | 0.111 | 0.889 | True |
| current_rule_diagnostics | 37 | 0.784 / 0.784 | 0.293 / 0.293 | undefined / not measured | 0.000 | 1.000 | True |
| archived_nli_diagnostics | — | NOT MEASURED: Dataset split/SHA-256 differs from the current permitted dataset; Claim/passage counts differ; Claim IDs/order differ | — | — | — | — | — |

Fresh rule-based runs do not measure NLI performance. Archived NLI results are historical replay only, not current inference validation. Identical predictions imply no observed verdict gain. Full per-class precision/recall/F1, gold support, confusion matrices (rows=gold) and errors are stored in JSON. Macro-F1 uses gold-present labels; empty/undefined denominators are null.

## B. Diagnostic quality on existing labeled component fixtures

| Task | Unit / N | Precision | Recall | F1 | False-positive rate |
|---|---|---:|---:|---:|---:|
| Temporal mismatch | evidence / 26 | 1.000 | 1.000 | 1.000 | 0.000 |
| Dependency exact | pairs / 23 | 1.000 | 1.000 | 1.000 | 0.000 |
| Dependency near | pairs / 23 | 1.000 | 0.500 | 0.667 | 0.000 |
| Dependency explicit | pairs / 23 | 1.000 | 1.000 | 1.000 | 0.000 |
| Dependency group | pairs / 23 | 1.000 | 0.900 | 0.947 | 0.000 |
| Numerical mismatch | comparisons / 38 | 1.000 | 0.800 | 0.889 | 0.000 |
| Uncertainty category micro (all labels) | label decisions / 168 | 1.000 | 1.000 | 1.000 | 0.000 |

Temporal classification accuracy: 0.960; unresolved claim-context rate: 0.200.
Numerical comparison macro-F1: 0.896; unresolved: 19/38.
Uncertainty exact category-set accuracy: 1.000; macro-F1 (gold-present categories): 1.000. Absent gold categories: No identified diagnostic issue.
Baseline new-view quality is NOT MEASURED, not zero. Component labels cannot score the unlabeled paired-case diagnostics. Uncertainty scores test declared snapshot mapping only, not detector accuracy or causal faithfulness.

## C. Explanation coverage and ablations

| Track | Existing reasons / claims | Enhanced excerpts / claims with sources | Exact substring containment | Recorded NLI entries |
|---|---|---|---|---:|
| current_rule_development | 9/9 | 9/9 | 13/13 | 0 |
| archived_nli_development | 9/9 | 9/9 | 13/13 | 11 |
| current_rule_diagnostics | 37/37 | 36/36 | 59/59 | 0 |

A selected excerpt is a reading aid, not the model's causal rationale. Missing archived method/limitations are not counted as a baseline defect.

Each measured track has six presentation ablations in JSON. Counts below use the current diagnostic split only; counts are descriptive and overlapping, not accuracy or benefit scores.

| Condition | Visible modules | Required modules | Findings by module | Unresolved by module |
|---|---|---|---|---|
| baseline | none | none | none | none |
| temporal_only | temporal | temporal | temporal: 234 | temporal: 0 |
| independence_only | independence | independence | independence: 1 | independence: 59 |
| numerical_only | numerical | numerical | numerical: 19 | numerical: 12 |
| uncertainty_only | uncertainty | temporal, independence, numerical, uncertainty | uncertainty: 153 | uncertainty: 80 |
| enhanced | explainability, temporal, independence, numerical, uncertainty | explainability, temporal, independence, numerical, uncertainty | explainability: 59; temporal: 234; independence: 1; numerical: 19; uncertainty: 153 | explainability: 0; temporal: 0; independence: 59; numerical: 12; uncertainty: 80 |

Uncertainty-only consumes hidden temporal, independence and numerical views; ablation is presentation-level, not independent algorithm isolation. All conditions use identical cached assessments and stored evidence. More warnings is not automatically better.

## Error analysis

- Temporal t19: timeless_candidate → explicit
- Dependency p04: expected {"exact": false, "explicit": false, "group": true, "near": true}; actual {"exact": false, "explicit": false, "group": false, "near": false}
- Numerical n26: potential_mismatch, potential_mismatch → comparison_unresolved, comparison_unresolved
- Numerical n29: compatible → comparison_unresolved
- Numerical n30: compatible → comparison_unresolved

Rule-based abstentions reflect conservative exact-proposition matching; they are retained as errors when directional developer labels differ. Archived NLI trace gaps remain unknown, not reconstructed from references. Per-case verdict errors and all component outputs are in JSON.

## D. Threats to validity, limitations and next experiment

- Developer-authored labels are not independent human annotations; fixtures were inspected during development.
- All conditions inherit identical frozen production verdicts. Equality is a consistency check, not an accuracy gain.
- Standalone component scores have different denominators and are not pooled or transferred to unlabeled paired cases.
- Output counts and excerpt containment do not establish explanation usefulness, semantic correctness or model faithfulness.
- Presentation ablation caches views; uncertainty consumes upstream diagnostics. This is not isolated algorithm or runtime ablation.
- No real reporting independence is established by pair labels, domains, publisher IDs or dependency warnings.
- No confidence intervals or significance claims: small, dependent convenience samples; undefined metrics are null.
- Partial archived trace projection cannot reproduce every original safeguard or provenance label.
- Current production NLI re-execution: no model inference authorized in this protocol
- Independent human-annotated performance: no completed independent dataset supplied
- Explanation usefulness, comprehension and causal faithfulness: require human judgments
- Live retrieval quality, runtime/memory gains and UI usability: not tested here
- Held-out generalization: protected datasets are not opened or hashed
- Five imported unannotated pilot claims: collection progress only, excluded from scoring

Human-validated findings: NOT MEASURED. Next: complete independent annotations and randomized, counterbalanced baseline/enhanced explanation ratings (usefulness, correct attribution, warning relevance, comprehension and review time), with adjudication and blinded model output. Freeze the protocol before final testing. Do not tune against protected test data.

Reproduce: `.venv/bin/python -m evaluation.compare_systems --output-dir evaluation/results/comparison_NEW_RUN`. The destination must not exist. JSON is deterministic for identical inputs/code/Python; no wall-clock timing is scored.
