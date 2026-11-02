# Independent annotation framework

This directory defines an annotation-ready dataset format. The three JSON files
in `templates/` are intentionally empty. No new examples, labels, or agreement
statistics have been fabricated. `evaluation/data/development.jsonl` and
`diagnostics.jsonl` remain developer-authored pilot fixtures; they are not
independent annotations. The existing held-out material is not part of this
framework and must not be used for tuning or described as a new blind test.

The 90-claim preparation lives in `pilot_90/`. Its manifest has an aspirational
30/30/30 verdict distribution and all planned multi-label challenge categories;
the claim list, both annotator files, and adjudications are empty. The class
targets are sampling goals only. Never change a gold label to satisfy a quota.

Before adding staged candidates, use the separate
[`candidate_reviews/README.md`](candidate_reviews/README.md) workflow. It ties
human inclusion decisions to exact candidate snapshots and provides a dry-run
importer. The 30 prepared review packets are blank; no approvals or real-pilot
imports have been generated.

## Record layout

Store one JSON object per claim in the pilot's `claim_records.json` array.
It contains the original claim, one or more challenge-category tags, the split,
source passages, URLs or source IDs, publication dates, and event dates only
when explicitly stated. Do not include annotator labels in this file. Use
`annotation_status: "unannotated"` until independent labeling begins.

Each annotator submits one separate record per claim in
`annotator_records.jsonl`. It records that annotator's claim-level verdict and
one relevance and stance label for every evidence passage, plus separate
rationales, confidence ratings, and notes. Annotators must not see one
another's labels or system predictions before submission.

After comparing the two frozen records, an adjudicator writes one record to
`adjudications.jsonl`. This is the only record containing final `gold_verdict`,
`gold_relevance`, and `gold_stance`. Before review, use `adjudication_status:
"pending"`, null gold labels, and no adjudicator ID. A missing label means
unannotated; it must never be interpreted as Inconclusive. The JSON Schemas in
`schemas/` define allowed fields and labels. Validate with a JSON Schema 2020-12
validator when one is available; no new validation dependency is required by
TruthLens itself.

Evidence records preserve the passage as collected with source title, source
identifier or direct URL, declared publisher ID, and check date where
available. Keep publication date and event date separate. Do not infer a date,
source independence, or stance from a publisher category. Record collection
method and retrieval timestamp in a separate dataset manifest when the real
corpus is assembled.

## Annotation protocol

1. **Freeze the evidence bundle.** For each claim, record the exact claim text
   and the passages a participant should assess. Preserve direct URLs and
   source identifiers. Mark synthetic passages explicitly and never mix them
   with public evidence without a clear tag.
2. **Calibrate the guide.** Select a small subset of the 90 claims, have both
   annotators label it independently, then lock both submissions before
   discussing unclear instructions. Revise the guide and re-annotate affected
   pilot examples under the final version. Keep this pilot development-only.
3. **Annotate independently.** Two people label the same 90 claims and every
   every passage. Hide model output, thresholds, the other annotator's labels,
   and any expected label. Each annotator records a 1–5 confidence rating and
   a short rationale. Do not force a directional verdict when the fixed
   evidence is absent, ambiguous, stale for the claim's time frame, or
   conflicting.
4. **Compare before adjudication.** Preserve both original files. Report raw
   agreement and a confusion matrix for claim verdict, passage stance, and
   relevance. For two annotators on the same categorical units, report Cohen's
   kappa alongside agreement. Also report each annotator's class counts and
   per-class agreement/disagreement counts where support allows. Avoid a
   class-specific kappa when its denominator is too small. Evidence passages are clustered within claims;
   use claim-cluster bootstrap intervals for uncertainty, or report the
   passage-level agreement as descriptive only. Do not compute a statistic
   until two genuine independent annotation files exist.
5. **Adjudicate disagreements.** A third reviewer, or a documented consensus
   meeting after independent submission, resolves each disputed label using
   the written rules and source passage. Record the chosen label, reason,
   adjudicator ID, and unresolved ambiguity. Keep pre-adjudication labels so
   agreement remains reproducible. If ambiguity remains substantive, use
   Inconclusive for the claim and NOT ENOUGH INFORMATION for the passage when
   neither direction is established.
6. **Lock the later final split.** This 90-claim pilot is for guideline
   refinement and is not a final test set. Only adjudicated records enter score computation.
   Track missing decisions explicitly and exclude them from denominators with
   counts reported. Never convert missing annotation into an Inconclusive gold
   label.

### Label rules

- **Relevant**: addresses the same proposition, including an explicit
  contradiction, in compatible scope and time. **Weakly related**: topical or
  entity overlap without addressing the proposition. **Unrelated**: offers no
  useful context.
- **SUPPORTS**: the passage asserts the claim in the same scope, time, and
  reference frame. **CONTRADICTS**: it asserts an incompatible proposition.
  **NOT ENOUGH INFORMATION**: it is silent, hypothetical, attributed to a
  historical belief, incomplete, merely reports intent for a future event, or
  otherwise does not assert either direction.
- The **claim verdict** is about the entire provided evidence bundle. Use
  Supported or Contradicted only when the collected evidence meets the
  predeclared evidence policy and has no unresolved directional conflict. Use
  Inconclusive for insufficient, conflicting, stale, or ambiguous evidence.
  Absence of evidence is never contradiction.
- For compound claims, annotate each passage against the original claim and
  identify the supported/contradicted component in the rationale. Do not
  consider one supported component sufficient to support the whole claim.

### Illustrative examples (not pilot records or gold labels)

These examples explain distinctions only. They are not observations, citations,
or pilot annotations.

| Situation | Illustrative claim and passage | Annotation guidance |
|---|---|---|
| Relevance versus stance | Claim: “Mars has exactly three natural moons.” Passage: “Mars has two natural moons.” | Relevant passage; CONTRADICTS stance. Relevance does not mean support. |
| Quantifier scope | Claim: “Not all planets have moons.” Passage: “Some planets have moons.” | Relevant topic, but NOT ENOUGH INFORMATION: it does not establish that some planet lacks a moon. |
| Direct negation | Claim: “The board did not approve the plan.” Passage: “The board approved the plan.” | CONTRADICTS if the board, plan, and time match. Otherwise note the ambiguity. |
| Double negation | Claim: “The board did not reject the plan.” Passage: “The board did not reject the plan.” | SUPPORTS the wording as stated; do not mechanically flip a label because “not” appears. |
| Numerical claim | Claim: “A triangle has four sides.” Passage: “A triangle has three sides.” | Relevant and CONTRADICTS. This example does not authorize a general calculator rule. |
| Event versus publication date | Claim: “The mission launched in 2024.” Passage: “Published in 2024; the mission launched in 2019.” | Use the explicitly stated event date, not publication date: CONTRADICTS if it is the same mission. |
| Future intent | Claim: “The company will open the site next year.” Passage: “The company plans to open the site next year.” | Relevant but NOT ENOUGH INFORMATION about whether the event occurs. |
| Compound claim | Claim: “A and B occurred.” Passage: “A occurred.” | May support component A; claim-level verdict remains INCONCLUSIVE until B is addressed. |
| Conflicting evidence | Claim: “The event was held on 3 May.” Passages: one says 3 May, another says 4 May. | Preserve each passage label; claim verdict INCONCLUSIVE while the conflict remains unresolved. |
| Insufficient or unverifiable | Claim: “A private meeting included a promise.” No passage documents it. | INCONCLUSIVE. Missing evidence is not proof that the event did not happen. |

For ambiguous wording, mismatched entities, unresolved time frames, or claims
that cannot be checked from the supplied bundle, use INCONCLUSIVE and explain
why rather than guessing.

## Categories and target size

Use multi-label challenge tags; categories overlap. Cover quantifier scope,
direct/double/partial negation, numerical statements, event versus publication
date, future intent versus completed events, compound claims, conflicting
evidence, and insufficient evidence. Include ordinary non-edge claims as a
control group. Do not force a category into a verdict it cannot logically
receive (for example, a genuinely evidence-insufficient case is Inconclusive).

Recommended main-study target: **600 distinct claims**, aiming for **200
adjudicated claims per verdict** after a candidate pool has been independently
annotated. Tag categories across that pool and target at least 50 cases per
challenge tag where feasible. After adjudication, a data steward can assign
whole claim/provenance groups to a grouped 60% development, 20% diagnostic,
20% final-test split while balancing the adjudicated verdict counts; keep the
final-test labels inaccessible to the people tuning TruthLens. That yields
about 120 development, 40 diagnostic, and 40 final-test cases per verdict.
Category tags overlap, so category counts need not sum to 600. This remains a
modest study, not enough for broad population-level claims. If time or
annotator capacity is limited, use the prepared 90-claim pilot manifest first
(about 30 per verdict as an aspirational target) and report it as exploratory
rather than claiming a balanced benchmark.

Before splitting, deduplicate and group claim families: near-duplicate claims,
paraphrases, shared events, and passages from the same reporting chain must
stay together. Also group by event/topic and source provenance to reduce
leakage. A data steward may use adjudicated class counts to balance the split,
but must seal the final-test claims and labels from the people tuning the
system. Do not move difficult examples between splits after seeing system
errors. If the final set is exposed or used for a decision, retire it and
collect a new future test set.

## Reporting safeguards

Report claim-level final verdict metrics separately from passage relevance,
raw NLI stance, and effective stance after filters. Include per-class
precision/recall/F1, confusion matrices, accuracy, macro-F1, coverage,
abstention, and selective accuracy. State each denominator and show `undefined`
when a class has no gold or predicted examples; do not replace undefined
precision with zero without saying so. Macro-F1 should average only classes
present in gold data and list those classes. Report missing annotation counts,
inter-annotator agreement before adjudication, and confidence intervals for
final-test estimates. Never tune thresholds or guards on final-test results.

The evaluation runner currently consumes the older `expected_*` developer
fixture format. This new annotation schema is deliberately separate; a future
adapter should be reviewed and tested before adjudicated records are scored.

## Current experimental guards

Neither guard is enabled in the app.

- **Quantifier-scope abstention:** targets cases where the NLI model mistakes
  existential evidence such as “some” for support of a universal or partial
  negation claim. It preserves the model's raw label but maps affected
  effective passage labels to NOT ENOUGH INFORMATION. Because the cue list is
  broad, it can abstain even when a passage fully entails a quantified claim.
  In the current 37-claim developer diagnostic set it changed coverage from
  0.216 in the experimental semantic path to 0.189; selective accuracy rose
  from 0.875 to 1.000. This is one small, authored dataset and not evidence of
  general improvement.
- **Future-intent abstention:** targets NLI support for statements like “the
  company plans to launch” when the claim says the event will occur. It
  preserves the raw label and abstains on the effective passage label. It may
  also abstain on clear commitments or on passages whose wording matches the
  simple cue pattern without changing the claim's meaning. In the current
  diagnostics it did not change aggregate claim metrics or coverage; the
  single future-intent case was already Inconclusive under the two-source
  threshold. It remains experimental pending independent annotation.

Metrics above are from visible developer-authored diagnostics, not an
independent evaluation. The NLI score is not a probability that a claim is
true.

## Preparing and validating this pilot

The pilot layout is:

```text
pilot_90/
  manifest.json
  claim_records.json
  submissions/
    annotator_1.json
    annotator_2.json
  adjudications.json
```

The manifest fixes the target at 90, lists all planned tags, and assigns the
same claim IDs to both annotators. The files contain no records yet. Add only
claims with traceable evidence to `claim_records.json`; use stable claim,
evidence, claim-family, event-group, and provenance-group IDs. Set
`provenance_relation` to `unknown` and the group ID to null unless a shared
origin, syndication, suspected relation, or independence is supported and its
basis is documented. These fields are leakage and provenance diagnostics, not
verdict signals.

Keep the two submissions in separate files. Give each annotator the same
manifest and frozen evidence but access only to their own file. The workflow
below creates a separate snapshot and checksum before adjudication. Store the
adjudicated result separately in `adjudications.json`.

Validate during preparation with:

```sh
python -m evaluation.annotation.validate_pilot
```

This checks schemas, required fields, label values, duplicate IDs, references,
and annotator identity. It permits an empty or partially completed pilot. Once
all 90 claims are present, set manifest status to `ready`; after both
annotators submit every claim and passage, run:

```sh
python -m evaluation.annotation.validate_pilot --require-complete
```

The command does not compute agreement or create gold labels. Compare the two
frozen submissions before adjudication; report overall and class-specific raw
agreement, confusion counts, and Cohen's kappa for each label task where
sample support permits. Keep class supports beside each statistic. Do not
calculate any agreement value until actual independent annotation files exist.

The validator uses `jsonschema`, listed in `requirements-dev.txt`; it is a
development-only tool and is not imported by the application or evaluation
runner.

### Submission integrity and readiness

Once the manifest is `ready` and all 90 claim/evidence records are frozen,
each annotator completes only their assigned working file. After completion,
from the project root run:

```sh
python -m evaluation.annotation.submit_pilot --annotator annotator_1
python -m evaluation.annotation.submit_pilot --annotator annotator_2
```

The command validates the submission and writes a separate snapshot under
`submissions/snapshots/<alias>/` plus a record under
`submissions/integrity/<alias>/`. Each integrity record includes the pilot
version, SHA-256 hashes for the pilot manifest, claim/evidence records,
working file and snapshot, annotator alias, UTC ISO 8601 timestamp, schema
version, and validation status. It does not edit the working submission. New
files use exclusive-create mode so an existing snapshot or integrity record
cannot be silently overwritten.

To intentionally revise a submission, retain the previous snapshot and
integrity record, update the working file as a new revision, and explicitly
name the latest integrity manifest:

```sh
python -m evaluation.annotation.submit_pilot --annotator annotator_1 \
  --supersedes submissions/integrity/annotator_1/<latest-manifest>.integrity.json
```

The validator checks that the revision names the same annotator's latest
record and that the chain is unambiguous. A change to claim/evidence records
invalidates previous integrity records; freeze them before annotation and
create a new pilot version if they must change. Adjudications must reference
the current verified integrity manifests. A revision makes existing
adjudication references stale, so affected records must be adjudicated again.

Validate and view a concise status report with:

```sh
python -m evaluation.annotation.validate_pilot
python -m evaluation.annotation.validate_pilot --require-complete
python -m evaluation.annotation.readiness_report
```

Normal validation permits the empty pilot. `--require-complete` fails until
there are 90 claims, matching complete submissions, and verified snapshots.
The readiness report summarizes claim/evidence completeness, challenge-tag
counts, submission and integrity status, and adjudication counts. It reports
not ready for analysis until validated original submissions exist and all 90
claims are adjudicated. None of these commands creates labels or agreement
statistics.

SHA-256 hashes detect accidental changes when both data and integrity records
are preserved; they are not digital signatures. Someone with write access can
change both the files and their hashes. Read-only file permissions are
advisory and can be changed by the same user. For a stronger audit trail,
archive integrity records and snapshots in institution-managed,
access-controlled or append-only storage. Separate files do not prove that
annotators worked independently; use separate accounts or managed storage
when that guarantee matters. The coordinator remains responsible for access.

Tests create synthetic records in temporary directories only. They do not
populate the real pilot or claim human annotation has occurred.

### Pre-distribution quality-control audit

Before sending the pilot to annotators, run the separate, read-only preparation
audit from the project root:

```sh
python -m evaluation.annotation.quality_control --full-pilot
```

It prints a human-readable report and writes a machine-readable JSON report to
`evaluation/annotation/pilot_90_quality_report.json`. To also save Markdown,
or choose another report location:

```sh
python -m evaluation.annotation.quality_control \
  --directory evaluation/annotation/pilot_90 \
  --full-pilot \
  --json-output evaluation/annotation/reports/pilot_90_qc.json \
  --markdown-output evaluation/annotation/reports/pilot_90_qc.md
```

Without `--full-pilot`, zero claims is reported as an empty preparation state.
With that flag, anything other than exactly 90 claims is an error. Errors block
distribution, warnings require human review, and informational findings
describe coverage and sampling targets. Readiness is granted only with 90
claims and no outstanding errors or warnings. The audit never edits records,
generates labels, fetches URLs, or creates train/test splits. URL/date checks
are structural; near-duplicate and provenance-overlap findings are review
candidates, not proof. Keep claim-family, event, and recorded provenance
groups intact when a future split is designed.

For each label task, align records by `(claim_id)` for claim verdict and by
`(claim_id, evidence_id)` for passage labels, never by file row order. Report
the number of matched units and missing units first. Raw agreement is the
number of matching pairs divided by the number of matched pairs. Cohen's
`kappa = (P_o - P_e) / (1 - P_e)`, where `P_o` is raw agreement and `P_e` is
the agreement expected from each annotator's observed label marginals. If no
pairs exist or `P_e = 1`, report kappa as undefined. Keep confusion matrices,
class supports, and one-vs-rest class agreement/disagreement counts so class
imbalance is visible. Do not compute or publish these statistics from the
empty pilot templates.
