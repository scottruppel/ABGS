from __future__ import annotations

import logging
import os
import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader
from pypdf import filters as pypdf_filters

from abgs.config import PipelineConfig
from abgs.contracts import ChunkRecord, DocumentRecord
from abgs.hashing import hash_file, sha256_text

LOGGER = logging.getLogger(__name__)

# pypdf caps Flate-decompressed stream size (default 75 MiB) to mitigate zip-bomb PDFs.
# Large or image-heavy PDFs can exceed that; raise or disable for trusted local corpora.
# Set ABGS_PYPDF_ZLIB_MAX_OUTPUT_BYTES=0 to disable the zlib output cap (trusted inputs only).
def _configure_pypdf_decompression_limit() -> None:
    raw = os.getenv("ABGS_PYPDF_ZLIB_MAX_OUTPUT_BYTES", "268435456").strip()
    if raw.lower() in ("", "default"):
        return
    if raw == "0":
        pypdf_filters.ZLIB_MAX_OUTPUT_LENGTH = 0
        LOGGER.info("pypdf: ZLIB_MAX_OUTPUT_LENGTH disabled (ABGS_PYPDF_ZLIB_MAX_OUTPUT_BYTES=0)")
        return
    try:
        pypdf_filters.ZLIB_MAX_OUTPUT_LENGTH = int(raw)
    except ValueError:
        LOGGER.warning("Invalid ABGS_PYPDF_ZLIB_MAX_OUTPUT_BYTES=%r; using pypdf default", raw)
        return
    LOGGER.debug("pypdf ZLIB_MAX_OUTPUT_LENGTH=%s", pypdf_filters.ZLIB_MAX_OUTPUT_LENGTH)


_configure_pypdf_decompression_limit()

DOT_LEADER_RE = re.compile(r"\.{5,}")
OCR_GARBAGE_RE = re.compile(r"\b([A-Za-z])\1{5,}\b")
GENERIC_FRONT_MATTER = {
    "table of contents",
    "revision history",
    "executive summary",
    "contents",
}


def ingest_corpus(
    input_dir: str | Path,
    config: PipelineConfig,
) -> tuple[list[DocumentRecord], list[ChunkRecord], dict[str, str], dict[str, object]]:
    documents: list[DocumentRecord] = []
    chunks: list[ChunkRecord] = []
    content_index: dict[str, str] = {}
    filtered_chunks: list[dict[str, object]] = []
    filtered_reason_counts: Counter[str] = Counter()
    raw_chunk_count = 0

    for path in sorted(Path(input_dir).glob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".txt", ".pdf"}:
            LOGGER.info("Skipping unsupported file: %s", path.name)
            continue

        document = _load_document(path, config)
        normalized_text = _normalize_text(document["text"])
        document_id = path.stem.lower().replace(" ", "_")
        document_hash = hash_file(path)

        record = DocumentRecord(
            document_id=document_id,
            source_path=str(path),
            parser=document["parser"],
            document_hash=document_hash,
            source_type=path.suffix.lower().lstrip("."),
            text=normalized_text,
            metadata={
                "raw_length": len(document["text"]),
                "normalized_length": len(normalized_text),
            },
        )
        documents.append(record)
        content_index[document_hash] = document_id
        raw_chunks = _chunk_document(record, config)
        raw_chunk_count += len(raw_chunks)
        kept_chunks, rejected_chunks = _filter_chunks(raw_chunks)
        chunks.extend(kept_chunks)
        filtered_chunks.extend(rejected_chunks)
        for item in rejected_chunks:
            filtered_reason_counts.update(item["reasons"])

    return documents, chunks, content_index, {
        "raw_chunk_count": raw_chunk_count,
        "accepted_chunk_count": len(chunks),
        "filtered_chunk_count": len(filtered_chunks),
        "filtered_reason_counts": dict(filtered_reason_counts),
        "filtered_chunks": filtered_chunks,
    }


def _load_document(path: Path, config: PipelineConfig) -> dict[str, str]:
    if path.suffix.lower() == ".txt":
        return {"text": path.read_text(encoding="utf-8"), "parser": "text_loader_v1"}

    if config.ingestion.pdf_fallback == "pypdf_then_pymupdf":
        text, parser = _pdf_text_with_pymupdf_fallback(path, config.ingestion.pymupdf_short_page_chars)
        LOGGER.info("PDF %s parser=%s", path.name, parser)
        return {"text": text, "parser": parser}

    pages = []
    for page in PdfReader(str(path)).pages:
        pages.append(page.extract_text() or "")
    return {"text": "\n".join(pages), "parser": "pypdf"}


def _pdf_text_with_pymupdf_fallback(path: Path, short_chars: int) -> tuple[str, str]:
    try:
        import fitz  # type: ignore[import-untyped]
    except ImportError:
        LOGGER.warning(
            "ingestion.pdf_fallback=pypdf_then_pymupdf but pymupdf is not installed; "
            "install with: pip install -e .[ingest-extra]. Using pypdf only."
        )
        pages = []
        for page in PdfReader(str(path)).pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages), "pypdf"

    reader = PdfReader(str(path))
    doc = fitz.open(path)
    used_fallback = False
    try:
        parts: list[str] = []
        n_pages = len(reader.pages)
        for i in range(n_pages):
            t = reader.pages[i].extract_text() or ""
            if i < doc.page_count and len(t.strip()) < short_chars:
                t2 = (doc[i].get_text() or "").strip()
                if len(t2) > len(t.strip()):
                    t = doc[i].get_text() or ""
                    used_fallback = True
            parts.append(t)
    finally:
        doc.close()
    parser = "pypdf+pymupdf_fallback" if used_fallback else "pypdf"
    return "\n".join(parts), parser


def _normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _chunk_document(document: DocumentRecord, config: PipelineConfig) -> list[ChunkRecord]:
    sentences = _split_sentences(document.text)
    target = config.chunking.target_tokens
    overlap = config.chunking.overlap_tokens
    chunks: list[ChunkRecord] = []

    token_buffer: list[str] = []
    sentence_buffer: list[str] = []
    start_char = 0
    chunk_index = 0

    for sentence in sentences:
        sent_tokens = sentence.split()
        if sentence_buffer and len(token_buffer) + len(sent_tokens) > target:
            chunk_text = " ".join(sentence_buffer).strip()
            chunks.append(
                _make_chunk(
                    document=document,
                    chunk_index=chunk_index,
                    chunk_text=chunk_text,
                    start_char=start_char,
                    config=config,
                )
            )
            chunk_index += 1
            overlap_text = " ".join(token_buffer[-overlap:]) if overlap else ""
            sentence_buffer = [overlap_text] if overlap_text else []
            token_buffer = overlap_text.split() if overlap_text else []
            start_char = max(0, document.text.find(chunk_text) + len(chunk_text) - len(overlap_text))

        sentence_buffer.append(sentence)
        token_buffer.extend(sent_tokens)

    if sentence_buffer:
        chunk_text = " ".join(sentence_buffer).strip()
        chunks.append(
            _make_chunk(
                document=document,
                chunk_index=chunk_index,
                chunk_text=chunk_text,
                start_char=start_char,
                config=config,
            )
        )

    return chunks


def _filter_chunks(chunks: list[ChunkRecord]) -> tuple[list[ChunkRecord], list[dict[str, object]]]:
    accepted: list[ChunkRecord] = []
    rejected: list[dict[str, object]] = []

    for chunk in chunks:
        reasons = _chunk_rejection_reasons(chunk)
        if reasons:
            rejected.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "reasons": reasons,
                    "text_preview": chunk.text[:220],
                }
            )
            continue
        accepted.append(chunk)

    return accepted, rejected


def _chunk_rejection_reasons(chunk: ChunkRecord) -> list[str]:
    text = chunk.text
    lowered = text.lower()
    compact = re.sub(r"\s+", "", text)
    alpha_chars = sum(char.isalpha() for char in compact)
    alpha_ratio = alpha_chars / max(1, len(compact))
    alpha_tokens = re.findall(r"[A-Za-z]{3,}", lowered)
    unique_alpha_tokens = {token for token in alpha_tokens}
    newline_short_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and len(line.strip().split()) <= 4
    ]
    reasons: list[str] = []

    if DOT_LEADER_RE.search(text):
        reasons.append("table_of_contents_pattern")
    if OCR_GARBAGE_RE.search(text):
        reasons.append("ocr_noise")
    if alpha_ratio < 0.55:
        reasons.append("low_alpha_density")
    if len(unique_alpha_tokens) < 4:
        reasons.append("low_vocabulary_chunk")
    if len(newline_short_lines) >= 5 and chunk.chunk_index < 12:
        reasons.append("front_matter_layout")
    if any(marker in lowered for marker in GENERIC_FRONT_MATTER) and chunk.chunk_index < 20:
        reasons.append("front_matter_marker")
    if lowered.count("unclassified") >= 2 and chunk.chunk_index < 20:
        reasons.append("cover_page_marker")
    if re.search(r"\bpage\s+\d+\b", lowered):
        reasons.append("page_marker")
    if re.search(r"\bversion\s+\d+\b", lowered) and chunk.chunk_index < 12:
        reasons.append("version_header")

    deduped = []
    seen = set()
    for reason in reasons:
        if reason not in seen:
            deduped.append(reason)
            seen.add(reason)
    return deduped


def _make_chunk(
    document: DocumentRecord,
    chunk_index: int,
    chunk_text: str,
    start_char: int,
    config: PipelineConfig,
) -> ChunkRecord:
    chunk_id = f"{document.document_id}-chunk-{chunk_index:04d}"
    chunk_hash = sha256_text(chunk_text)
    match_index = document.text.find(chunk_text, start_char)
    actual_start = 0 if match_index < 0 else match_index
    actual_end = actual_start + len(chunk_text)

    return ChunkRecord(
        chunk_id=chunk_id,
        document_id=document.document_id,
        document_hash=document.document_hash,
        chunk_hash=chunk_hash,
        text=chunk_text,
        chunk_index=chunk_index,
        start_char=actual_start,
        end_char=actual_end,
        tokenizer=config.chunking.tokenizer,
        normalization_rules=config.chunking.normalization_rules,
        chunking_strategy_id=config.chunking.strategy_id,
        chunking_version=config.chunking.version,
        metadata={"token_count": len(chunk_text.split())},
    )


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]
