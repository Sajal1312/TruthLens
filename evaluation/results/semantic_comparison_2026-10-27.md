# Semantic assessment experiment — 2026-10-27

The run used the existing cached model and fixed data. No Tavily request was
made. Production uses `experimental_semantic=False` by default. Neither
`held_out.jsonl` nor the preserved inspected holdout was loaded or changed in
these comparisons. The seven-case diagnostics are visible, hand-authored and
partly synthetic; they are not an independent or blind test set.

## Claim-level comparison

Macro-F1 averages the three verdict classes present in each split. Rows in
the confusion matrices below are expected labels and columns are predictions,
ordered Supported, Contradicted, Inconclusive.

| Split / mode | n | Accuracy | Macro-F1 | Coverage | Abstention | Selective accuracy |
|---|---:|---:|---:|---:|---:|---:|
| Development — current | 9 | 0.889 | 0.644 | 0.111 | 0.889 | 1.000 |
| Development — experimental | 9 | 1.000 | 1.000 | 0.222 | 0.778 | 1.000 |
| Diagnostics — current | 7 | 0.286 | 0.148 | 0.000 | 1.000 | Not defined (0 directional predictions) |
| Diagnostics — experimental | 7 | 0.857 | 0.886 | 0.571 | 0.429 | 1.000 |

### Confusion matrices

Development current:

```text
                 predicted
expected       S  C  I
Supported      1  0  0
Contradicted   0  0  1
Inconclusive   0  0  7
```

Development experimental:

```text
                 predicted
expected       S  C  I
Supported      1  0  0
Contradicted   0  1  0
Inconclusive   0  0  7
```

Diagnostics current:

```text
                 predicted
expected       S  C  I
Supported      0  0  4
Contradicted   0  0  1
Inconclusive   0  0  2
```

Diagnostics experimental:

```text
                 predicted
expected       S  C  I
Supported      3  0  1
Contradicted   0  1  0
Inconclusive   0  0  2
```

| Diagnostic expected class | Current P / R / F1 | Experimental P / R / F1 | Support |
|---|---|---|---:|
| Supported | undefined / 0.000 / 0.000 | 1.000 / 0.750 / 0.857 | 4 |
| Contradicted | undefined / 0.000 / 0.000 | 1.000 / 1.000 / 1.000 | 1 |
| Inconclusive | 0.286 / 1.000 / 0.444 | 0.667 / 1.000 / 0.800 | 2 |

The current mode's undefined precision means it made no predictions of the
directional class. These are tiny, selected samples; the scores are useful for
finding behavior differences, not for estimating general accuracy.

## Diagnostic interpretation

- On development, the current path abstained on the one reversed-motion
  contradiction. The model labeled both explicit Earth-around-Sun passages
  SUPPORTS for the opposite Sun-around-Earth claim. The experimental path
  mapped those high-confidence labels to CONTRADICTS after relevance and
  historical/hypothetical/date checks, so the claim became Contradicted.
- In the seven new diagnostics, the experimental path corrected both
  named-entity-list cases and the two-component case. It returned Supported
  only when every separate component had enough evidence. The partial-evidence
  case remained Inconclusive, as did the no-evidence disjunction.
- One synthetic negation case remained Inconclusive because the local model
  gave the two passages conflicting directional labels. The experiment does
  not override that conflict.
- The one real-source reversal diagnostic produced Contradicted in the
  experimental mode and Inconclusive in the current mode. The experiment
  corrects interpretation only when the underlying NLI score still meets the
  unchanged confidence and margin thresholds.
- Experimental publisher grouping results are included in the JSON reports;
  these samples do not show a material difference from the production result.

## Passage metrics and limits

In the diagnostics set, experimental effective passage-stance accuracy was
0.786 (14 passages; macro-F1 0.829), raw model-label accuracy was 0.750 (12
recognized labels; macro-F1 0.429), and relevance accuracy was 1.000 (14
passages). All diagnostic relevance examples are annotated relevant, so that
number says nothing about detecting unrelated evidence. Passage stance uses
the first assessed claim component; the corpus does not yet contain gold
labels for every passage-component pair.

The development and diagnostic JSON reports preserve component assessments,
raw labels, confidence/margin values, and reasons. Model confidence remains a
score for the text-pair classification, not a probability that the claim is
true. Production verdict logic, model, confidence threshold (0.70), margin
threshold (0.15), and two-source requirement were not changed. The result
supports further evaluation of the opt-in path; it does not justify enabling
it by default.
