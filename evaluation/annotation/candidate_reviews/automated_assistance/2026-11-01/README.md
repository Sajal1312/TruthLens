# Automated source assistance — 1 November 2026

These are AI-generated preliminary inclusion-review aids. They are **not human
approvals, independent annotations, gold verdicts, or NLI/model predictions**.
No human identity or review timestamp was supplied. `automated_checked_on` records
the machine inspection date, not an independent review date.

## What was actually checked

All 30 staged candidates and 38 saved passages were inspected. The web tool was
asked to open all 37 distinct original URLs, then locate saved fragments and
inspect relevant surrounding context and metadata. The shared NIST document was
opened once and both distinct passages were checked. It counts as one source URL.

- 36 distinct original URLs returned readable source content.
- 37/38 saved passages were located: 29 exact fragments, four with formatting
  normalization, and four assembled from adjacent headings/date fields,
  registry cells, or bullets. An exact fragment is not necessarily a standalone
  quotation or a sufficient piece of evidence.
- The BIPM defining-constants URL timed out on both attempts. Its passage is
  **incomplete**, even though the historical resolution page was accessible.
  Previous collector checks were not substituted for current verification.
- All 11 existing publication days were corroborated in the retrieved source
  text. The other 27 candidate publication dates remain unknown: 26 original days
  were not established and one source was inaccessible. No dates were repaired.
- Preliminary recommendations: 21 suitable for a human inclusion decision,
  seven needing revision/context, two with insufficient evidence for the stated
  proposition. **None is approved by this report.**

The tool can return cached/indexed rendered text. This is not a direct HTTP
status measurement, full DOM/structured-metadata audit, archival capture, or
proof that an origin server returned the same content at an exact instant.
No local requests/Tavily calls, secrets, NLI inference, or held-out records were
used. No source code or downloaded webpage instructions were executed.

Titles and publishers are recorded as observed document identities, including
minor heading variants (for example, NASA's “Mars Moons” versus the collector's
“Moons of Mars”). They are not authenticated publisher-ownership certifications.
The Nature article returned readable text despite a cookie-error query in the
redirect. Its saved abstract fragment and publication field were readable.

## Files and interpretation

- `assessments.json`: all 30 version-bound machine assistance records.
- `reports/worksheets/<candidate_id>.json`: a separate assistance sheet per claim.
- `reports/report.md`: consolidated all-30 table, source URLs, exact excerpt-check
  statuses, observed titles/publishers, dates, context and provenance notes.
- `reports/summary.json`: machine-readable inspection counts.
- `../../../schemas/automated_source_assessment.schema.json`: strict assistance
  schema, separate from the human review schema.

Each record includes the SHA-256 of the full current claim/evidence record.
Offline validation rejects stale versions, missing or duplicate coverage,
changed URLs, unsupported publication-day repairs, human/gold fields and
inaccessible sources described as verified. It checks consistency of the saved
observations; it does not independently prove that an AI inspection was correct.

Recommendations assess **dataset inclusion quality**, not truth. Opposing
evidence is useful for annotation: the HTTPS legitimacy claim remains suitable
for human review even though the FTC passage challenges it. The Europa passage
is a habitability mission goal, not evidence of life; absence of a detection in
this bundle does not establish absence of life. A human may intentionally
include a limited-evidence candidate if the protocol and scope are clear.

## Human review priority

Start with these high-priority records:

| Candidate | Required attention |
|---|---|
| candidate-p1-env-003 | Reconcile UNEP's annual framing with a research estimate for 2016; a citation chain was not established. |
| candidate-p1-general-004 | Retry inaccessible BIPM page; the accessible fragment describes the 2011 proposal rather than the operative 2019 definition. |
| candidate-p1-general-005 | Recheck the Gaia forecast at approval and freeze an as-of reference; expected release is not completion. |
| candidate-p2-env-003 | Resolve unqualified future certainty, study assumptions and projection horizons before calling the passages a conflict. |
| candidate-p2-env-004 | Restore WHO's limited-information qualifier and address the 2019/current-exposure mismatch; categorical harmlessness is not established. |
| candidate-p2-tech-004 | Preserve selection date and the historical 2027 expectation; do not reinterpret as a completed standard. |
| candidate-p2-general-003 | Clearly distinguish potential habitability from detection; decide whether a deliberately insufficient bundle is appropriate. |

Other revision recommendations concern standalone context: WMO's missing leading
qualification (`p2-env-002`), the **multi-factor** OTP section (`p2-tech-002`),
the Marie Curie pronoun antecedent (`p2-general-002`) and the Great Wall question
antecedent (`p2-general-005`). Do not silently edit the candidate or old packets.

## Provenance and dependence

The existing combined QC report records eight shared provenance groups. This
inspection does not certify any source pair as independent. In particular:

- EIA/NIH's matching percentage is not two independent measurements; NIH has
  older statistics and a visible site-currency warning.
- UNEP and the Science abstract have matching ranges but a different temporal
  presentation; their direct citation relationship was not established.
- The treaty overview/registry concern one treaty; the two NIST standards
  passages concern one release program.
- Python's glossary explicitly links PEP 703: a shared design/implementation
  lineage. BIPM pages share institutional origin.
- `p1-tech-004` and `p2-tech-002` reuse exactly the same NIST source URL. Keep them
  grouped when designing future splits.
- The AMOC announcement describes its research team's paper. Different teams,
  domains and methods alone do not demonstrate independent data or a like-for-like
  contradiction. NASA/ESA summaries likewise do not establish independence of
  the underlying measurements.

No additional exact duplicate claims or copied evidence passages were observed
in this inspection. That is not an exhaustive syndication or plagiarism audit.
Use the existing QC grouping observations as well as these notes before splitting.

## Revalidate without fetching sources

From `~/Downloads/TruthLens`:

```sh
source .venv/bin/activate
python -m evaluation.annotation.automated_source_review --assessments evaluation/annotation/candidate_reviews/automated_assistance/2026-11-01/assessments.json
```

This only validates saved observations against the current candidate checksums.
It does **not** reopen websites or claim fresh verification. To create another
report copy, add `--output-dir /tmp/truthlens-assistance-review-copy` using a
directory that does not yet exist. Existing output directories are refused.
The stored report's relative inspection-notes link assumes the original layout.

## Complete authentic human decisions

1. Read the assistance sheet alongside
   `candidate_reviews/drafts/CANDIDATE_ID/candidate.json`. Open each original URL
   yourself, particularly the flagged context and dates. A real reviewer must
   confirm or correct the preliminary observations.
2. Complete the existing `drafts/CANDIDATE_ID/review.json` **yourself** using the
   [human workflow](../../README.md). Supply your own alias, unique review ID,
   actual timezone-bearing timestamp, assessments and inclusion rationale.
   Address every evidence record. Unknown publication dates are acceptable only
   with an honest rationale; do not mark a source “verified undated” merely
   because its original day was not found.
3. If the excerpt, scope or date needs changing, record `revision_required` on
   the current version. Preserve the old candidate/packet, make a separately
   versioned revision through the existing collection process, and obtain a
   new checksum-bound human decision. These assistance files do not authorize
   changes or carry approvals forward.
4. Submit only a genuinely completed human worksheet:

```sh
python -m evaluation.annotation.candidate_review submit --file evaluation/annotation/candidate_reviews/drafts/CANDIDATE_ID/review.json
python -m evaluation.annotation.candidate_review report
```

Replace `CANDIDATE_ID` with the actual folder name. Never submit the machine
assistance worksheet: it intentionally cannot validate as a human review.
No import command is included here; importing into the real pilot remains a
separate authorized task after authentic human decisions.

## Remaining limitations

Human approval, source independence, underlying empirical calculations and
complete source accuracy remain unestablished. Web content can change, primary
datasets were not audited, and excerpts can omit context despite exact matches.
Collector-written negation/quantifier variants must remain disclosed as such;
they are not naturally occurring quoted claims. Recommendations are AI judgments,
not independent research labels. Source-review assistants should not show these
interpretations to later blinded annotators; distribute only the approved frozen
claim/evidence bundle under the independent annotation protocol.
