# Readiness remediation — NO-GO pending human completion

Preparation only. No recruitment, new participant bundle, participant data,
human approval or study finding was generated. Frozen `runs/study_v1`, the
production application, pilot records and existing study protocol/analysis
rules remain unchanged.

## Prepared deliverables

Internal artifacts are under
[`runs/remediation_2026-11-02_internal/`](runs/remediation_2026-11-02_internal/README.md),
which is excluded from Git by the existing `runs/` rule. Keep the review packet
private because it identifies proposed answers. These are researcher documents,
not participant-facing materials or a recruitment release.

- `INVESTIGATOR_INFORMATION_WORKSHEET.md`: 20 unfilled investigator decisions,
  including investigator/supervisor/institution contacts, storage, retention,
  withdrawal, institutional approval and adult eligibility. It explicitly
  must not be distributed or used as the final `--information-sheet` input.
- `PROPOSED_MATERIAL_REVISIONS.md`: before/after wording for jargon and ratings,
  suggestions for less obvious distractors and missing-response choices, all
  twelve unchanged claims with context-review notes, and burden/blinding options.
  Suggestions preserve the intended claim wording and constructs; no new quiz
  key is approved and no source evidence or participant wording was replaced.
- `KEY_REVIEW_PACKET.md`: all 12 claims, 17 saved passages, 24 questions/keys,
  source references and baseline/enhanced frozen-packet links for the independent
  reviewer. Every per-question decision/rationale and reviewer identity/time
  field is blank. Exact source-file and canonical item/question/key checksums
  are recorded, with an automated preparation manifest.
- `BROWSER_ACCESSIBILITY_PREFLIGHT.md`: blank Safari/macOS and Chrome/macOS
  results covering keyboard/VoiceOver, wrapping/zoom, consent gate, download,
  UTF-8 contents, explicit sharing, missing answers and temporary test cleanup.

## Existing workflow reused

`key_review.schema.json` already supports a genuine review of the entire key
file tied to `keys_sha256`, version, reviewer declaration, actual timestamp and
rationale. It does not accept per-question worksheets. The new packet is a
human working aid, not another submission format, approval service or scoring
path. After reviewing the **final** bundle, a real independent reviewer must
supply their own existing-schema aggregate record. An unresolved item must not
be silently promoted to aggregate verification. Preserve the original drafts;
work on separately named copies. No record was submitted or modified.

Current genuine review records: **0**. Independently approved keys: **0/24**.
Actual response files in `study_v1/responses/`: **0**.

## Technical progress and checks

The prior generator fix already gives quiz controls programmatic question
labels; its regression passes. No further generator/schema/production defect
required a change in this task. It has not been retrofitted into the frozen
`study_v1` packets; a later final bundle must use the corrected generator.

The targeted run passed **144 tests** (the existing 139 plus five internal
artifact checks). It covers allocation balance, unique exposure, source/key
version matching, all blank decision fields, HTML safety/accessibility labels,
response validation, missing data, decoding and deterministic analysis. Tests
that construct synthetic responses use temporary directories only, which were
deleted afterward. No synthetic response was placed in a real study folder.

Python syntax, JSON/schema parsing, artifact/source checksums, frozen-bundle
integrity and `git diff --check` were checked. One existing urllib3/LibreSSL
warning remains. No held-out data, secrets, Tavily requests or model inference
were used. There was **no real browser or assistive-technology execution during
this remediation task**. Mock/code tests do not establish Safari/Chrome download
compatibility. Both manual result columns remain blank.

## Remaining investigator actions — in order

1. Complete all C01–C20 decisions and applicable institutional procedures.
   In particular, actual contacts, supervisor, institution, storage/access,
   retention/deletion, withdrawal rules, eligibility and approval details are
   still missing. Write a separate clean neutral final information sheet;
   exclude placeholders, completion instructions and unsupported policy claims.
2. Decide which wording and presentation proposals to adopt. Confirm the
   intended audience, constructed-scenario reference conventions, the treatment
   of “I don't know,” reading burden, timing and the narrow all-Inconclusive
   rule-mode scope. Changes to options/schema/scoring require explicit versioned
   decisions before implementation. Do not change claims to force answers.
3. Implement only the accepted changes, then prepare a **new** frozen bundle
   using the final information sheet and a new output directory. Do not overwrite
   `study_v1` or copy old checksum-bound approvals to changed material.
4. Have an independent reviewer check every final-version question/key, display,
   family and source context. The prepared packet binds the **existing** version;
   it cannot approve revised future keys. Obtain genuine checksum-bound review.
5. Complete actual Safari/Chrome, keyboard, VoiceOver and burden preflight on the
   final bundle; document actual observations, validate temporary software-test
   exports and delete test artifacts. Keep genuine exports separate.
6. Recheck the final bundle, consent completeness, human review and manual test
   record before a human recruitment GO decision. Give each person only their
   assigned packet and finalized public information; keep mappings/keys private.

**Recommendation: NO-GO for recruitment. Researcher preparation and reviewer
traceability are improved; human consent decisions, independent approval,
accepted material revisions and real-browser readiness are still outstanding.**
