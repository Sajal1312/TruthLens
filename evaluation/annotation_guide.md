# TruthLens evaluation annotation guide

## Purpose and unit of annotation

The case is one claim plus a fixed set of passages. Annotate each passage's
relevance and textual stance, then annotate the conservative final verdict
that the available passages justify. These are different labels: a passage
can say something related without supporting or contradicting the claim.

This is a pilot annotation guide, not a validated scientific protocol. A
second reviewer should label a copy independently before discussion. Preserve
both original label sets and record disagreements; do not report agreement
until that independent pass has actually been completed.

## Passage labels

`expected_relevance`:

- `relevant`: directly addresses the proposition, including explicit
  contradiction.
- `weakly_related`: shares the topic or entities but does not address the
  proposition's relation, scope, or key qualifier.
- `unrelated`: does not provide useful context for the proposition.

`expected_stance` describes what the passage asserts relative to the claim:

- `SUPPORTS`: asserts the same proposition in compatible time, scope, and
  reference frame.
- `CONTRADICTS`: asserts an incompatible value, direction, date, or relation.
- `NOT ENOUGH INFORMATION`: asks a question, describes a hypothetical,
  attributes a historical belief without endorsing it, is too incomplete, or
  otherwise does not assert either direction.

Do not infer a contradiction from silence, missing search results, or a
passage merely saying that the claim is unknown.

## Final verdict labels

- `SUPPORTED` / `CONTRADICTED`: only when at least two distinct, directly
  relevant passages clearly agree on that direction with no directional
  conflict, in line with the current production policy.
- `INCONCLUSIVE`: insufficient or absent evidence, conflict, irrelevant or
  ambiguous text, duplicate evidence, or a claim whose parts do not all point
  consistently in one direction.

The gold final label evaluates this evidence policy on the provided fixture;
it is not a declaration of ground truth. For `synthetic_fixture` entries,
passages are manually constructed for controlled behavior tests and are not
real quotations or citations. Never display them as retrieved sources.

## Provenance and publisher fields

For `public_excerpt`, record a direct HTTPS URL, page title, publisher ID, and
the date on which the cited passage was checked. Keep excerpts short and
faithful. A URL or publisher label is not proof that a page is accurate or
independent. If two pages repeat the same underlying reporting, annotate that
known relationship in `independence_basis`; otherwise state that independence
has not been verified. Do not use publisher category as a truth label.

## Independent review workflow

1. Copy the JSONL corpus to a reviewer-specific file; retain stable `case_id`
   and `evidence_id` values.
2. Hide the first annotator's `expected_*` values from the reviewer.
3. Ask the reviewer to label relevance, stance, and final verdict, with a
   short rationale and source check date for public excerpts.
4. Compare annotations only after the independent pass. Summarize raw
   agreement and disagreements by label; use a suitable chance-corrected
   statistic only when the sample and class counts make it meaningful.
5. Resolve labels with a documented adjudication note. Keep pre-adjudication
   labels for an honest agreement calculation.

`second_annotator_template.csv` provides the fields for this workflow. It is
blank by design; no second-annotator results or agreement are claimed.
