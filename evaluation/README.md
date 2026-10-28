# TruthLens offline evaluation

This is a small, source-control-ready pilot set for repeatable diagnostics. It is not a representative benchmark, and its scores must not be described as general accuracy. The current workspace has no `.git` metadata, so these files are not yet tracked in a Git history. Running the evaluation does not query Tavily or access API credentials. The NLI mode uses the locally cached, pinned model; missing model files cause an explicit `NOT MEASURED` exit rather than a download or rule-based substitution.

From the project root, activate the existing environment and run:

```sh
source .venv/bin/activate
python -m evaluation.run_evaluation --split development
python -m evaluation.run_evaluation --split diagnostics --output evaluation/results/semantic_diagnostics.json
python -m evaluation.run_evaluation --split held_out --output evaluation/results/held_out.json
python -m evaluation.benchmark_resources --repeats 5 --output evaluation/results/resources.json
```

Use `--split all` only for a combined diagnostic. Run development first to check that the harness works. Held-out labels must not be used to adjust production rules, thresholds, or the model. If the implementation changes after viewing held-out results, create a new future holdout rather than tuning to this one.

## Files and split

- `data/development.jsonl`: nine development cases for known edge cases, with one gold case for each verdict class.
- `data/diagnostics.jsonl`: sixteen developer-authored semantic diagnostics. These are partly synthetic controlled fixtures, deliberately visible, and not blind or independent test cases. They cover claim splitting, negation, passive voice, reversed relations, compound evidence, historical/hypothetical context, duplicates, date mismatch, conflicts, missing publisher metadata, and lexical overlap.
- `data/held_out.jsonl`: three newly curated cases covering support, contradiction, and no evidence, based on NASA/ESA Mars-moon pages and a controlled private-event case.
- `data/held_out_inspected_diagnostic.jsonl`: preserved copy of the former set, which was inspected during earlier development and must not be presented as unseen.
- `metrics.py`: dependency-free confusion matrices and summary metrics.
- `run_evaluation.py`: fixed-passage adapter to `assess_evidence_nli()` and report generator.
- `benchmark_resources.py`: local model load and inference timing plus process-level peak RSS; no search requests.
- `results_template.md`: report format that distinguishes measured from unmeasured values.
- `annotation_guide.md` and `second_annotator_template.csv`: label guide and blank independent-review workflow; no second-annotator results are claimed.

Development cases cover supported evidence, historical attribution, hypothetical framing, lexical overlap without the claimed relation, conflicting assertions, copied text, date mismatch, and a qualified barycenter statement. Held-out cases cover a supported claim, a contradicted claim, and an unrecorded private event without evidence.

**Held-out status for this version:** the former set was inspected during earlier development and is preserved as `held_out_inspected_diagnostic.jsonl`; it is not unseen. The current three cases are newly curated for this evaluation iteration and have not been used to tune production logic in this iteration. They are still developer-authored, their labels are visible, and the set is tiny; this is neither blinded nor statistically powered. Freeze the code and labels before recording results. Do not tune against those results; if they drive a code change, retire this split and prepare a future holdout.

## JSONL schema

Each line is one independent claim case:

```json
{
  "case_id": "stable_unique_id",
  "split": "development | diagnostics | held_out",
  "claim": "one claim passed to TruthLens",
  "tags": ["historical"],
  "expected_final_verdict": "SUPPORTED | CONTRADICTED | INCONCLUSIVE",
  "rationale": "why this is the expected pipeline assessment",
  "evidence": [{
    "evidence_id": "stable_id",
    "passage": "text passed unchanged to the existing assessor",
    "expected_relevance": "relevant | weakly_related | unrelated",
    "expected_stance": "SUPPORTS | CONTRADICTS | NOT ENOUGH INFORMATION",
    "source": {
      "kind": "public_excerpt | synthetic_fixture",
      "title": "source title or explicit constructed-fixture label",
      "url": "real URL for public excerpts; null for synthetic fixtures",
      "publisher_id": "publisher identity, null for synthetic fixtures",
      "checked_on": "date the cited page text was checked, null for fixtures",
      "independence_basis": "why publisher identity differs, or why not independent"
    }
  }]
}
```

Expected stance is the gold relation of the passage to the stated claim, not a truth label for the world. Historical and hypothetical mentions are generally labeled NOT ENOUGH INFORMATION when they do not assert the present-day proposition. Date-mismatched excerpts can have gold CONTRADICTS while the current pipeline conservatively excludes them and therefore produces an effective abstention. Expected final verdict means the appropriate system output under this evidence policy: lack of evidence is Inconclusive, never Contradicted.

Public excerpts have a title, direct source URL, check date, and a short passage. They are citations for the fixture text only; the script does not fetch/refresh them. Synthetic passages are explicitly labeled and have no citation URL. The evaluator internally gives a `.invalid` placeholder URL only so the existing URL-based assessor can be exercised; it is not shown as a real citation. Directional gold cases require two unique public URLs, but URLs and publisher labels do not establish independent reporting. Same-publisher cases are allowed so experimental grouping can be compared. Exact duplicates are included; neither duplicates nor different URLs alone count as independent confirmation.

## Metrics

The report contains counts and a fixed-label confusion matrix (rows are expected labels, columns are predictions) for:

- **Passage relevance:** macro precision/recall/F1 across relevant, weakly related, unrelated. Pipeline “Directly relevant candidate” and “Different time period” map to relevant for this coarse retrieval metric; the latter remains visible in passage status. A more nuanced relevance annotation is future work.
- **Effective passage stance:** macro precision/recall/F1 over SUPPORTS, CONTRADICTS, NOT ENOUGH INFORMATION after the production relevance/context/date/confidence/margin/dedup filters. Uncertain, excluded, duplicate-excluded, and unassessed passages map to NOT ENOUGH INFORMATION.
- **Raw NLI stance:** same metrics against the raw recognized model label, only when a model label was emitted. The report records its smaller denominator. This distinguishes model classification from downstream filtering.
- **Final verdict:** confusion matrix, accuracy and macro-F1 across Supported, Contradicted, Inconclusive.
- **Selective behavior:** selective accuracy is exact expected/predicted match among directional predictions only; coverage is the fraction of cases receiving Supported or Contradicted; abstention rate is the fraction predicted Inconclusive.
- **Stress groups:** case and passage counts plus final-label accuracy for tags such as historical, hypothetical, irrelevant, conflicting, duplicate, and date-sensitive.
- **Publisher diagnostics:** for counted passages, the runner reports declared publisher IDs, URL counts, and the largest publisher share. These annotations flag concentration but cannot prove editorial independence and do not alter any verdict.
- **Aggregation comparison:** alongside unchanged production verdicts, the report computes evaluation-only modes: one vote per normalized declared publisher (all missing or malformed IDs share one unknown group) and a stricter mode requiring distinct declared publisher IDs. It does not infer publisher identity from hostnames. Both preserve the two-vote threshold and abstain on mixed directions. Missing or malformed IDs cannot count in strict distinct-publisher mode. These are provenance grouping diagnostics, not proof of independence. Each mode reports per-class metrics, class distributions, coverage, abstention, selective accuracy, and errors grouped by case tags.
- **Semantic interpretation comparison:** the evaluation invokes the existing default assessor and an opt-in experimental assessor on the same fixed passages and cached model. The experiment preserves noun lists and disjunctions, splits only coordinated independent clauses, and tests an explicit reversed motion relation as contradiction after the existing relevance, context, and confidence gates. Passive “X is orbited by Y” wording is normalized in that experimental relation check. This is an evaluation path, not the production default. It reports confusion matrices, per-class precision/recall/F1, macro-F1, coverage, abstention, selective accuracy, error categories, and component-level experimental assessments.

Undefined metrics are represented as `null` where mathematically undefined. Per-class support is explicit, and macro-F1 averages only labels present in gold data; the report lists the included labels and class count. Empty accuracy/macro-F1/selective values are `null`. Do not compare headline scores without class counts, held-out size, and split protocol. With only three held-out claims, all metrics are descriptive and statistically unreliable; per-class metrics have at most one example. The set is a smoke evaluation, not a statistically powered benchmark.

For compound evidence, the current passage-level stance metrics use the first assessed component because the dataset does not yet have component-specific gold annotations. The reports retain every experimental component assessment for qualitative review; do not interpret the passage-level aggregate as a component-level benchmark.

## Methodology text for project report

“TruthLens was evaluated using a manually labeled pilot corpus of claim–passage examples prepared for source control. The corpus separates development diagnostics from a small held-out set. Public passages include direct source URLs and a check date; controlled edge-case passages are labeled synthetic and are not presented as real-world evidence. Expected labels describe relevance, passage stance, and the appropriate final system output under a conservative abstention policy. The offline runner passes each fixed passage through the existing NLI assessment and aggregation pipeline without making search requests. It reports class-wise confusion matrices and macro-F1 for relevance, raw NLI stance, effective stance, and final verdict, along with selective accuracy, coverage, and abstention rate. Due to the small, purpose-selected sample, results are exploratory and cannot establish general performance. Model scores are not probabilities that claims are true.”

## Resource measurement

Run `python -m evaluation.benchmark_resources --repeats 5` to time local model loading and repeated inference on three fixed development passages. It records Python/platform/architecture/model revision, timed run count, one warm-up inference per probe, timing method, per-probe and combined latency summaries, and process peak resident-set size. It explicitly marks end-to-end verification as NOT MEASURED. On macOS the standard library reports `ru_maxrss` in bytes. This is a process high-water measurement that includes Python and model loading; it is not an inference-only memory delta and may not capture every accelerator allocation. The script does not call Tavily, read API keys, or download a missing model. Energy is NOT MEASURED because no reliable energy telemetry is configured. Do not infer energy or carbon savings from local runtime alone.

## Current methodological limitations

- Labels are human-authored pilot annotations, not independently adjudicated by multiple annotators; no inter-rater agreement is estimated.
- Only a few public-source excerpts are included, and their pages may change. There is no systematic sampling frame or broad domain/language coverage.
- Publisher separation is recorded but does not establish independent original reporting. The current production aggregator counts distinct URLs/passages, not verified provenance chains.
- The task mixes system quality with model behavior and heuristic filters. Raw and effective passage results are therefore reported separately.
- Search/retrieval recall, ranking, freshness, Tavily error rates, and UI behavior are not evaluated by this offline harness. Those require a separately logged, privacy-safe live retrieval study and are intentionally not run here.
- `Different time period` is mapped into the broad relevant class for one metric; date reasoning deserves a richer annotation taxonomy.
