# Pre-collection analysis plan v1

Freeze this plan and the generated bundle before any response is inspected.
The primary endpoint is perceived usefulness; other outcomes are exploratory.
No data/results or power calculation are claimed by this preparation.

1. Validate the response JSON schema, bundle/version, consent, slot and trial
   IDs against the locked private allocation. Reject duplicate slots/trials,
   out-of-range values, condition fields supplied by participants, stale bundles
   and unknown IDs. Decode conditions only from the private allocation.
   Blank templates are not observations. Nonconsenting files are not analyzed.
   Preserve input files; never impute missing ratings or skipped quizzes.
2. Report assigned slots, consenting response files, trials with any response,
   answered/missing fields, and trials by condition. Count missing trials
   against all planned allocations separately from missing answers among
   consenting respondents. Display per-condition rating counts, means and
   medians; Likert means are descriptive, with medians also retained.
3. For each outcome, compute enhanced-minus-baseline condition mean difference
   and each slot's within-person mean difference where both conditions have
   observations. Report the number of eligible slots. These can differ with
   missingness; neither substitutes for a crossed participant/item model.
4. CIs are conditional on this fixed convenience item set. Use percentile
   bootstrap (2,000 repeats, fixed recorded analysis seed) over **complete
   counterbalance blocks**, preserving both slots within each sampled block.
   Only blocks with both real consenting slots and all ratings for that outcome
   enter the CI contrast (mean of within-slot differences). Require at least
   eight complete blocks and nonzero contrast variation; otherwise return null
   with the reason. This conservative reporting rule is not a power guarantee.
   Do not resample individual trials as independent people. Do not extrapolate
   these CIs to other claims/populations. No significance test or confirmatory
   multi-outcome claim is planned; missingness and multiplicity are disclosed.
5. Score objective reason/limitation accuracy only after independent key review
   tied to the exact key SHA. Include answered denominators and missing counts.
   For limitation answers with confidence, compute Brier score
   `mean((confidence/100 - correctness)^2)` and mean confidence versus accuracy
   by condition. Lower Brier is task-specific calibration, not truth confidence.
   Subjective willingness to rely is reported separately; do not call high trust
   an improvement or subjective usefulness factual correctness. The repeated
   literacy questions can cause learning/ceiling effects.
6. Report optional time only for explicitly recorded, uninterrupted facilitator
   stopwatch measurements. Exclude null, interrupted and unverified timing.
   This is a separate descriptive outcome; no automated latency claim is made.
7. No responses means **Study not yet conducted**, with null estimates and
   participant count zero. Unreviewed keys mean objective results **NOT MEASURED**.
   Do not generate participant responses to fill any report or validate a desired
   effect. Synthetic unit-test responses stay in pytest temporary fixtures only.

Limitations: convenience recruitment, small size, all-Inconclusive rule-mode
items, mixed synthetic/public evidence, partial blinding, length differences,
learning and missingness. A later preregistered study should include independently
reviewed decisive NLI snapshots, new claim families, a usability pilot and a
crossed participant/item analysis with an appropriately justified sample size.
