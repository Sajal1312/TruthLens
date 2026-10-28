# TruthLens safety robustness comparison — 2026-10-27

## Scope and safeguards

This offline run uses the pinned local NLI model and fixed passages only. It did not call Tavily, read API configuration, or evaluate either holdout file. The development set has 9 claims and 13 passages. The visible developer-authored diagnostic set has 16 claims and 34 passages; many entries are synthetic, and none are a blind benchmark. Metrics describe these selected fixtures only.

The unchanged assessment thresholds are confidence `0.70`, margin `0.15`, and two distinct directional URLs. Source metadata is not proof of source independence. The diagnostic source fixtures do not establish real-world reporting independence.

Before editing, the existing full suite reproduced at **85 passed**. At that point, the 9-case development split measured production accuracy `0.889`, macro-F1 `0.644`, coverage `0.111`; the then-current 7-case diagnostic split measured production `0.286 / 0.148 / 0.000` and experimental `0.857 / 0.886 / 0.571` for accuracy / macro-F1 / coverage. The diagnostic set was then expanded to 16 cases, so those old seven-case values are not directly comparable to the 16-case run below. The original seven cases were re-run separately on the final code: production `0.286 / 0.148 / 0.000`; experimental `0.857 / 0.886 / 0.571` (same metric order). This confirms the negated-claim disagreement remains an abstention in experimental mode.

## Reproducible commands

```sh
./.venv/bin/python -m pytest -q
./.venv/bin/python -m evaluation.run_evaluation --split development
./.venv/bin/python -m evaluation.run_evaluation --split diagnostics
PYTHONPYCACHEPREFIX=/tmp/truthlens-pycache ./.venv/bin/python -m compileall -q app.py verifier.py nli_assessor.py evidence_quality.py evaluation tests
```

The evaluation runner forces Hugging Face offline mode. It emits no Tavily request. The model revision used was `03d06b2f6f06023bd596151a16477e2fcec601fb`.

## Claim-level comparison

Confusion matrices use gold labels as rows and predictions as columns, ordered Supported, Contradicted, Inconclusive. Macro-F1 averages the F1 of all three verdict labels, including labels with no predicted examples (their F1 is zero). Coverage is the share of claims receiving a directional verdict.

### Development (9 claims)

| Path | Accuracy | Macro-F1 | Coverage | Abstention | False directional on gold Inconclusive |
|---|---:|---:|---:|---:|---:|
| Production default | 0.889 | 0.644 | 0.111 | 0.889 | 0 |
| Experimental semantic | 1.000 | 1.000 | 0.222 | 0.778 | 0 |

Development confusion matrices, rows gold → columns prediction:

Production:

| Gold \ Predicted | Supported | Contradicted | Inconclusive |
|---|---:|---:|---:|
| Supported | 1 | 0 | 0 |
| Contradicted | 0 | 0 | 1 |
| Inconclusive | 0 | 0 | 7 |

Per-class precision / recall / F1, development:

| Path | Supported | Contradicted | Inconclusive |
|---|---|---|---|
| Production | 1.000 / 1.000 / 1.000 | n/a / 0.000 / 0.000 | 0.875 / 1.000 / 0.933 |
| Experimental | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 |

Experimental:

| Gold \ Predicted | Supported | Contradicted | Inconclusive |
|---|---:|---:|---:|
| Supported | 1 | 0 | 0 |
| Contradicted | 0 | 1 | 0 |
| Inconclusive | 0 | 0 | 7 |

The sole production miss is `dev_reverse_motion_contradiction` (abstained); the experimental path classifies it directionally.

### Developer-authored diagnostics (16 claims)

| Path | Accuracy | Macro-F1 | Coverage | Abstention | False directional on gold Inconclusive |
|---|---:|---:|---:|---:|---:|
| Production default, before guard | 0.500 | 0.222 | 0.063 | 0.938 | 1 |
| Production default, after guard | 0.563 | 0.240 | 0.000 | 1.000 | 0 |
| Experimental semantic, before guard | 0.875 | 0.859 | 0.438 | 0.563 | 1 |
| Experimental semantic, after guard | 0.938 | 0.945 | 0.375 | 0.625 | 0 |

The “before guard” rows are a same-dataset run immediately before the safety fix, not a blind comparison. They show the effect of this narrow double-negation guard on these 16 known cases. The decrease in experimental coverage is intentional: the uncertain case is now rejected instead of receiving a directional label.

Production confusion matrix after guard:

| Gold \ Predicted | Supported | Contradicted | Inconclusive |
|---|---:|---:|---:|
| Supported | 0 | 0 | 5 |
| Contradicted | 0 | 0 | 2 |
| Inconclusive | 0 | 0 | 9 |

Experimental confusion matrix after guard:

| Gold \ Predicted | Supported | Contradicted | Inconclusive |
|---|---:|---:|---:|
| Supported | 4 | 0 | 1 |
| Contradicted | 0 | 2 | 0 |
| Inconclusive | 0 | 0 | 9 |

Experimental per-class precision / recall / F1 after guard:

| Class | Gold count | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Supported | 5 | 1.000 | 0.800 | 0.889 |
| Contradicted | 2 | 1.000 | 1.000 | 1.000 |
| Inconclusive | 9 | 0.900 | 1.000 | 0.947 |

Production per-class precision / recall / F1 after guard:

| Class | Gold count | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Supported | 5 | n/a | 0.000 | 0.000 |
| Contradicted | 2 | n/a | 0.000 | 0.000 |
| Inconclusive | 9 | 0.563 | 1.000 | 0.720 |

The single experimental miss is `diag_negated_reverse_relation`: the two passage-level model outputs conflict, so the system remains Inconclusive instead of forcing the expected Supported result. Its annotation is developer-authored, and should not be treated as evidence that the model should be tuned to this claim.

## Passage-level results (experimental effective labels)

These metrics are distinct from claim-level verdict metrics. Effective labels include the conservative context/relevance adjustments and map excluded or uncertain passages to `NOT ENOUGH INFORMATION`.

| Split | Passages | Accuracy | Macro-F1 | Gold support counts |
|---|---:|---:|---:|---|
| Development | 13 | 0.846 | 0.839 | Supports 6; Contradicts 4; Not enough information 3 |
| Diagnostics | 34 | 0.824 | 0.804 | Supports 19; Contradicts 7; Not enough information 8 |

Diagnostic effective-stance confusion matrix, rows gold → columns prediction (`SUPPORTS`, `CONTRADICTS`, `NOT ENOUGH INFORMATION`):

| Gold \ Predicted | Supports | Contradicts | Not enough information |
|---|---:|---:|---:|
| Supports | 15 | 1 | 3 |
| Contradicts | 0 | 5 | 2 |
| Not enough information | 0 | 0 | 8 |

Diagnostic relevance matrix, rows gold → columns prediction (`relevant`, `weakly_related`, `unrelated`):

| Gold \ Predicted | Relevant | Weakly related | Unrelated |
|---|---:|---:|---:|
| Relevant | 32 | 0 | 0 |
| Weakly related | 0 | 2 | 0 |
| Unrelated | 0 | 0 | 0 |

Diagnostic relevance labels: 32 relevant, 2 weakly related, 0 unrelated. Therefore, an `unrelated` class score cannot be estimated. The relevance metrics are especially weak evidence because the sample is tiny and deliberately constructed.

For diagnostic tags, all covered classes except `negation` receive the expected experimental final verdict in this run. The `negation` tag contains two claims: the singly negated claim abstains on conflicting NLI labels, while the double-negated claim now abstains by design. Duplicate/syndicated, historical, stale-year, irrelevant-overlap, conflicting-source, component-conflict, and active/passive relation probes return their annotated Inconclusive or Contradicted results in the experimental path. Single-case category scores are only pass/fail observations, not meaningful estimates.

Selected category hit counts (correct final verdicts / claims tagged; overlapping tags are counted in each category):

| Category | Production after guard | Experimental after guard |
|---|---:|---:|
| Compound named entities | 0 / 2 | 2 / 2 |
| Independent clauses | 0 / 1 | 1 / 1 |
| Negated single relation | 0 / 1 | 0 / 1 |
| Double negation | 1 / 1 | 1 / 1 |
| Reversed relation | 1 / 4 | 3 / 4 |
| Active/passive reversal | 0 / 1 | 1 / 1 |
| Partial compound evidence | 1 / 1 | 1 / 1 |
| Conflicting passages/components | 2 / 2 | 2 / 2 |
| Historical attribution | 1 / 1 | 1 / 1 |
| Stale-year evidence | 1 / 1 | 1 / 1 |
| Duplicate/syndicated passages | 1 / 1 | 1 / 1 |
| Irrelevant lexical overlap | 1 / 1 | 1 / 1 |
| Conflicting sources/components | 2 / 2 | 2 / 2 |
| Missing publisher metadata (synthetic) | 0 / 1 | 1 / 1 |

The development split also contains one hypothetical case; both paths abstain correctly on it (1 / 1).

## Defect and change

A double-negated motion claim (`The Sun does not not revolve around the Earth.`) received a high-confidence raw `CONTRADICTS` model label on two reverse-motion passages. Before the fix, the experimental override handled double negation only inside the model-`SUPPORTS` branch; the raw `CONTRADICTS` label bypassed it and produced a false directional verdict. The production path also produced that false directional verdict.

A narrow fail-safe now detects multiple surface negation cues on an explicitly parsed motion relation before either path can count a directional passage. It marks such passages uncertain and leaves the claim Inconclusive. It does not attempt to interpret the scope of double negation. The production path therefore has one justified behavior change: this ambiguous case now abstains. Thresholds, model, and experimental opt-in status are unchanged.

## Test and integrity notes

The complete suite passed **96 tests**. Python syntax compilation passed. One environment warning remains: urllib3 reports that this Python build uses LibreSSL 2.8.3 rather than OpenSSL 1.1.1+. No live search, UI launch, or API-key validation was performed for this task.

Neither `evaluation/data/held_out.jsonl` nor `evaluation/data/held_out_inspected_diagnostic.jsonl` was evaluated or edited. Their final SHA-256 values were respectively:

- `held_out.jsonl`: `d9b9a974d16973b8fbccaa311ddde72325ae8e08ce3a4414cd5aa4fed234defa`
- `held_out_inspected_diagnostic.jsonl`: `07c77096af2e60f03a09edc2c1b6fd59d9ccb5af51c97e1782e03a9bf099e07e`

## Limitations and next step

These are small, purpose-selected diagnostics, not estimates of real-world performance. The system remains limited by model errors, simplistic claim splitting, surface negation detection, snippet context loss, and the fact that URL or publisher diversity does not prove independent sourcing. Keep the NLI model's scores separate from truth probabilities. Next, collect a larger independently annotated dataset, have a second annotator label passage relevance and stance, resolve disagreements before evaluation, and reserve a new unseen test split before tuning further.
