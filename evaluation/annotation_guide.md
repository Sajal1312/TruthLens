# TruthLens evaluation annotation guide

## Purpose and unit of annotation

The case is one claim plus a fixed set of passages. Annotate each passage's
relevance and textual stance, then annotate the conservative final verdict
that the available passages justify. These are different labels: a passage
can say something related without supporting or contradicting the claim.

This is the label guide for the existing developer-authored pilot fixtures.
It is not itself evidence of independent labeling or a validated scientific
protocol. The annotation-ready schemas and fuller independent two-annotator
workflow are in [`annotation/README.md`](annotation/README.md). Preserve both
original label sets and record disagreements; do not report agreement until
independent submissions actually exist.

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

- `SUPPORTED`: the evidence bundle sufficiently supports the entire claim,
  using the predeclared evidence policy and without unresolved conflict.
- `CONTRADICTED`: the evidence bundle sufficiently establishes an incompatible
  proposition, again without unresolved conflict. Absence or silence alone
  never qualifies.
- `INCONCLUSIVE`: evidence is absent, insufficient, conflicting, duplicated,
  ambiguous, stale for the claim's time frame, or supports only part of a
  compound claim. Do not force a direction for a claim that cannot be verified
  from the supplied evidence.

For the existing developer-fixture study, the production policy requires at
least two distinct URLs for a directional result. In independent annotation,
record evidence quality and provenance separately; two URLs do not prove
independent reporting.

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

## Difficult cases

The worked examples in [`annotation/README.md`](annotation/README.md#illustrative-examples-not-pilot-records-or-gold-labels)
are illustrative only, not sourced pilot records or gold labels. Apply these
principles:

- Quantifiers (`all`, `some`, `most`, `none`, `not all`) and negation must be
  interpreted in scope; word overlap does not establish entailment.
- For numerical claims, compare the same quantity, units, population, and
  rounding rule. If conversion or tolerance is unclear, annotate uncertainty.
- Keep publication date separate from event date. A publication in a given
  year does not establish that the event happened that year.
- A plan, forecast, or intention is not confirmation that a future event
  occurred. Historical attributed beliefs do not establish a current claim.
- For compound claims, record which part the passage addresses. The whole
  claim is not Supported when one component remains unaddressed.
- When passages conflict, annotate each passage independently and mark the
  claim Inconclusive until the conflict is resolved.

## Review workflow for existing pilot fixtures

1. Give both reviewers the same frozen JSONL corpus while keeping their
   submission files separate; retain stable `case_id` and `evidence_id` values.
2. Hide developer-authored `expected_*` values, model predictions, and each
   reviewer's labels from the other reviewer.
3. Ask each reviewer to label relevance, stance, and final verdict, with a
   short rationale and source check date for public excerpts.
4. Compare both records only after both independent passes are locked. Summarize raw
   agreement and disagreements by label; use a suitable chance-corrected
   statistic only when the sample and class counts make it meaningful.
5. Resolve labels with a documented adjudication note. Keep pre-adjudication
   labels for an honest agreement calculation.

`second_annotator_template.csv` provides a simple flat worksheet for this
workflow. It is blank by design; no second-annotator results or agreement are
claimed. For the new claim/evidence/annotation/adjudication records, use the
JSON schemas under `annotation/schemas/`.
