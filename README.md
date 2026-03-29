# ABGS

ABGS is an open-source benchmark engineering system for turning private document corpora into traceable QA benchmarks and evaluation artifacts. It is designed around traceability, reproducibility, and domain alignment rather than one-off QA generation.

## Mental Model

ABGS turns documents into benchmarks through four stages:

1. Structure the corpus through ingestion and chunking.
2. Generate questions and answers with traceability.
3. Validate and filter for quality.
4. Evaluate models against the resulting dataset.

## What This MVP Includes

- Deterministic ingestion with content-addressable `document_hash` and `chunk_hash`
- Chunking stability metadata, prompt hashing, and run manifests
- Closed-loop coverage accounting for question generation
- Exact citation spans, validation outcomes, failure mode tagging, and difficulty labeling
- Dataset export, dataset profiling, operator guidance, and a lightweight evaluation harness
- Sample corpora and reference configs for reproducible demos

## Quickstart

1. Create a virtual environment and install the package:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

2. Add a repo-root `.env` file when using Gemini-backed generation:

```text
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

3. Run the sample pipeline:

```bash
abgs-run run --config data/reference_configs/technical_manuals.yaml --input data/samples --output artifacts/runs/sample
```

4. Review the generated artifacts under `artifacts/runs/sample`.

5. Run the Gemini pilot on a policy corpus:

```bash
abgs-run run --config data/reference_configs/policy_docs_gemini_pilot.yaml --input data/AI_Policy --output artifacts/runs/AI_Policy_gemini_pilot
```

6. Compare two runs:

```bash
abgs-compare compare --baseline artifacts/runs/sample_v3 --candidate artifacts/runs/sample_ops --output artifacts/reports/sample_delta
```

## Core Artifacts

- `documents.jsonl`
- `chunks.jsonl`
- `filtered_chunks.jsonl`
- `ingestion_summary.json`
- `candidate_questions.jsonl`
- `coverage_ledger.jsonl`
- `candidate_qa.jsonl`
- `generation_summary.json`
- `validated_qa.jsonl`
- `rejected_qa.jsonl`
- `dataset_profile.json`
- `operator_summary.json`
- `run_manifest.json`
- `evaluation_summary.json`

## Read Next

- `docs/user_guide.md`: complete usage guide, troubleshooting, glossary, and production roadmap
- `docs/methodology.md`: pipeline methodology
- `docs/metrics.md`: MOEs, MOPs, and artifact meanings
- `docs/run_comparison.md`: compare runs and track improvements over time

## Data Handling

ABGS processes data locally by default. No external transmission occurs unless you later configure external model providers. You remain responsible for securing corpora, API keys, and generated outputs.
