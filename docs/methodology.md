# Methodology

ABGS turns a private corpus into benchmark artifacts through **deterministic, traceable stages**. The MVP prioritizes measurement discipline and reproducibility over model sophistication.

## Pipeline stages

1. **Ingest** — Load supported formats (`TXT`, `PDF`), compute **`document_hash`** from raw bytes, and record ingestion metadata. PDF text uses `pypdf`; very large compressed streams may require raising `ABGS_PYPDF_ZLIB_MAX_OUTPUT_BYTES` (see user guide).

2. **Normalize and chunk** — Normalize text, apply preprocessing filters (front matter, TOC-like blocks, OCR noise, low-value chunks), chunk with recorded strategy metadata, and compute **`chunk_hash`** from normalized chunk text.

3. **Question generation** — Closed-loop generation with coverage accounting, topic-quality gating, upstream duplicate suppression, and deterministic difficulty / question-type labels with rationale.

4. **Answer generation** — Reference answers with **exact citation spans** aligned to chunk text (support-quote contract for provider-backed paths).

5. **Validation** — Grounding is **quote-based**, not naive string equality on full answers. A **two-tier** strategy applies: strict span match first; **fuzzy recovery** second (whitespace collapse, hyphenation and line-break repair, Unicode normalization, window similarity). Items record **`recovered_grounding_rate`** to show how often recovery rescues otherwise-failing items.

6. **Export and profiling** — Emit accepted and rejected records, dataset profile, preprocessing and generation summaries, operator summary, and **`run_manifest.json`**.

7. **Evaluation** — Score configured behaviors (e.g. extractive baseline, cautious refuser, live APIs) on the **same accepted item set**. Scoring uses a **hybrid** view: citation-style support, answer alignment with reference answers, and refusal / inappropriate-refusal signals so abstractive but grounded answers are not treated as failures.

8. **Reporting (optional but standard for demos)** — Full pipeline runs can write **`benchmark_report.json`**, **`benchmark_report.md`**, and **`evaluation_protocol.json`**: dataset overview, model comparison, cuts by difficulty / question type / single vs multi-chunk, a **demo-grade slice** (e.g. L2/L3 + multi-chunk), model behavior profiles, use-case guidance, and a **protocol stamp** (`evaluation_protocol_id`, hashes of `validated_qa` and `run_manifest`, resolved model ids—no secrets) so published numbers can be reproduced.

9. **Optional paths** — **Gemini-backed** pilot configs for provider question/answer generation with explicit support quotes; optional **critic** pass (e.g. Gemini) for refusal/hallucination-style labeling when enabled. **Anthropic** live evaluation can be merged with an existing run via helper scripts; see user guide.

10. **Run comparison** — Compare two completed run directories to track drift in corpus coverage, validation, and evaluation metrics over time.

## Interpretation

Operator-facing output includes comparison of headline metrics to **default benchmark quality bands** (tunable by domain), logging of filtered chunks, and—where reports are generated—**behavioral** interpretation (e.g. grounding vs alignment tradeoffs, refusal stance), not only scalar accuracy.
