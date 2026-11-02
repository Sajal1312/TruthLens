# Blinded explanation reading study — preparation only

This is separate from `evaluation/annotation/`. It neither reads gold pilot
labels nor writes claims, approvals, submissions or imports. There are no real
participants or response results in the framework. Generated assignment slots
are empty allocations, not invented people.

## Prepare once

From `~/Downloads/TruthLens`:

```sh
.venv/bin/python -m evaluation.explanation_study.prepare --output-dir evaluation/explanation_study/runs/study_v1 --slots 24
.venv/bin/python -m evaluation.explanation_study.analyze --bundle evaluation/explanation_study/runs/study_v1 --output-dir evaluation/explanation_study/runs/analysis_before_collection
```

The second command must say **Study not yet conducted**. Both commands refuse
existing output directories. Use a new name for a later preparation/analysis.
No model inference, network, Tavily key or extra dependency is needed.

Preparation creates a fresh random assignment seed locally and records it in
`private/manifest.json`. To reproduce the same allocation, use the same source
files/version, `--slots` and `--seed RECORDED_NUMBER` with a new destination.
An explicit seed gives deterministic byte-for-byte preparation. Do not send
the seed or manifest to participants. The generated `runs/` directory is
excluded from Git because it contains the allocation/key mapping and will
later hold raw responses. Other destinations need equivalent protection.

## Folder layout

- `public/PARTICIPANT_INFORMATION.md`: finalize investigator, contact, retention,
  withdrawal and applicable approval details before distribution.
- `public/QUESTIONNAIRE.md`: common neutral instructions and 1–5 rating scale.
- `public/slots/<opaque code>/packet.html`: one person's offline reading/form
  packet, with 12 distinct claims shown once each.
- `public/slots/<opaque code>/blank_response.json`: optional empty worksheet;
  deliberately tagged `blank_template`, with no consent or answers.
- `private/`: original material snapshots, proposed keys, schema copies,
  counterbalanced assignments, frozen spec/protocol/analysis plan, checksums
  and the initially empty `key_reviews.json`.
- `responses/`: initially empty. Only files voluntarily exported by real
  consenting participants and supplied by the organizer belong here.

Generated packets mix saved public excerpts and explicitly constructed study
passages. Synthetic titles are neutralized to avoid exposing developer stance
expectations; passage text is preserved. Public source URLs/titles remain real
stored references, not newly verified sources. The original candidate/pilot
datasets are not touched. All displayed verdicts in this version are
Inconclusive from current rule mode; do not claim this is a full NLI study.

## Investigator checklist before conducting

1. Read [PROTOCOL.md](PROTOCOL.md) and [ANALYSIS_PLAN.md](ANALYSIS_PLAN.md).
   Finalize contact/consent details and applicable institutional approval.
   Edit a separate copy of `PARTICIPANT_INFORMATION.md`, then prepare a new
   bundle using `--information-sheet PATH_TO_FINALIZED_SHEET`. The initial
   preparation-only bundle contains an unfinalized template. Do not edit
   frozen generated sheets in place; their checksums would become invalid.
   Changes to rendering code, schema or information text create a different
   bundle ID, so responses from different material versions cannot be mixed.
   Preview the local HTML in the browsers that will be used, check that labels
   wrap and download works, and do not treat a preview as participant data.
2. Have a reviewer independent of material preparation check each private
   item, family, question, distractor and proposed key against the displayed
   evidence and recorded explanation. These are output/literacy keys, not
   factual claim gold. Record their actual decision in
   `private/key_reviews.json`, using `key_review.schema.json`. Do not ask an
   assistant to invent or submit a human review.
3. Each actual review record needs `study_version`, `keys_sha256`,
   `reviewer_alias`, `independent_of_materials_author: true`, `decision`
   (`verified` or `revision_required`), an actual timezone-aware ISO 8601
   `reviewed_at`, and `rationale`. Obtain the key checksum with Python's
   `hashlib.sha256(path.read_bytes()).hexdigest()` or `shasum -a 256` on
   `private/answer_keys.json`. Do not alter keys after review; create a new
   version/bundle if changes are required. Every supplied review must match
   the frozen keys, and any `revision_required` blocks objective scoring.
4. Freeze allocation and plan. Recruit real consenting adults under the
   approved procedure. Give consecutive unused slots in complete two-slot
   blocks; never choose conditions according to a person's preferences.
   Do not populate names, recruitment logs or ratings automatically.

## How a real participant completes it

Give the person **only their own slot folder** and the finalized information
and questionnaire sheets. Do not share `private/`, other slots or the whole
repository. They open `packet.html` locally in Safari/Chrome, read the
information, decide about consent, and work in task order. Ratings and quizzes
are optional; unanswered is distinct from a low rating. They explicitly click
**Download my responses**, then choose whether to give the file to you.
The form has no analytics, network submission, autosave or automatic timer.
Leaving without exporting creates no research response. Downloads can expose
the file to the device owner, so use an appropriate private device/folder.

Optional timing must be recorded consistently by a facilitator using a
stopwatch, including interruption status. Otherwise leave timing blank. Do
not substitute guessed time or claim automated reading-time measurement.

Preserve exports unchanged in a restricted local folder. Copy the voluntarily
shared JSON into `responses/` once; duplicate slot IDs are rejected, not
merged. Keep consent paperwork separately if the institution requires it.
If paper worksheets are used, transcribe only the person's actual answers
and consent, retain originals, and have a second person check transcription.

## Analyze after genuine collection

```sh
.venv/bin/python -m evaluation.explanation_study.analyze --bundle evaluation/explanation_study/runs/study_v1 --output-dir evaluation/explanation_study/runs/analysis_after_collection
```

Use a new output directory for every run. `--responses OTHER_DIRECTORY` may be
used for explicitly supplied local exports. Analysis preserves inputs, checks
schema/assignment/material checksums, decodes conditions privately and emits
`analysis.json` and `REPORT.md`. Blank templates and nonconsenting files are
not analyzed. Missing ratings/quiz answers are counted, never imputed.

Without real consenting responses: **Study not yet conducted** and null
estimates. Without verified independent keys: comprehension/calibration
**NOT MEASURED**. Subjective usefulness never demonstrates factual correctness.
CIs require at least eight complete counterbalance blocks with variation,
not just many repeated trials. Any interval remains exploratory and conditional
on the fixed convenience item set.

Blinding is partial: condition names and hypothesis are hidden, but different
length and detail may reveal presentation differences. No outcome can yet be
claimed. After participation, use the protocol's debrief explanation.
