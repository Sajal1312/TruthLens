# Actual validation record

## Tests executed

Before edits:

```sh
.venv/bin/python -m pytest -q tests/test_candidate_collection.py tests/test_candidate_approval.py tests/test_automated_source_review.py
```

**51 passed in 2.84 seconds.**

After adding the follow-up checks and review-sheet generator:

```sh
.venv/bin/python -m pytest -q tests/test_review_followup.py tests/test_automated_source_review.py tests/test_candidate_collection.py tests/test_candidate_approval.py
```

**63 passed in 7.20 seconds**, including 12 new tests. They check exact claim and
evidence coverage, blank human decision spaces, unchanged input objects,
separate partial/unresolved status counts, stale versions, duplicate/missing IDs,
invalid references, missing-date coverage, unsupported date precision, blocked
source handling, forbidden human/gold fields and output-overwrite refusal.

Final broader annotation-related suite:

```sh
.venv/bin/python -m pytest -q tests/test_annotation_framework.py tests/test_pilot_quality_control.py tests/test_candidate_collection.py tests/test_candidate_approval.py tests/test_automated_source_review.py tests/test_review_followup.py
```

**94 passed in 22.09 seconds.** No test failures were observed. This is the
annotation-related suite, not a production/NLI benchmark or live UI test.

## Other checks executed

```sh
PYTHONPYCACHEPREFIX=/tmp/truthlens-followup-pycache .venv/bin/python -m compileall -q evaluation/annotation/review_followup.py tests/test_review_followup.py
git diff --check
```

Both passed. The temporary cache avoids writing to macOS's external Python cache.
New files additionally passed `git diff --no-index --check /dev/null PATH`.

Explicit offline schema/integrity checks passed:

- All annotation schema definitions validated with Draft 2020-12.
- All 30 current candidates and 30 original blank human review packets passed
  their existing schemas.
- Follow-up schema, all nine candidate-version checksums, exact flagged-set
  coverage, 41 unique source-check IDs/URLs and all 27 missing-date references
  passed. Publication precision remained distinct from original-day fields.
- Prior automated assessments remained valid for the same candidate versions.
- Saved summary and all-30 review sheet reproduced exactly from `followup.json`.
- Every new JSON artifact parsed successfully.
- SHA-256 comparison of **129 pre-existing protected files found zero changes**.
  These cover the old candidate collections, blank packets, previous assistance,
  pilot records, application and core verification modules, and approval/import
  helpers. Existing unrelated workspace edits were preserved.
- Read-only approval report still shows **30 pending, zero approved and zero
  import-eligible**. The real pilot still contains zero claims.

## Exact new files

No pre-existing file was edited. Eight files were created:

1. `evaluation/annotation/review_followup.py`
2. `evaluation/annotation/schemas/source_review_followup.schema.json`
3. `tests/test_review_followup.py`
4. `evaluation/annotation/candidate_reviews/automated_assistance/2026-11-02/followup.json`
5. `evaluation/annotation/candidate_reviews/automated_assistance/2026-11-02/prepared/human_review_sheet.md`
6. `evaluation/annotation/candidate_reviews/automated_assistance/2026-11-02/prepared/summary.json`
7. `evaluation/annotation/candidate_reviews/automated_assistance/2026-11-02/README.md`
8. `evaluation/annotation/candidate_reviews/automated_assistance/2026-11-02/VALIDATION.md`

## Scope and limitations

Web-tool checks are recorded separately in the source log. Of 41 requested URLs,
37 returned readable content and four were inaccessible. This is not a claim of
37 independent publishers or measured HTTP-200 responses. No Tavily calls,
credentials, held-out data, NLI inference or Streamlit tests were used. The full
WHO report, empirical datasets and complete provenance chains were not audited.

Four context gaps have documented remedies, one original-source issue has an
authoritative replacement proposal, and four scope/evidence issues remain
unresolved. **No remedy was applied to a candidate version.** All 27 original
missing publication-day fields remain null. No authentic human decision or gold
label was generated, and no review submission, adjudication or import occurred.
