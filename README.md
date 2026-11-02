# TruthLens

TruthLens is a small Streamlit demo that searches the web with Tavily and presents sources with a conservative, explainable preliminary assessment. It is not an authoritative fact checker. Search snippets are untrusted evidence and are displayed as text; the app never runs webpage instructions or downloaded code.

## Run on a Mac

Open Terminal, then enter these commands one at a time:

```sh
cd ~/Downloads/TruthLens
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install -r requirements.txt
mkdir -p .streamlit
```

Get a Tavily API key by creating an account at [tavily.com](https://tavily.com/) and copying an API key from its dashboard. Check Tavily's current plan and usage limits there. Put the key in `.streamlit/secrets.toml` (create the file in VS Code) using this exact format:

```toml
TAVILY_API_KEY = "paste_your_key_here"
```

Keep that key private. `.streamlit/secrets.toml` and `.env` are ignored by Git. Alternatively, set `TAVILY_API_KEY` in your shell environment before starting Streamlit. `.env.example` is only a placeholder; Streamlit does not automatically load `.env` files.

Start the app:

```sh
streamlit run app.py
```

Open **http://localhost:8501** in your browser. Test with: `The Eiffel Tower is in Paris.` The app must have a valid Tavily key and internet access for a live search. Without a key it displays a friendly configuration message. Demo examples are illustrative only and never shown as sourced verification.

## What the assessment means

The existing rule-based assessment looks for the claim's complete wording or a narrow explicit-negation form in at least two search snippets. Related words alone cannot create a verdict. It does not understand paraphrases or validate source credibility. Always open the source links and check context.

## Optional local NLI mode

The app starts with the existing rule-based method. To install the optional local NLI dependencies in the virtual environment, run:

```sh
python -m pip install -r requirements-nli.txt
```

Enable **Use local NLI model (experimental)** in the app to load `cross-encoder/nli-deberta-v3-xsmall`. The pinned checkpoint uses `safetensors` and is about 283 MB, plus small tokenizer/configuration files. The weights are cached outside the project in Hugging Face's normal model cache. First use needs an internet connection; later use can run locally. If the model cannot load, the app falls back to the existing rule-based method and labels that fallback.

The model card lists the model under Apache-2.0 and says it was trained on SNLI and MultiNLI. The local model classifies snippets as SUPPORTS, CONTRADICTS, or NOT ENOUGH INFORMATION relative to the claim. Its scores are not calibrated probabilities or proof of truth. TruthLens requires at least two distinct result URLs with clear directional predictions and returns Inconclusive for conflicting, weak, neutral, or uncertain results. Open the sources to check context and credibility.

Run all offline tests with:

```sh
python -m pytest -q
```

## Architecture

- `app.py` contains the Streamlit interface, input checks, loading indicator, assessment explanation, and source cards.
- `explainability.py` provides the read-only **Why did TruthLens reach this verdict?** section: escaped evidence highlights, recorded source/component decisions, provenance and limitations. See [the explanation method and offline checks](docs/explainability.md). It does not change verdict rules or model thresholds.
- `temporal_reasoning.py` adds **Temporal Evidence Analysis** within that panel. It distinguishes claim time cues, publication/update/event dates, unresolved relative expressions and possible mismatches. It is diagnostic only. See [the temporal method, challenge set and measured limitations](docs/temporal_reasoning.md); run `.venv/bin/python -m evaluation.evaluate_temporal` for its separate synthetic evaluation.
- `evidence_independence.py` adds **Evidence Independence Analysis**: duplicate wording, shared references, cautious dependency groups and a provenance relationship table. It never proves independence or changes evidence counts. See [the method and measured limitations](docs/evidence_independence.md); run `.venv/bin/python -m evaluation.evaluate_independence` for its separate synthetic challenge.
- `numerical_reasoning.py` adds **Numerical and Quantifier Analysis**: unit-normalized intervals, explicit approximation bands, scope warnings and conservative context matching. It reuses the existing quantifier cue pattern without enabling the guard. See [the method and measured limitations](docs/numerical_reasoning.md); run `.venv/bin/python -m evaluation.evaluate_numerical` for its separate synthetic challenge. Comparisons never override a verdict.
- `uncertainty_analysis.py` adds **Evidence Sufficiency and Uncertainty**, reusing the already-computed diagnostic views and recorded decision trace. Additional warnings are never asserted verdict causes, and missing trace data remains unknown. See [the taxonomy, attribution rules and snapshot evaluation](docs/uncertainty_analysis.md); run `.venv/bin/python -m evaluation.evaluate_uncertainty` for the separate synthetic checks.
- `verifier.py` reads the Tavily key from Streamlit secrets or `TAVILY_API_KEY`, retrieves and cleans actual Tavily results, and provides the conservative rule-based assessment.
- `nli_assessor.py` optionally loads the local DeBERTa NLI model, checks relevant sentence windows, evaluates simple compound claims component by component, and aggregates predictions across distinct source URLs. If model loading fails, the rule-based method is used as a fallback.
- `tests/` contains offline pytest coverage. The tests mock Tavily responses and model predictions; they do not make network requests.

Source cards include optional provenance notes using metadata returned by Tavily and the actual URL/text: publication date when supplied, local retrieval time, host, and URL/text overlap. Each relationship identifies whether its basis is an observed URL/text match or a heuristic near-duplicate inference. A similarity match does not establish common authorship or syndication; publisher identity, shared original reporting, and editorial independence remain unknown unless the response actually supplies that information. These notes are presentation diagnostics only and do not change assessment votes. The **Show per-run performance timing (diagnostic)** option measures local search/assessment stages for the current run; timings are shown in the page and are not written to logs or sent to Tavily. Total time excludes rendering. These diagnostics do not evaluate source credibility or system accuracy.

Source links point to URLs returned by Tavily. The app displays retrieved titles and snippets, with a publication date when Tavily provides one. An NLI score describes the model's classification of a snippet against a claim; it is not a calibrated probability that the claim is true. Inconclusive means the retrieved snippets did not meet the relevance, confidence, or agreement requirements.

## Offline evaluation

For the **baseline versus enhanced diagnostic comparison**, run
`.venv/bin/python -m evaluation.compare_systems --output-dir evaluation/results/comparison_NEW_RUN`.
This separate offline study requires no API key or model inference and produces
a Markdown report plus JSON metrics. It preserves verdicts and distinguishes
synthetic diagnostic findings from unmeasured human usefulness. See the
[research protocol](docs/comparative_evaluation.md). Use a new output directory
for each run; the comparison does not read held-out or pilot records.

The tests exercise controlled assessment behavior. The separate pilot evaluation in [`evaluation/README.md`](evaluation/README.md) documents its developer-authored data, splits, metrics, and limitations. An empty, independent annotation-ready framework with schemas and a two-annotator protocol is documented in [`evaluation/annotation/README.md`](evaluation/annotation/README.md); it contains no new examples or labels. Run the existing pilot evaluation without Tavily using:

```sh
python -m evaluation.run_evaluation --split development
python -m evaluation.run_evaluation --split diagnostics --output evaluation/results/semantic_diagnostics.json
python -m evaluation.benchmark_resources --repeats 5 --output evaluation/results/resources.json
```

With no `--split` argument, the evaluation command defaults to the development set. The held-out split requires an explicit `--split held_out` and should be run only for a final report, never for tuning. Evaluations require the pinned local model already to be cached; they force Hugging Face offline mode and do not download weights. A missing model is reported as **NOT MEASURED**. The pilot sets are very small and developer-authored, so their scores are not general accuracy estimates. The former three-case held-out set was inspected and is preserved as `evaluation/data/held_out_inspected_diagnostic.jsonl`. The current three-case set is visible and not blinded; do not tune against it. The 37 semantic diagnostics are partly synthetic controlled fixtures, not independent or blind evidence. Reports record dataset checksum, model revision, thresholds, class metrics, and publisher-grouping diagnostics. Tests are not a benchmark, and offline evaluation does not measure live search quality. See `evaluation/annotation_guide.md` for a second-annotator workflow; no agreement results are claimed. Search results can change between searches; `manual_claim_diagnostic_before_fixes.md` is a point-in-time record of saved results from an earlier NLI diagnosis.

The latest local pilot outputs and measured limits are summarized in [`evaluation/results/pilot_summary_2026-10-27.md`](evaluation/results/pilot_summary_2026-10-27.md). It records a holdout false abstention caused by the current simple claim-part splitter; the code and labels were not adjusted after observing it.

The separate resource benchmark reports local model-load time, repeated inference latency, and process peak RSS using the Python standard library. It also compares repeated single-pair inference with batches of 1, 2, 4, 8, and 16 on the same 32 fixed offline passage/claim pairs, and compares uncached versus same-verification exact-pair reuse. Batching remains benchmark-only; the app currently enables only a per-verification exact premise/claim prediction cache. The cache never persists between claims or searches, and source-specific context checks and aggregation are still performed for each result. RSS includes the full process and model load; it is not an inference-only memory figure. Energy is not measured because there is no reliable energy telemetry configured, and local inference alone does not imply lower energy or carbon impact.

The evaluation report also compares opt-in quantifier-scope and future-intent abstention guards. These preserve the model's raw label for inspection, then abstain where the heuristic recognizes scope-sensitive claims or reported plans about future events. They are experimental comparison paths only; neither guard changes the Streamlit production assessment. Their visible diagnostic scores are not evidence of general accuracy.

The earlier opt-in compound and reverse-relation comparison is documented in [`evaluation/results/semantic_comparison_2026-10-27.md`](evaluation/results/semantic_comparison_2026-10-27.md). The experimental interpretation path is not enabled in the Streamlit application. A later, narrow production safety guard for ambiguous double-negated motion claims is documented separately below.

The 2026-10-27 safety-focused rerun and double-negation regression are recorded in [`evaluation/results/robustness_comparison_2026-10-27.md`](evaluation/results/robustness_comparison_2026-10-27.md). This diagnostic run does not use either holdout file and does not make Tavily requests.

## Limitations

- NLI classifies textual relationships; it does not verify facts, source quality, source independence, or whether a page is authoritative.
- Search snippets may be incomplete, stale, quoted, or taken out of context. Relevance and historical/qualification checks are conservative heuristics and cannot resolve every nuance.
- Simple compound statements joined by “and” are split for assessment. Complex grammar, conditional claims, dates, quantities, and nested claims may be handled poorly.
- Rule-based mode recognizes only exact wording and a narrow explicit-negation pattern, so it leaves many paraphrased claims Inconclusive.
- The optional model needs its dependencies and cached weights. The app can continue with its rule-based fallback if the model cannot load.

## Troubleshooting

- **`streamlit: command not found`**: activate the environment with `source .venv/bin/activate`, then run `python -m pip install -r requirements.txt` again.
- **Missing key message**: confirm `.streamlit/secrets.toml` exists and uses the TOML format above; stop and restart Streamlit after changing it.
- **Key rejected / rate limit**: check the Tavily dashboard, key spelling, and current usage allowance.
- **Search timeout or connection message**: check your internet connection and retry.
- **No sources**: try a shorter, more specific claim. Empty searches remain inconclusive.
- **Port already in use**: run `streamlit run app.py --server.port 8502`, then open `http://localhost:8502`.
