# ABGS User Guide

## What ABGS Is

ABGS is a benchmark engineering system for turning private document corpora into traceable QA benchmarks and evaluation artifacts. It is not just a QA generator or an eval script. The system is designed around:

- traceability
- reproducibility
- operational interpretability
- domain alignment

The framework is open source. Your corpora, generated benchmarks, and evaluation outputs remain local by default.

## Quick Mental Model

ABGS turns documents into benchmarks through four stages:

1. Structure the corpus through ingestion and chunking.
2. Generate questions and answers with traceability.
3. Validate and filter for quality.
4. Evaluate models against the resulting dataset.

If you remember only one thing, remember this: ABGS is meant to help you engineer trustworthy benchmarks, not just create lots of QA pairs.

## What The Current MVP Does

The current implementation supports:

- deterministic ingestion for `TXT` and `PDF`
- content addressability with `document_hash` and `chunk_hash`
- chunking metadata with `chunking_strategy_id`, `chunking_version`, tokenizer, and normalization rules
- preprocessing filters for front matter, OCR noise, and table-of-contents style chunks
- closed-loop question generation with coverage accounting
- topic-quality gating and upstream duplicate suppression
- answer generation with exact citation spans
- validation with `hard_fail` and `soft_fail` outcomes
- lightweight failure mode tagging
- deterministic difficulty labeling with observable rationale
- dataset export, dataset profiling, run manifests, and operator summaries
- a lightweight evaluation harness with answer support and refusal metrics
- an optional Gemini-backed pilot generation path for testing model-backed question and answer generation

## Repository Layout

- `src/abgs/`: core pipeline code
- `data/samples/`: sample corpus files
- `data/reference_configs/`: example configs for different corpus styles
- `artifacts/runs/`: generated outputs from benchmark runs
- `docs/`: methodology, metrics, and usage docs
- `tests/`: automated tests for the MVP pipeline

## Setup

Create a virtual environment and install the project:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

If you want to run the Gemini-backed pilot, add a repo-root `.env` file:

```text
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

## Running The Pipeline

Run the included sample corpus with:

```bash
abgs-run run --config data/reference_configs/technical_manuals.yaml --input data/samples --output artifacts/runs/sample
```

You can also use:

- `data/reference_configs/defense_doctrine.yaml`
- `data/reference_configs/policy_docs.yaml`
- `data/reference_configs/recreation_guides.yaml` (same defaults as policy docs; `category: recreation` for metadata)

To run on your own corpus, place supported files in a directory and point `--input` to that directory.

**PDF ingestion:** Text is extracted with `pypdf`, which limits how large a single compressed stream may expand (zip-bomb protection). Very large or image-heavy PDFs can hit that limit and raise `LimitReachedError`. By default ABGS raises the zlib output cap to **256 MiB** per stream. For trusted local files only, you can disable the cap with `ABGS_PYPDF_ZLIB_MAX_OUTPUT_BYTES=0`, or set a specific byte limit (e.g. `536870912` for 512 MiB).

**Stronger PDF text (optional):** Install extras with `pip install -e .[ingest-extra]` (PyMuPDF). In your YAML, set `ingestion.pdf_fallback: pypdf_then_pymupdf` and optionally `ingestion.pymupdf_short_page_chars` (default 20). When a page’s `pypdf` text is shorter than that threshold, ABGS retries that page with PyMuPDF. This does not replace OCR for fully scanned documents.

Example:

```bash
abgs-run run --config data/reference_configs/policy_docs.yaml --input C:\path\to\your\corpus --output artifacts/runs\my_run
```

Run the Gemini-backed pilot on the policy corpus with:

```bash
abgs-run run --config data/reference_configs/policy_docs_gemini_pilot.yaml --input data/AI_Policy --output artifacts/runs/AI_Policy_gemini_pilot
```

## Live evaluation (Gemini + Anthropic)

After a full pipeline run exists (`validated_qa.jsonl` and baseline `evaluation_records.jsonl`), generate a protocol-stamped report with live API models:

```bash
abgs-run live-eval --run-dir artifacts/runs/fly_fishing --output-dir artifacts/reports/my_live_eval --repo-root .
```

You can omit `--repo-root` (defaults to the current directory) or pass **`--repo-root` with no path** to mean the same as `.`.

- **`--strategy full`** (default): calls Gemini and Anthropic for every accepted item, then merges **`oracle`**, **`extractive_baseline`**, and **`cautious_refuser`** from the run’s existing `evaluation_records.jsonl`.
- **`--strategy anthropic_only`** with **`--v4-paths`**: same layout as the legacy v4 helper — refreshes **Anthropic** only and reuses **Gemini** (and baselines) from disk under `artifacts/runs/AI_Policy_gemini_pilot_v4` → `artifacts/reports/ai_policy_v4_with_claude`.

Other flags: **`--probe`** (API smoke test only), **`--retry-failed`** (retry rows that failed with transport errors), **`--skip-probe`** (not recommended).

Environment: **`GEMINI_API_KEY`**, **`GEMINI_MODEL`**, **`ANTHROPIC_API_KEY`**, **`ANTHROPIC_MODEL`**. Optional: **`ABGS_CRITIC_MODEL`** (e.g. `gemini:gemini-2.5-flash`) for the refusal/alignment critic; **`ABGS_EVAL_PROGRESS_INTERVAL`** (default `25`); **`ABGS_EVAL_API_DELAY_MS`** to throttle requests on large corpora.

Output includes **`live_eval_meta.json`** next to **`evaluation_summary.json`** (estimated live API call counts; dollar cost is not computed until token usage is wired).

Legacy entry points `scripts/run_live_eval_report.py` and `scripts/run_anthropic_v4_report.py` forward to this CLI.

## Comparing report directories (cross-corpus)

Compare **`evaluation_summary.json`** from two completed **report** folders (e.g. policy v4 vs fly fishing):

```bash
abgs-run compare-reports --baseline artifacts/reports/ai_policy_v4_with_claude --candidate artifacts/reports/fly_fishing_gemini_claude --output artifacts/reports/cross_corpus_model_comparison.md
```

## Comparing Two Runs

Compare two completed run directories with:

```bash
abgs-compare compare --baseline artifacts/runs/AI_Policy_refined --candidate artifacts/runs/AI_Policy --output artifacts/reports/ai_policy_delta
```

This produces:

- `run_comparison.json`
- `run_comparison.md`

Use these reports to track changes in benchmark quality over time.

## Expected CLI Output

A healthy run should print stage-level progress similar to:

```text
INFO Starting ABGS run 2bd3c66e7ebb
INFO Input corpus: data/samples
INFO Output directory: artifacts/runs/sample
INFO Configured models: oracle, extractive_baseline, cautious_refuser
INFO Ingestion complete: 2 documents, 4 chunks
INFO Generation complete: 7 questions, 7 answers
INFO Validation complete: 7 accepted, 0 rejected
INFO Dataset profile: 7 questions, 0.429 multi-chunk ratio
INFO Quality guidance: multi-chunk 0.429 (target), validation pass 1.000 (watch)
INFO Cost controls: max_cost_usd=25.0, max_tokens_total=250000
INFO Artifacts written under artifacts/runs/sample
INFO Completed pipeline run 2bd3c66e7ebb
```

Warnings should be treated as operator guidance, not automatic failure. They indicate where review is needed.

## How The Pipeline Works

### 1. Ingestion

ABGS reads supported files, computes a `document_hash` from the raw bytes, normalizes the extracted text, and splits each document into chunks. Each chunk includes:

- `chunk_id`
- `chunk_hash`
- `chunking_strategy_id`
- `chunking_version`
- tokenizer used
- normalization rules used

This is the basis for deduplication, reproducibility, and future continuous-update workflows.

The refined ingestion path also filters low-value chunks before generation. Typical filtered cases include:

- cover pages
- table-of-contents sections
- repeated page headers and footers
- OCR-like garbage
- low-alphabetic-density chunks

### 2. Question Generation

The generator produces benchmark questions across:

- `factual`
- `procedural`
- `analytical`
- `edge_case`

Generation is driven by a coverage ledger. The generator uses current coverage state to prioritize under-covered documents, topics, and question types.

Before a question is emitted, the generation stage now:

- rejects low-quality topics
- suppresses duplicate question signatures upstream
- records generation-side skip counts in `generation_summary.json`

### 3. Answer Generation

Each generated answer includes:

- canonical answer text
- acceptable answer variants
- exact citation spans
- `start_char`
- `end_char`

This supports grounding checks, audit review, and future UI highlighting.

### 4. Validation

Validation separates outcomes into:

- `hard_fail`: reject
- `soft_fail`: flag
- `accepted`

The validator also computes:

- grounding status
- citation precision
- duplicate detection
- confidence score
- failure mode tags such as `hallucination_risk`, `ambiguous_question`, `low_information_value`, `overly_trivial`, and `multi_hop_required`

### 5. Difficulty Labeling

Difficulty is deterministic in the current MVP and assigns:

- `L1`
- `L2`
- `L3`

The rationale records the rule fired and the observable features used, such as multi-chunk status, citation count, and estimated reasoning steps.

### 6. Dataset Export

The system exports accepted records, rejected records, a dataset profile, an operator summary, and a run manifest so each run is reproducible and reviewable.

### 7. Evaluation

The evaluation harness runs a set of model behaviors over the generated benchmark and reports:

- exact match
- answer support rate
- refusal rate
- appropriate refusal rate
- inappropriate refusal rate

## Determinism Guarantees

### Deterministic Today

- ingestion
- text normalization
- chunking
- content hashing
- validation rules
- failure mode tagging
- difficulty labeling
- dataset export

### Potentially Non-Deterministic Later

- LLM-based question generation
- LLM-based answer generation
- semantic scoring
- rubric-based evaluation

### How Seeds Are Used

The current MVP stores a generation seed in prompt trace metadata. In the template-based implementation, generation is deterministic regardless of the seed. Once provider-backed generation is added, seeds will matter for reproducibility where the provider supports them.

### What Reproducibility Means In Practice

In ABGS, reproducibility means:

- the same corpus bytes produce the same `document_hash`
- the same normalized chunk text produces the same `chunk_hash`
- the same chunking logic produces the same chunk boundaries
- the same prompt template and prompt inputs produce the same prompt hashes
- the same deterministic pipeline logic produces the same benchmark artifacts

## Key Output Files

### Ingestion And Corpus Artifacts

- `documents.jsonl`: canonical document records
- `chunks.jsonl`: chunked corpus with hashes and chunking metadata
- `content_index.json`: mapping for content-addressable corpus tracking
- `filtered_chunks.jsonl`: filtered chunks with rejection reasons and text previews
- `ingestion_summary.json`: accepted versus filtered chunk counts and filter-reason totals

### Generation Artifacts

- `candidate_questions.jsonl`: generated question candidates
- `coverage_ledger.jsonl`: coverage accounting by document/topic
- `candidate_qa.jsonl`: generated answers and citations
- `generation_summary.json`: attempted questions, generated questions, duplicate suppression counts, low-quality topic skips, and unique-topic count

### Validation And Dataset Artifacts

- `validated_qa.jsonl`: accepted and soft-failed benchmark records kept in the dataset
- `rejected_qa.jsonl`: hard-failed records removed from the dataset
- `validation_summary.json`: validation counts and aggregate signals
- `dataset_profile.json`: dataset-level statistics for sanity checks and run comparisons
- `operator_summary.json`: benchmark quality guidance, cost controls, and common failure scenarios

### Run And Evaluation Artifacts

- `run_manifest.json`: reproducibility anchor for the full run
- `evaluation_records.jsonl`: per-item evaluation outputs
- `evaluation_summary.json`: aggregate model comparison summary
- `benchmark_report.json` / `benchmark_report.md`: human-readable comparison, model behavior profiles, use-case guidance, and an epistemology framing section (beyond scalar accuracy)
- `evaluation_protocol.json`: frozen metadata for third-party reproduction (see below)

### Comparison Artifacts

- `run_comparison.json`: machine-readable before/after run delta
- `run_comparison.md`: concise comparison summary for humans

## How To Read The Main Artifacts

### `run_manifest.json`

This is the first file to inspect when reviewing a run. It tells you:

- which version of the pipeline ran
- which config produced the run
- which input corpus hashes were used
- stage timing and stage record counts
- where accepted and rejected outputs were written

### `dataset_profile.json`

Use this as a benchmark health summary. It shows:

- total questions
- difficulty distribution
- question type distribution
- multi-chunk ratio
- average citations per question
- coverage summary by document

### `operator_summary.json`

Use this when you want ABGS to help interpret the numbers. It includes:

- benchmark quality guideline status
- cost control configuration
- preprocessing summary
- generation summary
- common pipeline failure scenarios
- operator warnings for low-support or low-coverage conditions

### `evaluation_summary.json`

Use this to compare models on the same benchmark. The most important signals are:

- exact match rate
- answer support rate
- refusal rate
- appropriate versus inappropriate refusal

These metrics help show that the benchmark has discriminative power, not just volume.

### Refusal and alignment critic (optional)

For **Gemini** and **Anthropic** evaluation rows only, ABGS can call a second Gemini pass (the **ABGS Refusal & Alignment Critic**) that classifies each model response against the same source excerpts:

- **PASS** — answer is grounded in the excerpts.
- **SAFE_REFUSAL** — information needed for a direct answer is not in the excerpts (valid abstention).
- **COMPETENCY_REFUSAL** — excerpts contain enough signal but the model refused (synthesis or reasoning failure).
- **HALLUCINATION** — the model answered but the content is not supported by or contradicts the excerpts.
- **UNKNOWN** — critic call failed or could not parse (see `reasoning` in the payload).

When enabled, results are stored under `scoring_trace.critic` on each applicable row in `evaluation_records.jsonl`, including `critic_protocol_id` (`abgs-critic-v1` until the rubric changes).

**Full pipeline:** set in config YAML under `evaluation`, for example:

`critic_model: gemini:gemini-2.5-flash`

**Merged v4 report script:** set the environment variable `ABGS_CRITIC_MODEL` to the same value (e.g. `gemini:gemini-2.5-flash`). Leave unset, or set to `0`, `false`, `off`, or `no` to skip the critic and avoid extra API usage.

### Reproducing published numbers

To match a published benchmark report or comparison, pin the following (all appear in `evaluation_protocol.json` when a report is generated with protocol stamping enabled):

- **`evaluation_protocol_id`**: bumps when hybrid scoring or refusal taxonomy changes (see `EVALUATION_PROTOCOL_ID` in the codebase).
- **`abgs_version`**: pipeline package version.
- **`validated_qa_sha256`**: SHA-256 of the exact `validated_qa.jsonl` used as the benchmark item set.
- **`run_manifest_sha256`**: SHA-256 of `run_manifest.json` from the generation run that produced that dataset (config hash, corpus hashes, run id).
- **`resolved_models`**: API model ids only (e.g. `gemini-2.5-flash`, `claude-sonnet-4-20250514`), no API keys.

Full pipeline runs (`abgs run`) write `evaluation_protocol.json` next to `benchmark_report.json`. For the merged Gemini + Anthropic report on a fixed pilot run, use:

`PYTHONPATH=src python scripts/run_anthropic_v4_report.py`

from the repo root with the same `.env` model ids and the same `artifacts/runs/AI_Policy_gemini_pilot_v4` inputs.

## Benchmark Quality Guidelines

These are recommended default ranges for the MVP. They are starting points, not universal truths, and should be tuned by domain.

### Multi-Chunk Ratio

- Target: `>= 40%`
- Warning: `< 25%`
- Interpretation: low values often mean the benchmark is collapsing into simple lookup questions rather than synthesis.

### Validation Pass Rate

- Target band: `60% to 85%`
- Warning: `< 50%`
- Interpretation: very low values often mean weak source material, poor prompting, or inadequate grounding constraints. Very high values can also be a warning that the validator is too permissive.

### Answer Support Rate

- Target: `>= 80%` for reliable models
- Warning: `< 60%`
- Interpretation: lower values often indicate hallucination risk, weak grounding, or mismatch between benchmark design and model behavior.

### Citation Precision

- Target: as high as possible
- Warning: sustained low values across runs
- Interpretation: low citation precision suggests over-citation spam or weak answer grounding discipline.

## Common Failure Scenarios

### Extremely Low Question Diversity

Likely cause:

- coverage configuration is too narrow
- prompts are too repetitive
- chunks are overly similar

What to do:

- inspect `coverage_ledger.jsonl`
- widen question-type balancing
- refine chunking strategy

### High Duplicate Rejection

Likely cause:

- chunking is too coarse
- prompts are too narrow
- source corpus is highly repetitive
- upstream duplicate suppression is still too permissive for the corpus style

What to do:

- reduce chunk size
- increase chunk specificity
- broaden question prompts

### Low Grounding Rate

Likely cause:

- answer generation is not sufficiently constrained to citations
- source text is noisy
- citations are too broad

What to do:

- tighten answer-generation prompts
- inspect exact citation spans
- improve retrieval validation logic

### High Soft-Fail Rate

Likely cause:

- domain ambiguity
- weak source material
- validation heuristics are too coarse

What to do:

- inspect soft-fail reasons in benchmark metadata
- spot-check source clarity
- refine validation rules

## Cost Expectations And Controls

### MVP Cost Expectations

The current template-based MVP is effectively negligible in direct model cost because it does not call external providers for generation or evaluation.

### Production Cost Expectations

Once provider-backed generation and evaluation are added, cost will depend on:

- corpus size
- number of chunks
- question target volume
- number of retries
- provider choice
- prompt length
- model response length

As a planning heuristic, production cost should be estimated per 100 accepted QA pairs rather than per raw run.

### Config Guard Stubs

Reference configs now include:

- `max_cost_usd`
- `max_tokens_total`

These are recorded today and intended for future enforcement once live providers are integrated. They should be treated as planning ceilings in the MVP.

## Preprocessing And Duplicate-Reduction Notes

The current refined pipeline adds an important intermediate layer between ingestion and generation:

- low-value chunks can be filtered before generation
- weak topics can be rejected before a question is emitted
- duplicate question signatures can be suppressed before validation

This matters because it reduces wasted generation effort and improves the quality of the retained benchmark. For policy-style corpora in particular, this preprocessing layer is often the difference between a diagnostic run and a usable benchmark run.

## Minimal End-To-End Example Trace

Below is an abbreviated example based on the included sample corpus.

### Source Document Snippet

```text
Preventive maintenance is performed every thirty days. The technician records pressure readings, replaces the inline filter, and confirms that the emergency bypass valve opens within two seconds.
```

### Chunk Record

```json
{
  "chunk_id": "maintenance_manual-chunk-0001",
  "document_id": "maintenance_manual",
  "chunking_strategy_id": "sentence_window",
  "chunking_version": "1.0",
  "chunk_hash": "..."
}
```

### Generated Question

```json
{
  "question_id": "run-q-0001",
  "question_type": "procedural",
  "question": "What procedure is described for maintenance?",
  "chunk_ids": ["maintenance_manual-chunk-0001"]
}
```

### Generated Answer And Citation

```json
{
  "answer": "Preventive maintenance is performed every thirty days.",
  "citations": [
    {
      "chunk_id": "maintenance_manual-chunk-0001",
      "start_char": 0,
      "end_char": 48,
      "text": "Preventive maintenance is performed every thirty days."
    }
  ]
}
```

### Validation Result

```json
{
  "status": "accepted",
  "grounded": true,
  "citation_precision": 1.0,
  "failure_modes": []
}
```

### Final Dataset Row

```json
{
  "id": "run-q-0001",
  "difficulty": "L1",
  "category": "maintenance",
  "metadata": {
    "confidence_score": 1.0
  }
}
```

## Recommended Workflow For Users

### 1. Start With A Small Corpus

Begin with a representative but manageable set of files. Validate output quality, coverage, and traceability before scaling up.

### 2. Choose The Closest Reference Config

Pick the reference config that best matches your corpus:

- doctrine-like material
- policy and governance material
- technical manuals and procedures

Then adjust chunking and generation settings incrementally.

### 3. Review Dataset Shape First

After each run, review:

- `dataset_profile.json`
- `operator_summary.json`
- `coverage_ledger.jsonl`
- `validation_summary.json`

This is the fastest way to catch imbalance, triviality, or low coverage.

### 4. Audit A Few Records End To End

For several accepted items, trace:

- source document
- source chunk
- generated question
- generated answer
- citations
- validation result
- dataset row

If this trace is not trustworthy, the benchmark is not ready.

### 5. Compare Multiple Models

Run the same benchmark against multiple models or model policies. This is how you establish that the benchmark separates behavior in a useful way.

## When ABGS May Not Be Appropriate

ABGS may not be the right fit when:

- the corpus is extremely small, such as fewer than about five meaningful documents
- the text is highly unstructured or very noisy
- the task requires subjective, creative, or preference-based evaluation
- the domain does not have a stable notion of grounded correctness

In those cases, a manually curated benchmark or a different evaluation workflow may be more appropriate.

## Data Handling

- all data is processed locally by default
- no external transmission occurs unless you explicitly configure external providers
- you are responsible for securing API keys, corpora, and generated outputs
- benchmark artifacts may still contain sensitive source-derived content and should be handled accordingly

## Versioning Strategy

- `schema_version`: use for breaking or structural artifact changes
- `pipeline_version`: use for logic changes in ingestion, generation, validation, or evaluation
- `config_hash`: use as the experiment identity for a concrete run configuration

When comparing runs, always look at all three.

## Glossary

- `document_hash`: hash of the raw input document bytes
- `chunk_hash`: hash of normalized chunk text
- `coverage_ledger`: artifact tracking how well documents, topics, and question types are being covered
- `citation_precision`: percentage of cited spans that are actually necessary to support the answer
- `answer_support_rate`: percentage of model outputs that can be grounded in the same corpus
- `run_manifest`: run-level artifact capturing pipeline version, config hash, stage metadata, and output paths
- `operator_summary`: run-level artifact that interprets benchmark quality and highlights warnings
- `soft_fail`: record kept for review or caution
- `hard_fail`: record rejected from the final benchmark

## Current MVP Limitations

This repository is a strong scaffold, but it is still an MVP. Current limitations include:

- only `TXT` and `PDF` loaders are implemented
- question and answer generation are deterministic templates rather than live LLM-backed generation
- retrieval validation is lightweight and based on direct citation support
- model evaluation uses stubbed behaviors, not production API providers
- budget controls are recorded but not yet enforced
- continuous corpus refresh is not yet automated
- benchmark quality heuristics are useful but intentionally simple

## Production-Grade Roadmap

The sections below outline the next steps to move from a demonstration-ready MVP to a production-grade benchmark generation system.

## Phase 1: Harden The Current Contracts

Before adding more intelligence, keep the existing traceability model stable.

### Priorities

- freeze schema versions for benchmark records, run manifests, coverage ledgers, and dataset profiles
- add explicit artifact version validation at load and export time
- strengthen test coverage around chunking stability and prompt hash stability
- add richer logging around stage retries, stage failures, and partial outputs

### Why It Matters

If the contracts are unstable, every downstream metric and experiment becomes harder to trust.

## Phase 2: Expand Ingestion

Broaden the system’s usefulness by supporting more real-world corpus types.

### Next Steps

- add `DOCX` and `HTML` loaders
- add parser-specific metadata to document records
- add support for recursive directory traversal
- support richer metadata extraction such as title, section, page, and source collection
- add document deduplication using `document_hash`

### Production Goal

Users should be able to point ABGS at a heterogeneous corpus and get consistent canonical records without manual cleanup.

## Phase 3: Replace Template Generation With Provider Abstractions

The current generation stage proves the control flow, but production value depends on robust LLM-backed generation.

### Next Steps

- add a provider interface for question generation and answer generation
- support `.env`-based credentials and provider-specific configuration
- persist raw prompt text and sanitized prompt inputs for reproducibility
- add prompt template libraries by corpus type
- implement retries, timeouts, fallback providers, and actual cost enforcement

### Production Goal

Run the same pipeline against different LLM providers while preserving run-level comparability and prompt traceability.

## Phase 4: Improve Validation And Grounding

Validation is where benchmark trust is won or lost.

### Next Steps

- add retrieval-backed support checking against indexed chunks instead of only direct string containment
- add semantic duplicate detection
- add answer consistency checks across rephrasings
- add stricter span validation for exact citation necessity
- introduce a human-review queue for low-confidence or soft-fail records

### Production Goal

ABGS should be able to reject weak or poorly grounded items before they ever reach the final benchmark.

## Phase 5: Upgrade Benchmark Quality Heuristics

A benchmark can be technically valid and still strategically weak.

### Next Steps

- score questions for information value, difficulty, and operational relevance
- enforce dataset-level quality floors such as minimum multi-chunk ratio and minimum analytical coverage
- add cross-document synthesis targets
- broaden failure mode tagging to support richer benchmark diagnostics

### Production Goal

The benchmark should reveal meaningful model differences, not just confirm that a model can retrieve obvious facts.

## Phase 6: Build A Real Evaluation Harness

The current evaluation harness proves the reporting model. Production needs real model interfaces and deeper scoring.

### Next Steps

- integrate provider-backed model runners
- add semantic scoring and rubric-based evaluation
- preserve full model responses and metadata
- distinguish exact correctness from grounded correctness
- add batch execution, concurrency limits, and retry handling

### Production Goal

Users should be able to compare multiple real models on the same benchmark with reliable cost, latency, support, and refusal metrics.

## Phase 7: Add Continuous Benchmark Refresh

This is where ABGS becomes operationally durable.

### Next Steps

- detect changed documents using `document_hash`
- detect changed chunks using `chunk_hash`
- regenerate only the affected benchmark records
- track dataset lineage across versions
- compare benchmark drift across corpus updates

### Production Goal

Organizations should be able to refresh a benchmark as knowledge changes without rebuilding everything from scratch.

## Phase 8: Add Human Review And Governance

Production benchmarking in sensitive environments needs explicit governance.

### Next Steps

- create a reviewer workflow for soft-fail and low-confidence records
- add approval states to benchmark items
- track who reviewed or overrode a validation decision
- support exportable audit packages for review boards or conference reporting

### Production Goal

A benchmark should be explainable not only to engineers, but also to governance, safety, and mission stakeholders.

## Phase 9: Scale The System

Once quality and trust are in place, performance becomes the next concern.

### Next Steps

- parallelize ingestion, generation, and evaluation safely
- introduce persistent artifact caching
- add a vector index for retrieval validation and future search workflows
- support larger corpora and run partitioning
- capture resource utilization in telemetry

### Production Goal

ABGS should handle large corpora and repeated benchmark refreshes without losing reproducibility or observability.

## Phase 10: Improve User Experience

Production adoption depends on usability, not only pipeline quality.

### Next Steps

- add richer CLI options and config validation
- provide a benchmark inspection notebook or lightweight UI
- add a run comparison command for `dataset_profile.json` and `evaluation_summary.json`
- add downloadable demo reports for conference and stakeholder briefings

### Production Goal

Users should be able to run, inspect, compare, and explain benchmarks without needing to read raw JSON artifacts by hand.

## Suggested Implementation Order From Here

1. Add `DOCX` and `HTML` ingestion plus recursive corpus loading.
2. Introduce provider abstractions for live LLM generation and real model evaluation.
3. Strengthen retrieval validation and duplicate detection.
4. Add human review workflows and approval states.
5. Add continuous refresh using content-addressable change detection.
6. Add vector indexing, scaling improvements, and richer reporting UX.

## Suggested Success Criteria For The Next Milestone

The next milestone should prove that ABGS can operate on a real private corpus with live model calls while preserving traceability.

Recommended criteria:

- run successfully on a mixed-format corpus
- generate a benchmark with balanced question-type coverage
- maintain target multi-chunk ratio
- reject weak records with clear failure reasons
- compare at least two real models on the same benchmark
- produce an audit trail that is conference-ready for review

## Final Guidance

Treat the current system as a traceability-first foundation. Do not rush to add model complexity until ingestion, artifact contracts, validation semantics, evaluation reporting, and operator guidance are stable. For an open-source benchmark engineering tool, trust, reproducibility, and observability are the differentiators that will matter most.
