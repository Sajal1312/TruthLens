# Real-world candidate staging

`phase1_15/` contains 15 source-derived candidate claims collected on
2026-11-01: five environment/sustainability, five cybersecurity/technology,
and five general factual candidates. These are claims authored from accessible
public documents, not a representative sample of claims circulating online.
They have not received independent human review, stance labels or gold verdicts.

The Phase 2 review retained all original Phase 1 claim wording and excerpts,
added seven traceable passages, and archived the pre-review files in
`phase1_15/history/`. Phase 1 now has 22 passages. The separate `phase2_15/`
batch adds 15 claims and 16 passages; `combined_review/` reports on all 30
claims and 38 passages. See `phase2_15/README.md` for methods and limitations.

## Files and reproducibility

- `claim_records.json`: records matching the existing claim/evidence schema.
  `split: pilot` denotes intended pilot use only; nothing was imported into
  `pilot_90/`. All annotation statuses are `unannotated`.
- `collection_manifest.json`: topics, collection date, evidence locators,
  collector checks, excerpt SHA-256 values, source roles, retrieval failures,
  limitations and review notes. Topic metadata is kept here because the
  existing claim schema has no topic field. Its `claim_category` field contains
  challenge tags, not subject areas.
- `review_report.md` and `review_report.json`: generated collection QC reports.

From the project root, regenerate the offline report with:

```sh
source .venv/bin/activate
python -m evaluation.annotation.review_candidates
python -m evaluation.annotation.review_candidates --directory evaluation/annotation/candidates/phase2_15
python -m evaluation.annotation.review_candidates --combined
python -m pytest -q tests/test_candidate_collection.py
```

The command checks schemas, reference joins, excerpt hashes and the existing
read-only preparation QC. It does not refetch pages. The 90-claim count warning
and its aspirational verdict sampling distribution are omitted from this
15-candidate report; no candidate verdict distribution is inferred. Human
review stays pending even when checks succeed. These generated reports may
be overwritten by rerunning the command; source records are not modified.

Each stored excerpt was located in a source page opened using the public web
tool, rather than accepted only from a search preview. Short passages preserve
source wording; HTML whitespace was normalized and NOAA's CO2 subscript was
rendered in plain text. A hash confirms the saved passage has not changed
since that collector check; it is not a signed archival copy or independent
confirmation that a future page still contains the passage.

## Collection limitations and follow-up queue

Evidence coverage remains limited: 22 candidates have one passage and eight
have two. This is a collection starting
point, not a sufficient bundle for measuring TruthLens's existing two-source
directional evidence policy. Find additional sources where justified and
investigate reporting chains before independent annotation. Neither different
URLs nor publisher IDs establish editorial independence. NASA, NIST, IETF
and UNEP organizations recur; that concentration is visible in the reports.

The original fourteen unknown Phase 1 publication dates remain null; there
are 27 unknown publication dates across the 38 current passages. A visible last-updated date, a site
build timestamp, a year, or a month was not converted into an invented exact
publication day. The collector's access date is recorded separately.
Montreal Protocol event years, RFC publication months and Gaia's planned
release month are documented in source-check notes, with exact date fields
left null where precision is insufficient. Equal publication/event dates for
the NIST announcement are separately evidenced; other event dates are not
inferred from publication dates.

Environmental pages are institutional summaries; the underlying studies and
their numerical assumptions need additional review. The Gaia entry describes
a schedule, not a completed release. RFC 8446 is deliberately version-scoped;
check its status and successor before using it for any claim about the current
TLS standard. Password guidance has a compromise-related exception in its
surrounding text. Several planned challenge tags are absent; no hypothetical,
conflicting or insufficient-evidence cases were invented to fill them.

Failed CISA, old CERN, RFC and UN PDF retrieval attempts are logged in the
collection manifest. The CERN and RFC candidates use successfully opened
alternate URLs. No excerpt from an inaccessible page was included. There is
no claim that the 15 candidates represent balanced truth/stance classes.

## Human review and approval

1. A data steward opens every original URL and finds each exact excerpt using
   its locator. Check the surrounding context, source version, units, dates,
   scope and attribution. Consult underlying publications when needed.
2. Check the claim text is self-contained and retains qualifiers. Resolve
   compound components and scheduling language. Add evidence if the intended
   annotation policy needs it; do not manufacture an opposing passage.
3. Review duplicates, recurring publishers, claim families and provenance.
   Record evidence for any shared origin or independence assertion. Keep
   unknown relationships unknown.
4. Record content-review approval in a separate coordinator log: candidate
   ID, reviewed record checksum, reviewer alias, date, approved/deferred/rejected,
   rationale, and revision history. This approval concerns inclusion and source
   fidelity, not a gold verdict. Do not convert pending collection checks into
   independent annotation or overwrite previous review decisions.
5. Keep both annotators away from system predictions, expected labels and each
   other's submissions. Freeze the same evidence bundle and annotation policy
   before distributing approved material.

## Later import into the 90-claim pilot

Phase 3 adds an explicit reviewed-candidate importer and version-bound human
review packets. Follow [`../candidate_reviews/README.md`](../candidate_reviews/README.md).
Run `python -m evaluation.annotation.candidate_review report` and
`python -m evaluation.annotation.import_candidates --dry-run` before any
future authorized import. The default does not write pilot files. Current
packets contain no decisions and all candidates are blocked for missing approval.
Only an explicit `--apply` with current approved checksums may append records,
retaining stable IDs and `unannotated` status.
Preserve the collection batch and separate approval log, record before/after
checksums, and confirm no claim/evidence ID collision or duplicate family.
Retain topic/source-check metadata in the coordinator collection archive;
do not add unsupported fields to the fixed claim schema.

Run `python -m evaluation.annotation.validate_pilot` and preparation QC after
each authorized import. The full-pilot QC count requirement will appropriately fail until
90 claims exist. Do not set the manifest to `ready` or distribute incomplete
material. Do not edit frozen claims after sealing submissions; any change
requires a documented new collection/pilot revision and integrity workflow.
Do not create annotator records, adjudications, final splits or gold labels
as part of import. Independently collected human labels remain separate from
the collector's inclusion decisions.
