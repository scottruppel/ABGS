from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(slots=True)
class ChunkingConfig:
    strategy_id: str = "sentence_window"
    version: str = "1.0"
    target_tokens: int = 120
    overlap_tokens: int = 20
    tokenizer: str = "whitespace_v1"
    normalization_rules: list[str] = field(
        default_factory=lambda: [
            "trim_whitespace",
            "collapse_internal_whitespace",
            "normalize_newlines",
        ]
    )


@dataclass(slots=True)
class GenerationConfig:
    prompt_version: str = "v1"
    provider: str = "deterministic"
    model_name: str = "template_generator"
    seed: int = 7
    target_questions_per_chunk: int = 2
    minimum_multi_chunk_ratio: float = 0.4
    max_questions: int | None = None
    temperature: float = 0.2


@dataclass(slots=True)
class QualityConfig:
    duplicate_similarity_threshold: float = 0.92
    review_confidence_threshold: float = 0.75
    multi_chunk_target: float = 0.4
    multi_chunk_warning: float = 0.25
    validation_pass_target_min: float = 0.6
    validation_pass_target_max: float = 0.85
    validation_pass_warning: float = 0.5
    answer_support_target: float = 0.8
    answer_support_warning: float = 0.6


@dataclass(slots=True)
class EvaluationConfig:
    models: list[str] = field(
        default_factory=lambda: [
            "oracle",
            "extractive_baseline",
            "cautious_refuser",
        ]
    )
    max_cost_usd: float | None = None
    max_tokens_total: int | None = None
    # e.g. "gemini:gemini-2.5-flash" — annotates Gemini/Anthropic rows with refusal/alignment critic (extra API calls).
    critic_model: str | None = None


@dataclass(slots=True)
class IngestionConfig:
    """PDF text extraction; optional PyMuPDF fallback requires `pip install -e .[ingest-extra]`."""

    pdf_fallback: str = "pypdf_only"
    pymupdf_short_page_chars: int = 20


@dataclass(slots=True)
class PipelineConfig:
    name: str
    category: str
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)


def load_config(path: str | Path) -> PipelineConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    ev_raw = dict(raw.get("evaluation", {}))
    ing_raw = raw.get("ingestion") or {}
    return PipelineConfig(
        name=raw["name"],
        category=raw["category"],
        chunking=ChunkingConfig(**raw.get("chunking", {})),
        generation=GenerationConfig(**raw.get("generation", {})),
        quality=QualityConfig(**raw.get("quality", {})),
        evaluation=EvaluationConfig(**ev_raw),
        ingestion=IngestionConfig(
            pdf_fallback=str(ing_raw.get("pdf_fallback", "pypdf_only")),
            pymupdf_short_page_chars=int(ing_raw.get("pymupdf_short_page_chars", 20)),
        ),
    )
