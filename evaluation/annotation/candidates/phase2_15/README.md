# Phase 2 collection and evidence review

Phase 3 now provides blank review packets, an append-only inclusion-review
registry, status reports and an explicit dry-run importer. Use
[`../../candidate_reviews/README.md`](../../candidate_reviews/README.md) for
current approval/import instructions; no candidate has been approved or imported.

Collected/rechecked on 2026-11-01. All 30 candidates across both batches remain
unannotated and await human approval. Source fidelity was checked by the
collector using public web open/find tools; this is not independent human
annotation. The offline report checks saved structure and hashes and does not
perform live verification or NLI classification.

## Baseline and changes

Before editing, candidate/QC tests passed (18 tests), and Phase 1 had 15 claims,
15 passages, zero QC errors and 19 warnings. Original files and reports were
preserved under `../phase1_15/history/before_phase2_*`. Original claim wording
and original excerpts were not changed. Source title/publisher and context
checks were recorded for all 15 original documents.

Direct Requests retrieval failed DNS resolution for all original sites in the
local runtime. Those failed attempts are preserved separately from successful
web-tool excerpt checks in `../phase1_15/source_rechecks.json`. Consequently,
raw HTML date metadata could not be inspected locally. Visible page dates and
the NIST publication catalog were checked instead. All fourteen originally
unknown exact publication dates remain unknown: RFCs give month/year; the
NIST identity catalog gives July 2025; NOAA and NASA show update dates; other
pages do not establish an original publication day. No update, build, event
or access date was substituted for publication date.

Seven Phase 1 additions are traceable supplementary documents:

| Candidate | Addition | Limitation |
|---|---|---|
| Aluminum recycling | NIH energy-saving summary | Underlying calculation and independence not established |
| Plastic leakage | Borrelle et al., Science abstract via PubMed | Estimate is for 2016; review UNEP's broader annual framing. First online 17 September 2020, issue 18 September |
| Montreal Protocol | UN Treaty Collection registry | Same treaty origin; records conclusion and entry into force separately |
| NIST PQC announcement | FIPS 203 publication catalog | Only one of the three standards; partial coverage, same institution |
| Python optional GIL | PEP 703 | Design/proposal wording with Python 3.13 header; not independent evidence of installed behavior |
| Mars moons | ESA Mars Express article | A separate institutional document, not proven independent scientific evidence |
| SI constants | Original CGPM resolution | Historical considering-clause referring to the 2011 proposal; read the later decision for current applicability |

The other eight candidates retain one passage. No useful additional vetted
excerpt was admitted. In particular the linked Gaia release page returned
451, and a UN ocean page returned 403. Same-RFC mirrors would not establish
independent support. Remaining source work is a review queue, not evidence
that was silently assumed to exist.

## Phase 2 wording and challenge coverage

This batch has five environment, five technology, and five general candidates.
The review report lists every claim, source URL, role, locator, date and concern.
It contains 16 excerpts: the AMOC candidate has two published projections.
The older paper is primary research; the newer accessible passage is the
2025 study team's Met Office communication, because the newer Nature page
failed a cookie redirect. Compare definitions, scenarios, time intervals and
model assumptions before treating them as a genuine same-proposition conflict.
Neither projection is an observed future event.

Some claims are collector-worded verification propositions or explicit scope
and double-negation paraphrases of documented facts. They are not presented as
verbatim organic claims or publisher assertions. The SHA-1 and Nobel examples
exercise double negation through transparent paraphrases. The Europa and
microplastic propositions concern open or qualified evidence; habitability,
absence of observed harm and established presence/absence are different.
Challenge tags identify review tasks and do not assign gold labels.

All eleven planned challenge tags occur across the combined collection.
This is a purposive, visible development collection, not independent evidence
of model generalization or a representative verdict distribution. Do not tune
TruthLens on the collection and later call it an untouched final test set.

## Provenance and date cautions

The same NIST identity document supplies different sections for a Phase 1
password claim and a Phase 2 MFA claim. Both use one provenance group. Keep
that source group together in any later split. Phase 1 supplementary source
groups are linked by recorded topic/institutional relationships, with
`related_suspected` for inferred relationships and `same_origin` only where
the common original record is observed. None is marked independently verified.
The two Venus propositions also share a topic group, as do the NIST PQC
announcement and later HQC-selection claim.

The SHA-1 announcement body is dated 23 February 2017, while CWI labels the
page publication 27 February 2017; both dates are preserved separately. The
HQC claim is explicitly as of March 2025 and preserves a forecast for 2027.
The Venus comparison specifies sidereal rotation rather than its roughly
117-day solar day. The archived NASA Great Wall response is kept version-scoped;
dates from neighboring answers were not assigned to it. Primary Nobel pages
were inaccessible, so the Curie excerpt is explicitly a secondary museum summary.

## Reproduce reports and review

From the project root:

```sh
source .venv/bin/activate
python -m evaluation.annotation.review_candidates
python -m evaluation.annotation.review_candidates --directory evaluation/annotation/candidates/phase2_15
python -m evaluation.annotation.review_candidates --combined
python -m pytest -q tests/test_candidate_collection.py tests/test_pilot_quality_control.py tests/test_annotation_framework.py
```

Combined outputs are `../combined_review/review_report.json` and `.md`.
Publisher document counts deduplicate exact source URLs; publisher IDs and
hostnames are descriptive metadata, not verified editorial independence.
The source-check notes contain unresolved semantic/version warnings in addition
to the automated QC findings. All candidates still need human approval.

A coordinator should reopen sources, retain surrounding qualifications,
resolve scope/date concerns and document inclusion approval with the reviewed
record checksum. Preserve previous decisions. Add further primary evidence
where needed. Do not use these collector notes as annotator gold labels.
Only after content review should approved, unchanged unannotated records be
manually imported into `pilot_90`, checking IDs, families and provenance links.
Then validate the pilot and run QC. Freeze the same bundle for both independent
annotators; keep submissions, adjudication and gold decisions separate.
This task performs no import and creates no dataset split.
