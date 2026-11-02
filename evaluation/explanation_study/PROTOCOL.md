# Explanation reading study — investigator protocol v1

This study is separate from claim annotation and the 90-claim pilot. It tests
reader understanding and perceived usefulness, not factual correctness or
improvement in verdict accuracy. No participant has been recruited by this
software and no responses are supplied.

## Conditions, materials and estimand

The baseline displays the original frozen verdict, reason, method, limitations,
source passages and recorded per-source assessments. The other presentation
adds excerpts and the temporal, dependency, numerical and uncertainty views.
Both show identical claims, full evidence, source references and verdicts.
Shared warnings state that NLI scores are not truth probabilities, different
URLs do not establish independence, and this is preliminary assessment.
No diagnostics are recalculated and no model or network is used.

Twelve distinct claim families are selected explicitly in `study_spec.json`
from the permitted comparison report, with matching source-dataset checksums.
They are a convenience sample, not independently labeled gold. Repeated
Earth/Sun examples and paraphrase families are not assigned together. Inclusion
review must verify the manually declared families before recruitment. The five
imported pilot claims and their approvals/annotations are not study inputs.
All selected production rule-mode snapshots are Inconclusive. This preparation
therefore measures explanations of abstention, not decisive verdicts or current
NLI behavior. Archived NLI traces omit some original fields and are not used.

Some evidence is synthetic. Packets label it as constructed, retain its text,
and use neutral passage numbers instead of developer fixture titles containing
expected stance cues. Public-source titles/URLs and unknown dates are preserved.
Source pages are not refreshed. Gold labels, developer rationales, raw case IDs,
condition names, keys and assignment seed are never placed in public packets.

## Allocation and sample-size assumption

Plan 24 **unfilled assignment slots**, not 24 fabricated participants: up to
288 trial ratings if all 24 real consenting adults complete 12 trials. This is
an exploratory convenience study, with no claimed statistical power.

Recruit two new people per counterbalance block. Randomize item order within
each block with the recorded seed. Randomly assign six items to each condition
for one slot; the complementary slot receives the opposite condition for every
item in the same randomized order. Thus every slot has six of each type, each
person sees every claim once, and each item/order position appears under each
condition equally across complete blocks. Sequences have at most three
consecutive trials of one condition. No person should receive two slots or view
another packet. Recruit in complete blocks; record incomplete blocks, rather
than silently filling them with observations from another condition.

The facilitator allocates the next unused slot in the locked schedule without
selecting a packet based on a person's preferences. Do not create identities in
advance. A participant needs only their opaque slot code; no name, age, email,
student number, IP address or device details are requested. Staff must track
used slots privately without adding identifying data to exported research files.

## Blinding and conduct

Give each person only their own `public/slots/<code>/` folder plus the finalized
information/consent sheet. Never share the private directory, entire repository,
condition mapping or answer keys. The neutral study description discloses
different randomly assigned presentations but not a hypothesis about which is
better. Participants can infer differences from detail/length; do not describe
this as full double blinding. The facilitator may know allocation. If feasible,
freeze analysis decisions before an analyst opens the private mapping.

Use the same device/viewing instructions where feasible. Read saved evidence;
do not browse live sources during timed trials (links are optional references
for later checking). No coaching, feedback or discussion between participants.
They may skip questions, pause or stop without penalty. The local HTML form
exports only after an explicit click. It sends nothing over a network and has
no analytics, local storage, automatic timing or automatic collection. Preserve
original exported files; corrections should be documented separately.

Use consistent 1–5 agreement scales for clarity, usefulness, help identifying
limitations and understanding the recorded verdict reason. Reliance without
checking is measured separately and lower is not automatically better for every
possible application. The comprehension quiz concerns the recorded explanation
and system limitations, not truth labels for real claims. Participants give a
0–100 confidence estimate for their limitation-quiz answer. This supports a
task-specific calibration measure, not calibration of belief in claim truth.

Optional time fields are for a facilitator's per-trial stopwatch, ending after
ratings/quiz. Record interruptions; do not estimate retrospectively. Unmeasured
or interrupted time is excluded. Timing is facilitator-reported, not verified
telemetry; do not claim a reliable time effect without consistent collection.

## Objective keys and readiness

Private keys are proposed from exact displayed reason strings and documented
system limitations, never from NLI labels or developer factual gold labels.
One answer is objectively checkable against the frozen output; the other is a
system-literacy question about scores, missing evidence or source independence.
These are not independently validated yet. Before recruiting, an independent
reviewer must check every key, distractor and source display and write their
own record using `key_review.schema.json`. `private/key_reviews.json` starts as
`[]`. Never manufacture reviewer identities, dates or verification. Checksums
detect changes; they do not authenticate a person's honesty or independence.

Analysis with no verified key review suppresses objective accuracy/calibration
metrics even if subjective real ratings later exist. Any key objection blocks
those metrics. Human-reviewed keys still do not establish claim factual gold.

Before conducting: finalize investigator/contact, retention and withdrawal
details in a separate copy of the consent information, and pass it using
`--information-sheet` when preparing the final frozen bundle. Do not modify
generated frozen sheets in place. Obtain applicable departmental ethics/teaching
approval; independently review keys/families; freeze the bundle/version and
analysis plan. No institutional approval is asserted by this preparation.

After collection: debrief participants that the two presentation styles were
the existing explanation and the explanation with five diagnostic additions.
Do not tell them that the enhanced presentation is factually more accurate.
