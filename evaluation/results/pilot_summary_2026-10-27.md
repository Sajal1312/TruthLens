# TruthLens offline pilot summary — 2026-10-27

These are measured local NLI results for the data checksums in the adjacent
JSON reports. No Tavily request or API credential was used. The dataset is
small and manually curated; it is not representative or blinded.

## Development split

- 9 claims, 13 passages; gold verdict counts: Supported 1, Contradicted 1,
  Inconclusive 7.
- Final verdict accuracy: 0.889; macro-F1: 0.644 across all three present
  classes.
- Effective passage stance accuracy: 0.692; raw NLI stance accuracy: 0.727;
  passage relevance accuracy: 0.923.
- Coverage: 0.111; abstention rate: 0.889.
- All three aggregation modes agreed on all 9 cases. The one error was the
  reversed-motion contradiction: both passages explicitly say Earth moves
  around the Sun, but the NLI model labeled them SUPPORTS relative to the
  reverse claim, so the current context safeguard excluded them and returned
  Inconclusive. This is a conservative false abstention and a limitation in
  NLI/context handling; production code was not changed.

## Newly curated exploratory holdout

- 3 claims, 4 passages; one expected case per verdict class.
- Final verdict accuracy: 0.667; macro-F1: 0.556; confusion matrix is in
  `held_out_2026-10-27-exploratory.json`.
- Coverage: 0.333; abstention rate: 0.667; selective accuracy: 1.00 on the
  single directional prediction.
- Passage stance and relevance accuracy were each 1.00 on these four
  passages. These denominators are too small for a reliable performance claim.
- The Mars-two-moons support case returned Inconclusive. Both passages were
  assessed SUPPORTS, but the claim parser split “Phobos and Deimos” into two
  claim components; neither source independently stated the second fragment
  as a standalone proposition, so one component remained inconclusive. The
  other directional case (Mars has three moons) was Contradicted. The private
  event with no evidence was Inconclusive.
- The holdout's sole mismatch is the compound-label claim-part parsing noted
  above; the data labels were not changed after the run.
- Production and both experimental publisher modes had the same result on
  this set. Each directional case had one NASA and one ESA passage, while the
  one no-evidence case had no eligible votes. The grouping experiment thus
  did not reduce coverage on these particular cases.

This holdout was authored by the project developer, its labels are visible,
and it has now been run. It is not blind or unseen. Do not revise the code or
labels to improve these metrics; any change should use a future dataset for
evaluation.

## Resource measurement

- Model: `cross-encoder/nli-deberta-v3-xsmall`, pinned revision recorded in
  `resources_2026-10-27-final.json`.
- Model load: 1.292 seconds; predictor median latency: 10.389 ms over 15 timed
  calls (5 repetitions for each of 3 probes); 3 untimed warm-ups.
- Peak process RSS: 541,671,424 bytes (process high-water mark including
  Python and model load; not inference-only memory).
- CPU inference on Apple arm64, Python 3.9.6. End-to-end verification time
  and energy consumption were **not measured**.

## Interpretation

The development score is inflated by seven inconclusive cases and only one
directional gold label. The holdout demonstrates both a correct contradiction
and a sensible abstention, but also a false abstention caused by claim-part
splitting. Treat these numbers as harness diagnostics. A credible project
evaluation still needs a larger, sampled dataset, independent annotation,
broader domains, and explicit claim-component labels.
