# Validation record

All checks were offline except the explicitly described web-tool source
inspection. No Tavily requests or NLI verdict evaluations were performed.

## Baseline

Before editing, the existing candidate tests passed:

```sh
.venv/bin/python -m pytest -q tests/test_candidate_collection.py tests/test_candidate_approval.py
```

Actual result: **42 passed in 2.45 seconds**.

## Implementation checks

```sh
.venv/bin/python -m pytest -q tests/test_annotation_framework.py tests/test_pilot_quality_control.py tests/test_candidate_collection.py tests/test_candidate_approval.py tests/test_automated_source_review.py
PYTHONPYCACHEPREFIX=/tmp/truthlens-source-review-pycache .venv/bin/python -m compileall -q evaluation/annotation/automated_source_review.py tests/test_automated_source_review.py
git diff --check
```

The annotation-related test suite passed **82 tests**, including nine new
automated-assistance tests. This is not a full production/NLI suite or live
Streamlit validation. The source-inspection record is not an accuracy benchmark.

Syntax compilation passed with its cache directed to a temporary directory.
The initial compilation attempt could not write to macOS's configured external
Python cache; the retry used `/tmp` without changing project configuration.

Tracked-file `git diff --check` passed. New files were additionally checked with
`git diff --no-index --check /dev/null PATH`; an extra trailing blank line in
the generated Markdown report was corrected in the report renderer and report.

Additional explicit validation:

- All 30 candidates passed the existing claim-record schema.
- All 30 original human worksheets still passed the strict blank-draft schema.
- All 30 assistance records passed their separate schema and coverage,
  candidate-checksum, evidence-ID, source-URL and publication-day consistency checks.
- All annotation JSON schemas passed `Draft202012Validator.check_schema`.
- Generated summary, report and all 30 per-candidate sheets matched their saved
  assessment inputs exactly. Every new JSON artifact parsed successfully.
- SHA-256 comparison of 89 pre-existing protected files found **zero changes**:
  candidate collections, original draft packets, real pilot files and the
  application, verifier, NLI, evidence-quality, approval and import modules.
- Read-only human approval report: **30 pending, zero approved, zero eligible**.

The original 90-claim pilot remains empty. No candidate was revised or imported;
no review decision, annotator submission or adjudication was created. Existing
unrelated workspace edits were preserved. No held-out dataset or API secret was
read. No dependencies were added.
