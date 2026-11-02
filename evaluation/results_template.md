# TruthLens evaluation report

- Evaluation date:
- Code revision:
- Model ID and pinned revision:
- Split: development / diagnostics / final_test
- Search requests made: **No** (offline harness)
- Dataset version / checksum:
- Resource benchmark repeats / probe cases:

## Status

**NOT MEASURED** until the offline runner completes with the locally cached NLI model. Do not fill in predicted metrics from expected labels.

## Counts and results

| Metric | Measured result | Sample count | Interpretation / uncertainty |
|---|---:|---:|---|
| Gold final verdict counts | Not measured | — | Include Supported / Contradicted / Inconclusive |
| Predicted final verdict counts | Not measured | — | Report separately from gold counts |
| Final verdict accuracy / macro-F1 | Not measured | — | State labels included in macro-F1 |
| Final verdict per-class precision / recall / F1 | Not measured | — | Include support and undefined values |
| Final verdict confusion matrix | Not measured | — | Rows: gold; columns: predicted |
| Passage relevance per-class metrics / macro-F1 | Not measured | — | Relevant / weakly related / unrelated |
| Raw NLI stance per-class metrics / macro-F1 | Not measured | — | Raw model labels and their own denominator |
| Effective passage stance per-class metrics / macro-F1 | Not measured | — | After filtering and abstentions |
| Passage stance confusion matrices | Not measured | — | Keep raw and effective matrices separate |
| Selective accuracy | Not measured | — | Exact verdict match among directional predictions |
| Coverage / abstention rate | Not measured | — | Report counts and denominator |
| Missing / unadjudicated annotations | Not measured | — | Exclude from gold metrics and disclose |
| Claim verdict inter-annotator agreement | Not measured | — | Raw agreement and Cohen's kappa before adjudication |
| Evidence relevance / stance agreement | Not measured | — | Separate agreement per label task |

## Aggregation comparison

| Mode | Accuracy | Macro-F1 (gold-supported labels only) | Coverage | Abstention | Errors |
|---|---:|---:|---:|---:|---:|
| Production default | Not measured | Not measured | Not measured | Not measured | Not measured |
| Experimental semantic path | Not measured | Not measured | Not measured | Not measured | Not measured |
| Experimental quantifier abstention guard | Not measured | Not measured | Not measured | Not measured | Not measured |
| Experimental future-intent abstention guard | Not measured | Not measured | Not measured | Not measured | Not measured |

Production verdict behavior is the reference. Experimental modes are
post-hoc evaluator outputs; publisher IDs do not establish independent
reporting. Note missing or malformed metadata and errors grouped by case tags.

## Resource usage

| Measurement | Measured result | Conditions / limits |
|---|---:|---|
| Model loading time | Not measured | Local cache only |
| Inference latency: median / mean | Not measured | State repetitions and device |
| Peak process RSS | Not measured | Includes Python and model loading; not inference-only |
| Energy | **Not measured** | No reliable telemetry available |

## Stress groups

| Group | Case count | Passage count | Result |
|---|---:|---:|---|
| Historical | Not measured | Not measured | — |
| Hypothetical | Not measured | Not measured | — |
| Irrelevant | Not measured | Not measured | — |
| Conflicting | Not measured | Not measured | — |
| Duplicate | Not measured | Not measured | — |
| Date-sensitive | Not measured | Not measured | — |

## Limitations and deviations

Record model/cache errors, skipped cases, disagreements between raw and effective labels, and why the results do not support broad accuracy claims.
