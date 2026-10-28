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
- `verifier.py` reads the Tavily key from Streamlit secrets or `TAVILY_API_KEY`, retrieves and cleans actual Tavily results, and provides the conservative rule-based assessment.
- `nli_assessor.py` optionally loads the local DeBERTa NLI model, checks relevant sentence windows, evaluates simple compound claims component by component, and aggregates predictions across distinct source URLs. If model loading fails, the rule-based method is used as a fallback.
- `tests/` contains offline pytest coverage. The tests mock Tavily responses and model predictions; they do not make network requests.

Source links point to URLs returned by Tavily. The app displays retrieved titles and snippets, with a publication date when Tavily provides one. An NLI score describes the model's classification of a snippet against a claim; it is not a calibrated probability that the claim is true. Inconclusive means the retrieved snippets did not meet the relevance, confidence, or agreement requirements.

## Offline evaluation

The tests exercise controlled assessment behavior. The separate pilot evaluation in [`evaluation/README.md`](evaluation/README.md) documents its JSONL schema, development/held-out split, public excerpts versus synthetic fixtures, metrics, and limitations. Run it without Tavily using:

```sh
python -m evaluation.run_evaluation --split development
python -m evaluation.run_evaluation --split diagnostics --output evaluation/results/semantic_diagnostics.json
python -m evaluation.run_evaluation --split held_out --output evaluation/results/held_out_exploratory.json
python -m evaluation.benchmark_resources --repeats 5 --output evaluation/results/resources.json
```

It requires the pinned local model already to be cached; it forces Hugging Face offline mode and does not download weights. A missing model is reported as **NOT MEASURED**. The pilot sets are very small and developer-authored, so their scores are not general accuracy estimates. The former three-case held-out set was inspected and is preserved as `evaluation/data/held_out_inspected_diagnostic.jsonl`. The current three-case set is visible and not blinded; do not tune against it. The sixteen semantic diagnostics are partly synthetic controlled fixtures, not independent or blind evidence. The report compares experimental publisher aggregation and compound/relation interpretation modes while leaving production verdict logic unchanged. Reports record dataset checksum, model revision, thresholds, class metrics, and publisher-grouping diagnostics. Tests are not a benchmark, and offline evaluation does not measure live search quality. See `evaluation/annotation_guide.md` for a second-annotator workflow; no agreement results are claimed. Search results can change between searches; `manual_claim_diagnostic_before_fixes.md` is a point-in-time record of saved results from an earlier NLI diagnosis.

The latest local pilot outputs and measured limits are summarized in [`evaluation/results/pilot_summary_2026-10-27.md`](evaluation/results/pilot_summary_2026-10-27.md). It records a holdout false abstention caused by the current simple claim-part splitter; the code and labels were not adjusted after observing it.

The separate resource benchmark reports local model-load time, repeated inference latency, and process peak RSS using the Python standard library. RSS includes the full process and model load; it is not an inference-only memory figure. Energy is not measured because there is no reliable energy telemetry configured, and local inference alone does not imply lower energy or carbon impact.

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
