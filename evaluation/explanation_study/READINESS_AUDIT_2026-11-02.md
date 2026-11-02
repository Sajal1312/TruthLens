# Pre-recruitment audit — NO-GO

Audited the existing `runs/study_v1/` bundle on 2 November 2026. This is a
readiness assessment, not a participant study, ethics approval or independent
answer-key review. No recruitment, real responses or human approvals occurred.

## Passed checks

| Check | Actual finding |
|---|---|
| Allocation | 24 valid unfilled slots; 12 distinct claims and declared families per slot; six presentations of each condition |
| Counterbalance | 12 complementary two-slot blocks; each claim and each order position has 12 allocations per condition; no repeated claim within a packet |
| Pair integrity | Original claim/evidence/verdict blocks preserved across conditions; all displayed verdicts are Inconclusive |
| Frozen files | Existing bundle checksums verified; all 24 blank worksheets validate against the frozen schema |
| Participant masking | No explicit condition labels, condition fields, assignment map, seed, private keys, internal case IDs or directional hypothesis found in the 24 packets |
| Privacy by design | Consent is unchecked; sharing is voluntary; no automatic upload, analytics or autosave; source links are optional external references |
| Response import | Frozen JavaScript tested in a mocked DOM/Blob environment, with temporary synthetic fixtures only; consent gate, exported JSON parsing, schema validation and existing CLI import passed |
| Missing/invalid input | Skipped ratings retained as null; invalid rating rejected; duplicate/version checks exercised by regression tests; no independent key review means objective scores withheld |
| Empty study | Real response directory empty; analysis reports “Study not yet conducted” |
| Regression | 139 targeted tests passed, including the accessibility regression added in this audit; one existing urllib3/LibreSSL warning |

The masking check concerns explicit labels and stored answers. In a
multiple-choice quiz the correct option necessarily appears among the choices;
it is not identified as correct. The ordinary word “baseline” occurs in
measurement-context prose, not as an experimental condition label. Differences
in length/detail can reveal presentation differences, so blinding remains partial.

## Recruitment blockers and required human actions

1. **Consent information is unfinalized.** Complete investigator/contact,
   institution/course and applicable approval details, storage location/access,
   retention/deletion date, withdrawal contact/deadline, and independent concerns
   contact. The generic rights/privacy text already covers voluntary participation,
   skipping/stopping without penalty, data types, optional timing, local downloads
   and the limits of withdrawal after aggregation. Concrete operational details
   are missing; no institutional approval was found or inferred. An actual human
   organizer must finalize these details and confirm applicable local procedures.
2. **Independent key review is absent.** There are 12 items × two proposed keys
   = 24 keys, with **0 independently approved keys and 0 reviewer records**.
   `private/key_reviews.json` is `[]`. An independent reviewer must check every
   question, distractor, proposed key, family and source display in the final
   bundle, then record their own alias, actual timestamp, rationale and decision
   tied to the final `answer_keys.json` checksum. No approvals were generated.
   Checksums establish version matching, not reviewer honesty or independence.
3. **Audience comprehension has not been established.** All 24 packets contain
   implementation-facing terms including `timeless_candidate`, NLI, `counted:
   False` and references to an “experimental guard.” The method refers to exact
   propositions and narrowly recognized opposites; numerical notes describe
   interval/tolerance policies. Claim sentences are mostly short, but the full
   explanations cannot be certified understandable to implementation-naive
   participants. The investigator must specify the intended audience and review
   these terms, or approve a versioned neutral glossary/presentation change.
   This audit does not silently alter treatment wording or consent terms.
4. **Frozen quiz controls need an accessibility correction.** The original
   selects are labeled only “Your answer,” without a programmatic association
   to the actual question. The source generator now adds question IDs and
   `aria-labelledby`, with a regression test. Existing `study_v1` HTML is
   deliberately unchanged. Prepare a new final bundle using the corrected
   generator; do not distribute the old packets as corrected materials.
5. **Browser and burden preflight is incomplete.** No successful real-browser
   rendering/download/import round trip was completed. A Safari preview attempt
   was interrupted before rendering the packet; its temporary tab was closed.
   The JavaScript mock is not browser validation. Test the final local HTML in
   the actual Safari/Chrome versions/devices to be used, including keyboard
   navigation, zoom/narrow-width wrapping, screen-reader question names, export
   without consent, voluntary test export, JSON import and interruption handling.
   Use clearly labeled temporary software-test fixtures and delete them. Do not
   count a facilitator preflight as participant study data.

## Per-item clarity/context review

This table reviews wording, not factual gold or suitability approval. The
source passages were inspected as saved material; original websites were not
rechecked. No annotations or source facts were changed.

| Existing case ID | Readability/context concern for a human reviewer |
|---|---|
| `dev_earth_orbit_support` | Short claim; evidence adds a stellar reference frame and moving-object qualification. Distinguish passage nuance from the exact-wording system abstention. |
| `dev_conflicting` | Explicit, readable scope; standard atmospheric pressure may need ordinary-language context. The mutually incompatible passages are explicitly constructed, not two real scientific findings. |
| `dev_date_mismatch` | Specific named event; the saved passage contains 6 August and 5 August PDT. Review the date/time-zone nuance without treating page/event dates as interchangeable. |
| `diag_partial_negation_scope` | “Not all” versus “some” requires quantifier scope; “some have moons” alone need not establish “not all.” Test reader understanding without revealing a factual answer. |
| `diag_numeric_contradiction` | Simple claim and passages; the system's exact-wording abstention may appear counterintuitive. Participants must rate the recorded explanation, not assume semantic reasoning occurred. |
| `diag_all_students_some_failed` | Students and examination are unspecified. Confirm participants are told how to interpret the constructed scenario's shared population. |
| `diag_unit_equivalence` | Understandable unit conversion; paraphrased evidence and exact-wording abstention need clear method context. |
| `diag_greater_than_comparison` | “The sample” has no real-world identifier. Treat it only as a constructed same-sample scenario; extraction limitations must not be mistaken for arithmetic competence. |
| `diag_percentage_equivalence` | Simple arithmetic, with paraphrase/extraction limitations. General arithmetic knowledge may dominate the task. |
| `diag_future_plan_not_event` | Company and product unnamed; a reported plan is distinct from a completed outcome. Confirm the hypothetical entity/time context is clear. |
| `diag_ratio_equivalence` | Red/blue population unspecified; two-to-one wording needs basic ratio literacy. |
| `diag_conflicting_event_dates` | Conference unnamed; saved constructed passages conflict. Distinguish that textual conflict from the rule pipeline's recorded one-match reason. |

## Questionnaire and accessibility review

- Five rating prompts use a consistent 1–5 agreement scale, with a neutral
  midpoint and a skip/unanswered option. Comments and confidence are optional.
  Ratings and confidence inputs have text labels; raw retrieved text is escaped.
- “I understand why …” measures perceived understanding, not demonstrated
  understanding. The quote-selection quiz checks recognition of the recorded
  reason; eleven items reuse the same reason string. Several distractors are
  conspicuously implausible and different in length. Independent review should
  consider ceiling, learning and demand effects before approving these keys.
- The three recurring limitation questions repeat shared cautions displayed in
  both conditions. Performance can reflect recall of the notice, not deeper
  evidence-limit recognition. Quiz-confidence calibration concerns that answer,
  not whether a real-world claim is true.
- “Rely … without checking” may elicit socially desirable low reliance after
  repeated cautionary notices. Report it separately; higher trust is not an
  improvement metric by itself.
- Skip combines uncertainty, not-applicable and deliberate nonresponse; there
  is no separate “I don't know” response. Confidence can be entered without a
  quiz answer, but the analysis correctly excludes it from calibration. Any
  change to response options requires investigator approval and versioned
  materials/schema/analysis decisions; none were made in this audit.
- Numeric rating options rely on the global anchors; A/B/C answer options rely
  on a preceding list. Repeating anchors and reviewing screen-reader reading
  order may help. The new question association is only a targeted fix, not an
  accessibility conformance certification. No assistive-technology test occurred.
- Visible-text counts range from **9,219 to 9,593 words per packet**, including
  repeated instructions and controls and excluding script/style data. This is
  not a measured reading time. The stated 25–40-minute estimate remains untested.
  There is no autosave: accidental tab closure loses unsaved answers. The form
  warns about this; assess whether the burden and loss risk are acceptable.

## Nonblocking research limitations once readiness tasks are resolved

Convenience sampling, partial blinding, presentation-length confounding, mixed
synthetic/public evidence, no refreshed source verification, unspecified
constructed entities, learning/ceiling effects and all-Inconclusive rule-mode
snapshots restrict interpretation. These materials do not measure decisive NLI
explanations, verdict accuracy or general source independence. The 24-slot
plan is not a power calculation. Confidence intervals are exploratory and
conditional on the fixed item set, with complete-block requirements specified
in the unchanged analysis plan. Subjective usefulness is not factual correctness.

## Changes and validation scope

- Minimal technical change: `prepare.py` associates quiz selects with question
  prompts using ARIA IDs. Question wording, options, scales, assignment logic,
  consent terms, analysis rules and the frozen bundle were not rewritten.
- Added one accessibility regression in `tests/test_explanation_study.py`.
- Ran 139 targeted tests, frozen-JavaScript mock export plus existing CLI
  import with temporary synthetic input, schema/assignment/hash checks,
  Python syntax checks and `git diff --check`.
- All synthetic response exports, generated test packets, mock scripts, pytest
  fixtures and synthetic analysis outputs from this audit were held in one
  temporary directory and deleted on completion. The real response directory
  and key-review file remain empty. Production and pilot files are unchanged.
- No held-out data, Tavily credentials, live search or model inference used.

## Exact sequence to reach a recruitment decision

1. Resolve consent/contact/retention/approval details and investigator decisions
   on jargon, ambiguous scenarios, questionnaire options and burden. Preserve
   original materials and document any approved changes; do not fill human
   reviews automatically.
2. Create the final frozen bundle with the corrected generator and the actual
   finalized neutral information sheet, using a new destination, for example:

   ```sh
   .venv/bin/python -m evaluation.explanation_study.prepare --output-dir evaluation/explanation_study/runs/study_v2 --slots 24 --information-sheet /absolute/path/to/FINAL_INFORMATION.md
   ```

   Replace the example path with the organizer's genuine completed file. The
   new seed is recorded privately; use `--seed` with the recorded number only
   if the investigator elects to replay the same allocation. Do not overwrite
   `study_v1`, copy old key reviews blindly or hand-edit frozen file hashes.
3. Have an independent reviewer inspect the exact final keys/materials and
   supply their own checksum-bound review. Confirm applicable institutional
   requirements and finalize the plan before viewing any real responses.
4. Complete and document Safari/Chrome, keyboard/accessibility and burden
   preflight on that final bundle. Validate any temporary software-test export
   using the existing CLI, and delete all synthetic test artifacts afterward.
5. Recheck final bundle integrity, allocations, consent completeness and genuine
   key-review status. Only after all blockers are resolved should the human
   investigator issue GO. Share only one assigned packet and finalized public
   information per person; keep keys/mappings private and allocations balanced.

**Current recommendation: NO-GO for recruitment. Automated technical checks
pass; informed-consent readiness, genuine independent review and final human
usability/browser readiness have not yet been established.**
