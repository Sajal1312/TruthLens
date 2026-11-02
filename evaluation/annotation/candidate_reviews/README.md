# Human inclusion review and safe pilot import

This workflow approves a candidate for inclusion in a fixed annotation bundle.
It does not assign evidence stance, gold verdicts, source credibility scores or
independent annotator labels. The prepared 30 packets contain no human decisions.
All reviewer aliases, timestamps, assessments and decisions are initially null
or blank. They must be filled by a real reviewer.

## What is preserved

`drafts/<candidate_id>/candidate.json` is the exact candidate snapshot supplied
for review. `review.json` is its editable human worksheet. The checksum covers
the entire claim record, including every evidence passage, URL, date, tag,
family/group and provenance field. It uses canonical UTF-8 JSON with sorted
object keys and compact separators. Whitespace and object-key order do not
change the checksum; evidence order and field changes do. Collector sidecar
notes are supplementary context and are not part of this claim/evidence hash.

The strict blank-draft schema validates newly generated worksheets. A completed
worksheet must satisfy `schemas/candidate_review.schema.json`. Blank drafts
cannot be submitted as reviews. No fields are automatically interpreted as
approval. Re-running packet preparation refuses existing packet paths; use
a new output folder when preparing another candidate version.

Submitted decisions live in `submitted/<review_id>/` with `review.json`, the
reviewed `candidate.json`, and an integrity manifest. IDs and files use
exclusive creation. SHA-256 detects accidental changes to the review and
snapshot; original revisions remain available. An intentional later decision
must have a new review ID and explicitly name the latest ID in `supersedes`.
The latest decision controls eligibility, including a later rejection. Ambiguous
revision branches, missing snapshots and checksum errors stop the workflow.

## Reviewing the 30 candidates

1. Read the combined source review at
   `../candidates/combined_review/review_report.md`, the annotation guide, and
   the packet's `candidate.json`. The phase reports identify short excerpts,
   partial coverage, source versions, forecasts and collector paraphrases.
2. Open each original source yourself. Verify the saved excerpt and its
   surrounding qualifiers, publisher and source role. In `review.json`, use a
   unique pseudonymous `reviewer_alias` and `review_id`; enter your actual ISO
   8601 timestamp with timezone, for example the syntax
   `YYYY-MM-DDTHH:MM:SS+05:30`. Do not enter a template timestamp literally.
3. Assess claim clarity and scope (`clear` or `revision_required`) and evidence
   context (`adequate` or `revision_required`), explaining both. Verify source
   fidelity, not whether the claim is true. An open research proposition or
   deliberately limited bundle may be suitable for annotation if its scope
   and limits are explicit. A short fragment that loses meaning needs revision.
4. Complete every evidence-review entry exactly once. Record source status
   `verified`, `inaccessible`, `mismatch`, or `not_verified` and your basis.
   Set the overall source status to `verified`, `partially_verified`, or
   `unable_to_verify` consistently. Record provenance as `documented`,
   `unknown`, or `conflicting`, with a rationale. `documented` does not mean
   editorially independent; describe shared origin where present.
5. Choose one decision: `approved`, `revision_required`, or `rejected`, and
   write your inclusion rationale. Approval requires verified sources, clear
   scope, adequate context and resolved conflicting metadata. Unknown dates
   and unknown independence alone do not make a source invalid. Their effects
   must be acknowledged in the rationale. Do not add gold labels to this file.

### Publication-date choices (per evidence passage)

| Status | Meaning and required action |
|---|---|
| `verified_publication_date` | An authoritative original publication day is established. `verified_publication_date` must match the candidate's date. If the candidate is wrong or null, first request a candidate revision and review its new checksum. |
| `verified_undated_source` | The reviewer establishes the source is presented without a publication date. Candidate and verified-date fields remain null; explain the verification basis. |
| `publication_date_unknown` | The original publication date could not be established. Keep both date fields null; explain the search and whether the uncertainty affects inclusion. |
| `conflicting_date_metadata` | Authoritative metadata disagree or cannot be reconciled. Record the conflict and request revision or reject; import is blocked until resolved. |

An absent date does not automatically mean a verified undated source. Month-only
dates, last-updated dates, build timestamps, event dates and access dates must
not be converted into an invented publication day. Event dates remain in their
separate candidate field; describe multiple or partial event dates in your
scope/date rationale. Review commands never repair dates automatically.

## Commands

From the project root, activate the existing environment:

```sh
source .venv/bin/activate
python -m evaluation.annotation.candidate_review report
```

Packets for all 30 current candidates are already prepared. If you later need
a fresh set, use a new folder rather than replacing a reviewer's work:

```sh
python -m evaluation.annotation.candidate_review prepare --packets-dir /tmp/truthlens-review-packets-v2
```

After a human completes one worksheet, submit that exact file with:

```sh
python -m evaluation.annotation.candidate_review submit --file evaluation/annotation/candidate_reviews/drafts/CANDIDATE_ID/review.json
python -m evaluation.annotation.candidate_review report
```

Replace `CANDIDATE_ID` with the actual packet folder. The command validates
the current candidate checksum and preserves a separate submitted snapshot.
It does not edit candidate records or import them. For a revised decision,
use a new review ID and set `supersedes` to the latest existing review ID.
For a revised candidate, preserve the old collection version, edit it through
the collection process, prepare a new packet and obtain a new human decision.
Previous approvals become stale automatically.

Reports are `reports/approval_report.json` and `.md`. They show approved,
revision-required, rejected, pending and stale candidates; per-evidence date
assessments; metadata concerns; eligibility; and blocking reasons. The report
does not create reviewer decisions. An integrity failure stops reporting and
import rather than ignoring a damaged review.

## Safe import protocol

Use the default dry-run first. It writes no pilot files, backups or locks:

```sh
python -m evaluation.annotation.import_candidates --dry-run
```

Current output should block all 30 candidates for missing human approval and
exit with status 1. This is expected. To plan a reviewed subset, repeat
`--candidate CANDIDATE_ID` for each selected ID. One blocked requested candidate
prevents the entire requested import; the tool does not silently select a subset.

**No real import was performed during Phase 3.** Only after a separate human
approval and coordinator review of the dry-run can a future authorized import
use the explicit mutation command:

```sh
python -m evaluation.annotation.import_candidates --candidate CANDIDATE_ID --apply
```

Apply preserves stable IDs, tags, sources and provenance and appends exact
unannotated records. It rejects ID collisions, empty evidence/passages,
invalid sources/dates, stale or absent approval, capacity above 90, and any
pilot that is ready, has annotation/adjudication work, or has sealed/incomplete
submission snapshots. It never creates gold labels, submissions or adjudications.
After an import the manifest becomes `collecting`, never automatically `ready`.

Import uses cooperating process locks for both the pilot and submitted reviews,
checks exact current approvals again before writing, and saves exclusive
before-file backups, plan references and a receipt under `pilot_90/imports/`.
Existing record objects remain unchanged. Completed receipt chains and current
pilot checksums are checked before another import. After an authorized import,
run the pilot validator and QC and finish the full 90-claim collection before
freezing the bundle for the two independent annotators.

## Limits and recovery

Checksums and read-only permissions are accidental-change safeguards, not
authentication, digital signatures or strong immutability. The same filesystem
user can change files and hashes. Reviewer identity, actual source inspection
and independent work require coordinator controls and an external trusted
archive. This workflow records assertions; it cannot prove the reviewer did
the work. Inclusion review is separate from later independent labeling.

Two pilot files are replaced individually, not as a database transaction. If
a write is interrupted, before-files and the prepared plan are retained, and
an incomplete transaction blocks later imports. Do not delete snapshots or
silently retry. A coordinator must compare preserved and current hashes,
recover or restore the pre-annotation bundle explicitly, and document the
incident. A crash may leave a lock: establish that no process is active before
investigating it. Back up the review history outside this workspace for stronger
protection. Never edit the existing submission-integrity files to bypass a block.
