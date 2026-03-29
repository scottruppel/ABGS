# Metrics

**Last updated:** 27 Mar 26

## Measures of performance

- Documents processed per run
- Chunks produced per document
- Question candidates generated per 100 chunks
- Coverage correction iterations required before quotas are met
- End-to-end runtime per 100 accepted QA pairs
- Estimated cost per accepted QA pair (especially relevant for provider-backed generation/eval)

## Measures of effectiveness

- **Validation pass rate** — Share of items passing quote-based grounding checks
- **`recovered_grounding_rate`** — Share of accepted items where **fuzzy recovery** (not strict span match) produced a passing grounding check; indicates PDF/text-artifact pressure
- **Citation grounding / citation support rate** — Overlap of model output with source excerpts
- **Answer support rate** and **answer alignment rate** — Hybrid view of support vs reference answers (see evaluation protocol)
- **Corpus coverage** by document and topic
- **Multi-chunk ratio** — Share of items requiring synthesis across chunks
- **Cross-model score separation** on the same fixed item set
- **Refusal rate**, **appropriate refusal**, **inappropriate refusal** — Epistemic stance vs benchmark expectations

## Benchmark quality guidance

Default MVP guidance (operator defaults—not universal thresholds; tune by domain and risk):

- `multi_chunk_ratio`: target `>= 0.40`, warning `< 0.25`
- validation pass rate: target band `0.60–0.85`, warning `< 0.50`
- answer support rate: target `>= 0.80`, warning `< 0.60`

## Demonstrated results (reference benchmark)

The following are **illustrative numbers** from a completed, protocol-stamped report on the **`AI_Policy_gemini_pilot_v4`** fixed set (**59** accepted items), **`abgs-eval-hybrid-2`** (earlier runs may show `abgs-eval-hybrid-1`), with artifacts under `artifacts/reports/ai_policy_v4_with_claude/` (`benchmark_report.md`, `evaluation_protocol.json`). They show what the stack has already been used to demonstrate—not targets for every corpus.

| Quantity | Value |
| --- | --- |
| Accepted benchmark size | 59 |
| Validation pass rate | 0.983 |
| `recovered_grounding_rate` (dataset profile) | 0.883 |
| Multi-chunk ratio | 0.356 |

**Overall model metrics (same 59 items):** `gemini:gemini-2.5-flash` — answer support **0.751**, citation support **0.390**, refusal **0.102**. `anthropic` (`claude-sonnet-4-20250514`) — answer support **0.741**, citation support **0.314**, refusal **0.068**. Baselines for contrast: `extractive_baseline` answer support **0.931**; `cautious_refuser` **0.690** with higher refusal (**0.288**).

**Demo slice (L2/L3 + multi-chunk only):** answer support **0.665** (Gemini), **0.701** (Claude), **0.906** (extractive baseline), **0.536** (cautious refuser)—a harder slice where models separate more clearly than on the full set.

Re-run or third-party reproduction: see user guide *Reproducing published numbers* and the `evaluation_protocol_id` + hashes in `evaluation_protocol.json`.

## Core artifacts

- `run_manifest.json`
- `ingestion_summary.json`
- `filtered_chunks.jsonl`
- `coverage_ledger.jsonl`
- `generation_summary.json`
- `validation_summary.json`
- `dataset_profile.json`
- `operator_summary.json`
- `evaluation_summary.json`
- `evaluation_records.jsonl` (per-item scores, when evaluation is run)
- `benchmark_report.json`, `benchmark_report.md` (when the reporting step is enabled)
- `evaluation_protocol.json` (hashes, protocol id, resolved model ids—no secrets)
