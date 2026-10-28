# TruthLens evaluation report

- Evaluation date:
- Code revision:
- Model ID and pinned revision:
- Split: development / held_out / all
- Search requests made: **No** (offline harness)
- Dataset version / checksum:
- Resource benchmark repeats / probe cases:

## Status

**NOT MEASURED** until the offline runner completes with the locally cached NLI model. Do not fill in predicted metrics from expected labels.

## Counts and results

| Metric | Measured result | Sample count | Interpretation / uncertainty |
|---|---:|---:|---|
| Expected final verdict class counts | Not measured | — | — |
| Final verdict macro-F1 | Not measured | — | Pilot only |
| Final verdict confusion matrix | Not measured | — | Rows: expected; columns: predicted |
| Relevance macro-F1 | Not measured | — | Classes: relevant / weakly related / unrelated |
| Raw NLI stance macro-F1 | Not measured | — | Raw model outputs only |
| Effective stance macro-F1 | Not measured | — | Includes downstream abstentions |
| Selective accuracy | Not measured | — | Directional predictions only |
| Coverage | Not measured | — | Supported/Contradicted fraction |
| Abstention rate | Not measured | — | Inconclusive fraction |

## Aggregation comparison

| Mode | Accuracy | Macro-F1 (gold-supported labels only) | Coverage | Abstention | Errors |
|---|---:|---:|---:|---:|---:|
| Production default | Not measured | Not measured | Not measured | Not measured | Not measured |
| One vote per normalized publisher | Not measured | Not measured | Not measured | Not measured | Not measured |
| Distinct declared publishers only | Not measured | Not measured | Not measured | Not measured | Not measured |

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
