# Agentic Benchmark Generation System Diary

## 29 Mar 26

### Objective
Ship the planned **architecture round**: unified live-eval CLI, long-run observability and cost metadata, optional **PyMuPDF** PDF fallback, **`evaluation_failure`** refusal taxonomy separate from model abstention, **`recreation_guides.yaml`**, corpus-difficulty context in benchmark reports, and **cross-corpus report comparison**. **28 Mar** was a no-code day.

### Work Done
- **`abgs-run live-eval`** — Replaces ad-hoc scripts: `--strategy full` (Gemini + Anthropic live + baseline merge) or **`anthropic_only`** with **`--v4-paths`** for the AI Policy v4 workflow. **`--probe`**, **`--retry-failed`**, **`--skip-probe`**. Writes **`live_eval_meta.json`** (estimated call counts + cost placeholder). Thin wrappers: **`scripts/run_live_eval_report.py`**, **`scripts/run_anthropic_v4_report.py`** delegate to the CLI.
- **`src/abgs/evaluate/live_report.py`** — Shared loading, merge strategies, probes, retry using **`LIVE_EVAL_FAILURE_SENTINEL`**.
- **Evaluation protocol `abgs-eval-hybrid-2`** — Rows with API/transport failures use **`refusal_type: evaluation_failure`** and **`evaluation_failure_rate`** in summaries; no longer counted as appropriate/inappropriate refusal.
- **Live-eval UX** — **`ABGS_EVAL_PROGRESS_INTERVAL`** (default 25) logs progress; **`ABGS_EVAL_API_DELAY_MS`** throttles live API calls.
- **Ingestion** — Optional **`ingestion.pdf_fallback: pypdf_then_pymupdf`** (+ **`pymupdf_short_page_chars`**) with **`pip install -e .[ingest-extra]`** (`pymupdf`). Per-document parser metadata **`pypdf`** or **`pypdf+pymupdf_fallback`**.
- **Reference config** — **`data/reference_configs/recreation_guides.yaml`** (`category: recreation`).
- **Reporting** — **`corpus_health`** / **Benchmark difficulty context** in **`benchmark_report`**; model table adds **Evaluation Failure (API/transport)** column.
- **Cross-corpus** — **`abgs-run compare-reports`** — reads two report dirs’ **`evaluation_summary.json`**, writes side-by-side markdown (optional **`--output`**).
- **Tests** — `test_evaluation_failure_metrics.py`; pipeline test asserts **`corpus_health`** in report JSON.

### Current Interpretation
- Operators have **one CLI** for live eval and **honest metrics** when APIs fail mid-run; **cross-corpus** comparison is a single command away.

### Next steps
- Optional **resume/checkpoint** for interrupted live evals; **token-based cost** when providers expose usage.
- **Tesseract or cloud OCR** only if scanned PDFs dominate (PyMuPDF handles many text-layer edge cases first).

---

## 28 Mar 26

### Objective
Exercise ABGS on a **second corpus** (recreation / outdoor fishing guides), harden PDF ingestion at scale, and produce a **reproducible Gemini vs Claude** report comparable in shape to the policy v4 artifacts.

### Work Done
- Ran the full pipeline on **`data/fly_fishing`** with `data/reference_configs/policy_docs.yaml` (chunking and quality knobs are domain-agnostic; `category: policy` is metadata-only for this run).
- Fixed **large-PDF ingestion** when `pypdf` hit `LimitReachedError` (Flate decompress cap): import-time configuration of `ZLIB_MAX_OUTPUT_LENGTH` via **`ABGS_PYPDF_ZLIB_MAX_OUTPUT_BYTES`** (default raised to 256 MiB; `0` = disable for trusted local corpora only). Documented in `docs/user_guide.md`.
- Added **`scripts/run_live_eval_report.py`**: probes Gemini + Anthropic, runs live eval on **`gemini:${GEMINI_MODEL}`** and **`anthropic`**, merges with existing **`oracle` / extractive / cautious** rows from the run, writes **`evaluation_protocol.json`** + **`benchmark_report`**, supports **`--retry-failed`** and optional **`ABGS_CRITIC_MODEL`**.
- Completed **~931 × 2** live API calls for fly fishing; artifacts under **`artifacts/reports/fly_fishing_gemini_claude/`** (companion to v4’s `scripts/run_anthropic_v4_report.py`, which remains specialized to merging into the v4 run).
- Refreshed **`docs/metrics.md`** (date stamp, demonstrated v4 numbers, artifact list) and **`docs/methodology.md`** (quote validation, two-tier grounding, hybrid eval, protocol-stamped reports).

### Lessons Learned
- A **second domain** surfaces different failure modes: **validation pass rate ~0.54** and **`recovered_grounding_rate` 0** on this run vs the tight policy pilot—**benchmark difficulty and corpus noise** dominate headline metrics; model scores are not portable across corpora without context.
- **Frontier models** on fly fishing showed **very high refusal and inappropriate-refusal rates**; **Claude** modestly outperformed **Gemini** on citation/alignment and lower inappropriate refusal on this slice—**not** the same profile as policy v4, which is useful for **generalization** thinking.
- **Extractive baseline** remained strong, so gaps are largely **abstention and alignment**, not missing text in chunks.
- **Config file name** (`policy_docs.yaml`) does not change parsing logic; a dedicated **`recreation_guides.yaml`** (or similar) is still worthwhile for **`category` labeling** and future chunking tuning, not because the wrong parser was used.

### Results Demonstrated (fly fishing, 931 accepted items)
- **`gemini:gemini-2.5-flash`:** answer support **~0.241**, citation support **~0.110**, refusal **~0.643**.
- **`anthropic` (`claude-sonnet-4-20250514`):** answer support **~0.284**, citation support **~0.155**, refusal **~0.609**.
- **Demo slice (L2/L3 + multi_chunk):** live models **~0.19** answer support vs **extractive_baseline ~0.73**—sharp separation useful for demos of **when extractive wins** under heavy abstention.

### Current Interpretation
- ABGS has now been **end-to-end** on **policy (v4)** and **recreation (fly fishing)** with **protocol-stamped** live-eval reports for both directions of comparison.
- The stack is ready for **cross-corpus** discussion: same rubric, different domain stress tests.

### Next steps (architecture and product)
1. **Unify live-eval entry points** — One documented flow (e.g. `abgs-run evaluate` or a single script with `--run-dir` / `--merge-baseline`) so `run_live_eval_report.py` and `run_anthropic_v4_report.py` are not two mental models forever.
2. **Long-run ergonomics** — Progress logging, optional **resume** or **checkpoint** for 500+ item live evals; **rate-limit** handling and backoff; **cost** rolled into `operator_summary` or report footer.
3. **Benchmark quality per domain** — Tune **chunking / validation** when validation pass rate and refusal semantics diverge (recreation vs policy); optional **`recreation_guides.yaml`**; consider **procedural/L3** item review when baselines stay high but live models tank.
4. **Refusal and failure taxonomy** — Separate **API/transport failures** from **model abstention** in scoring; extend **critic** usage and calibration (`ABGS_CRITIC_MODEL`) on high-refusal corpora.
5. **Ingestion roadmap** — **OCR** or alternate extractors for scanned guides; continued **PDF** edge-case hardening without weakening zip-bomb limits by default.
6. **Cross-corpus generalization study** — Compare **rank-order** of models (and refusal vs citation tradeoffs) **policy v4 vs fly_fishing** to see what is stable vs domain-specific.
7. **Reporting** — Keep leading with **hard slices** (`L2/L3 + multi_chunk`); add short **corpus profile** blurb in reports (validation pass, recovered rate) so readers do not compare 59-item policy numbers to 931-item recreation numbers naively.

---

## 27 Mar 26

### Objective
Move ABGS from document parsing into a defensible, low-cost benchmark generation and evaluation workflow that can support a conference-grade demo.

### Work Done
- Built the initial ABGS MVP pipeline with ingestion, chunking, question generation, answer generation, validation, dataset profiling, evaluation, run manifests, and operator summaries.
- Added content addressability and reproducibility anchors including `document_hash`, `chunk_hash`, prompt hashes, chunking metadata, and run manifests.
- Added preprocessing filters for policy-style corpora to suppress front matter, table-of-contents blocks, OCR noise, low-value chunks, and repeated boilerplate.
- Improved topic extraction and upstream duplicate suppression so question generation stopped clustering around weak topics and repeated prompts.
- Added run comparison reporting so benchmark runs can be compared over time.
- Added Gemini-backed question and answer generation using explicit `support_quotes`.
- Changed validation from literal answer-string grounding to quote-based grounding, which unlocked abstractive but still grounded model outputs.
- Implemented a two-tier grounding strategy:
  strict span match first,
  fuzzy recovery second using whitespace collapse, hyphenation repair, line-break cleanup, Unicode normalization, and window-based similarity recovery.
- Added `recovered_grounding_rate` to quantify how often fuzzy recovery rescues items that strict matching would reject.
- Added a live evaluation path for `gemini:gemini-2.5-flash` alongside constrained baselines.
- Added Anthropic live evaluation support so the same benchmark can be scored by Claude on the identical accepted item set.
- Completed end-to-end fixed-benchmark runs comparing **Gemini** and **Claude** on `AI_Policy_gemini_pilot_v4` (59 accepted items), with artifacts under `artifacts/reports/ai_policy_v4_with_claude` and driver script `scripts/run_anthropic_v4_report.py`.
- Improved evaluation support scoring with a hybrid metric that combines citation support and answer-alignment scoring so grounded paraphrases are no longer badly underrated.
- Added a demo-grade report with:
  dataset overview,
  model comparison,
  difficulty and question-type cuts,
  single-chunk vs multi-chunk cuts,
  `L2/L3 + multi_chunk` demo slice,
  and representative failure examples with scoring traces.

### Lessons Learned
- Frontier generation was not the initial bottleneck. The first real failure was validation logic that assumed extractive answers.
- Support-quote contracts matter. Once the provider returned explicit evidence spans, validation quality changed dramatically.
- PDF extraction artifacts are a major source of false failures. Hyphenation, line wraps, and Unicode normalization need to be handled as first-class concerns.
- A single support metric is too blunt. Evaluation needed both source-support and answer-alignment signals to score abstractive responses fairly.
- Benchmark validity and benchmark discriminative power are different problems. A benchmark can be well grounded and still fail to separate models if the slice is too easy.
- Multi-chunk and higher-difficulty slices are the best place to show benchmark value.

### Results Demonstrated
- Gemini pilot generation remained cheap, with the two earlier runs costing about `$0.27`.
- `AI_Policy_gemini_pilot_v2` showed the validation-contract fix worked:
  dataset size rose to `53`,
  validation pass rate rose to `0.883`,
  and hard fails dropped sharply relative to the first Gemini pilot.
- `AI_Policy_gemini_pilot_v3` showed the two-tier grounding recovery worked:
  dataset size rose to `59`,
  validation pass rate reached `0.983`,
  hard fails dropped to `1`,
  and `recovered_grounding_rate` reached `0.850`.
- `AI_Policy_gemini_pilot_v4` showed evaluation support scoring moved from artificially low to realistic:
  `gemini:gemini-2.5-flash` answer support rate improved from `0.347` to `0.751`.
- The first demo-grade hard-slice comparison now exists for `L2/L3 + multi_chunk` items:
  `gemini:gemini-2.5-flash` support `0.665`,
  `extractive_baseline` support `0.906`,
  `cautious_refuser` support `0.536`,
  with materially different refusal behavior across models.
- **Gemini vs Claude (same 59 items, hybrid answer support):** latest refresh shows `gemini:gemini-2.5-flash` at **0.751** answer support and **0.390** citation support vs **`anthropic`** (`claude-sonnet-4-20250514`) at **0.725** / **0.297**; refusal rates **0.102** vs **0.085**. Full cuts are in `artifacts/reports/ai_policy_v4_with_claude/evaluation_summary.json` and `benchmark_report.md`.

### Current Interpretation
- ABGS is no longer just parsing documents.
- It can now generate a grounded benchmark from a real policy corpus, validate it with recovery-aware grounding, and evaluate contrasted answering systems with a report that surfaces model differences.
- The benchmark is beginning to show its teeth on the harder `L2/L3 + multi_chunk` slice.
- There is now a **reproducible head-to-head** on the fixed v4 set: rerun Anthropic with `scripts/run_anthropic_v4_report.py` (optional `--retry-failed` if any row still shows `REFUSE: live evaluation failed`).

### Anthropic live eval (fixed benchmark v4, engineering notes)
- **`claude-sonnet-latest` is not a valid Messages API model id** (HTTP 404). Use a dated snapshot such as **`claude-sonnet-4-20250514`** in `.env` and as the code default.
- **`load_local_env(..., override=True)`** so repo `.env` wins over stale `ANTHROPIC_*` values in the process environment (wrong key can mimic a billing error).
- **`artifacts/reports/ai_policy_v4_with_claude`** is produced by `scripts/run_anthropic_v4_report.py`: merges `AI_Policy_gemini_pilot_v4` Gemini + baselines with a live **`anthropic`** pass on the same 59 accepted items.
- The Anthropic provider tolerates **`refused: true` with an empty `answer`** (maps to a short refusal string) and uses **`JSONDecoder.raw_decode`** when the model emits JSON plus trailing text.

### Next steps
1. **Stress the hard slice in reporting** — Lead demos with `L2/L3 + multi_chunk` (and `demo_grade_slice` in `benchmark_report.md`) where models separate most; keep overall 59-item metrics as context.
2. **Protocol lock (implemented)** — `evaluation_protocol.json` + `evaluation_protocol_id` in each stamped report: `validated_qa` SHA-256, `run_manifest` SHA-256, `abgs_version`, and resolved model ids (no secrets). See `docs/user_guide.md` → *Reproducing published numbers*.
3. **Decision-ready report sections (implemented)** — `benchmark_report.md` now includes **Model Behavior Profile**, **Use Case Guidance**, **Evaluation Protocol (reproducibility)**, and **Beyond accuracy** (epistemology: refusals, grounding vs alignment).
4. **Optional model refresh** — When Anthropic or Google ship new API model ids, add a dated row (e.g. `claude-sonnet-4-*`, `gemini-*`) and re-run once; keep prior report directory or manifest note for history.
5. **Second corpus** — **Fly fishing** (`data/fly_fishing`, report `artifacts/reports/fly_fishing_gemini_claude`) is the first non-policy pass; next is **additional corpora** and **cross-corpus** comparison of model rank-order vs absolute scores (see 28 Mar 26).
6. **Evaluation quality** — Tune refusal labeling if placeholder refusals (`REFUSE: insufficient source excerpts`) should be scored differently from model-native refusals; consider logging raw Anthropic JSON for audit.
7. **Refusal & alignment critic (implemented)** — Optional Gemini second pass classifies frontier rows into PASS / SAFE_REFUSAL / COMPETENCY_REFUSAL / HALLUCINATION (`scoring_trace.critic`). Enable via `evaluation.critic_model` in YAML or `ABGS_CRITIC_MODEL` for `run_anthropic_v4_report.py`; see `docs/user_guide.md`.
8. **Cost and ops** — Track approximate API cost per full Anthropic pass in `operator_summary` or a small run note when you add new live models.
