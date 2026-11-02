# Source-issue follow-up and human approval preparation

Automated assistance checked on **2 November 2026**. No human approval, gold
label, independent annotation, adjudication or pilot import was created.
All old candidates, evidence, reports and blank review packets were preserved.

Start with [the all-30 human review sheet](prepared/human_review_sheet.md).
It contains exact claim wording, current version checksums, original source and
evidence IDs, prior automated findings, follow-up findings, remaining concerns,
recommended inclusion routes and **blank** human decision/rationale spaces.
It is a scratch worksheet, not a submittable approval record. Save your own copy
before recording decisions; keep the generated original as an audit artifact.

## What was resolved, and what was not

There were nine flagged candidate-level issues. Counts below describe research
assistance, **not completed changes to the frozen evidence bundle**:

| Candidate | Follow-up outcome | Remaining human action |
|---|---|---|
| p2-env-002 | Context gap resolved: full WMO quotation and Paris Agreement section distinguish annual exceedance from the long-term goal. | Review a versioned context expansion; saved evidence still contains only the trailing clause. |
| p2-tech-002 | Context gap resolved: NIST section 3.1.5 identifies the multi-factor OTP occurrence. | Preserve the correct section/definition in the reviewed bundle; do not use the single-factor occurrence. |
| p2-general-002 | Context gap resolved: preceding Oxford sentence identifies Marie Curie. | Add the antecedent through a versioned context revision. Official Nobel checks were blocked; acknowledge secondary-source status. |
| p2-general-005 | Context gap resolved: Cosmicopia question 99 identifies the Great Wall; another official NASA FAQ explicitly names it. | Review a versioned context expansion or source addition; distinguish Moon/naked eye from orbital photography. |
| p1-general-004 | Partial resolution: authoritative replacement found in BIPM's accessible SI Brochure, section 1.1. | Original webpage still times out. Review replacement evidence and the operative resolution; never mark the inaccessible original verified. |
| p1-env-003 | Unresolved: UNEP's annual wording versus the abstract's 2016 estimate. | Decide temporal scope and provenance; direct citation relationship was not established. |
| p2-env-003 | Unresolved: unconditional before-2100 wording versus conditional and method-dependent projections. | Define intended scope/as-of conditions and comparability; no future event was established. |
| p2-env-004 | Unresolved: 2019 qualified risk language does not establish categorical present-day harmlessness. | Decide whether a deliberately insufficient bundle is appropriate; no claim of either harmlessness or harm is established here. |
| p2-general-003 | Unresolved: potential habitability is not detection of life. | Decide whether a deliberately insufficient bundle is appropriate; absence of detection in this bundle is not absence of life. |

Thus **four context gaps have identified remedies, one is partially resolved,
and four remain substantively unresolved**. Five of the nine still lack a full
research resolution (the partial case plus four unresolved cases). Adoption of
any remedy remains pending. Do not report nine repaired candidates or increased
accuracy from this work.

Updated preliminary routes across all 30:

- **21:** review the current candidate personally, with the previous limitations.
- **5:** a specific context/source revision is prepared for consideration; obtain
  a new version-bound human decision after adopting any change.
- **4:** hold for unresolved scope/evidence review (two temporal/scope issues,
  two insufficient-evidence issues).

The original saved classification remains **21 suitable / 7 revision / 2
insufficient** because no candidate version was silently altered. An inclusion
review is not a verdict: a claim challenged by its evidence can still be a useful
annotation candidate. Humans may deliberately include insufficient/conflicting
bundles when the protocol defines them clearly.

## Source and date checks

`followup.json` is the strict machine-readable source log and nine version-bound
follow-ups. `prepared/summary.json` contains reproducible counts. The review sheet
also lists every checked URL, its status, locator and finding.

- **41 distinct requested URLs checked:** 37 returned readable content; four
  were inaccessible (original BIPM page and three official Nobel resources).
  The Europa alias and canonical page count as separate requested URLs, not
  independent sources. These totals differ from the earlier 37-source inventory.
- All **27 original unknown publication-day fields**, across **26 distinct
  URLs**, were rechecked using visible text and date/update lookups. No exact
  original publication day was newly established. They all remain null.
- NIST's official catalog gives **July 2025**, not a day. The SI Brochure has
  edition year 2019 and version V4.01 dated June 2026. These do not supply exact
  original page publication days. NASA, NOAA, EPA, Python and Geoscience update
  dates are kept separate from publication dates.
- A new WHO publication overview is dated **30 August 2022** and reviews data
  through December 2021, identifying further uncertainties. That is a different
  source, not a new date for the saved 2019 source. Only its overview was checked;
  the full 154-page report was not downloaded or audited.
- BIPM's English brochure was opened from its official landing page. Section 1.1
  is on printed page 121 / PDF page 11. The historical resolution's operative
  decision takes effect 20 May 2019, distinct from its 2011 considering clause.
- Three attempted Nobel primary resources returned 403. They are logged as
  inaccessible, not silently substituted with search snippets or invented data.

The web tool may return cached/indexed rendered text. “Opened” is not a measured
HTTP-200 result, uncached origin response, full DOM/metadata audit or archival
snapshot. The earlier passage checks are dated 1 November; this follow-up is
targeted and does not claim to have reverified every original passage anew.
Search snippets alone were not counted as verified evidence. Source dependence,
underlying calculations and scientific model comparisons were not exhaustively
audited. Different domains or a second NASA/BIPM page do not establish independence.

## Complete authentic human review

1. Save a personal copy of the review sheet. Read each exact claim and the linked
   original sources; inspect the identified context. Record your own decision
   and rationale in the blank spaces. Supply your own alias and actual review
   time; none has been entered for you.
2. For a current candidate you personally accept, complete its existing
   `candidate_reviews/drafts/CANDIDATE_ID/review.json` following the
   [human workflow](../../README.md). Address all per-evidence status, date and
   provenance fields. Unknown dates may remain unknown with a reason;
   “verified undated” is not a substitute for failing to find a date.
3. For a candidate needing a changed passage, source or context, record
   `revision_required` on the current version. Preserve that version and packet.
   A coordinator must prepare a separately versioned collection and new blank
   packet through the existing collection workflow, review its new checksum,
   and adopt it explicitly before it can be approved against current records.
   The proposed notes in this folder are not evidence silently added to the
   existing packet. Do not claim a remedy was adopted merely by reading it.
4. Only after **you** complete a genuine current-version review, run from the
   project directory:

```sh
source .venv/bin/activate
python -m evaluation.annotation.candidate_review submit --file evaluation/annotation/candidate_reviews/drafts/CANDIDATE_ID/review.json
python -m evaluation.annotation.candidate_review report
```

Replace `CANDIDATE_ID` with the real folder name. These commands are provided for
future human use; no review was submitted during this task. The scratch sheet
and machine follow-up JSON cannot be submitted as approval records. No import
command is part of this task. Keep these interpretive recommendations away from
later blinded annotators; distribute only the explicitly approved frozen bundle.

## Offline validation / regeneration

```sh
python -m evaluation.annotation.review_followup --followup evaluation/annotation/candidate_reviews/automated_assistance/2026-11-02/followup.json --previous evaluation/annotation/candidate_reviews/automated_assistance/2026-11-01/assessments.json
```

This checks schemas, saved checksums, references, missing-date coverage and
consistency. It does not fetch websites, choose decisions or approve anything.
For a new report copy, add `--output-dir /tmp/truthlens-followup-copy` using a
directory that does not already exist. Existing outputs are refused. No new
dependencies, application changes or submission-integrity changes were needed.
