from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any


class QuestionType(str, Enum):
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    ANALYTICAL = "analytical"
    EDGE_CASE = "edge_case"


class DifficultyLevel(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class ValidationStatus(str, Enum):
    ACCEPTED = "accepted"
    SOFT_FAIL = "soft_fail"
    HARD_FAIL = "hard_fail"


class FailureMode(str, Enum):
    HALLUCINATION_RISK = "hallucination_risk"
    AMBIGUOUS_QUESTION = "ambiguous_question"
    LOW_INFORMATION_VALUE = "low_information_value"
    OVERLY_TRIVIAL = "overly_trivial"
    MULTI_HOP_REQUIRED = "multi_hop_required"


@dataclass(slots=True)
class CitationSpan:
    document_id: str
    chunk_id: str
    chunk_hash: str
    start_char: int
    end_char: int
    text: str


@dataclass(slots=True)
class DocumentRecord:
    document_id: str
    source_path: str
    parser: str
    document_hash: str
    source_type: str
    text: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class ChunkRecord:
    chunk_id: str
    document_id: str
    document_hash: str
    chunk_hash: str
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    tokenizer: str
    normalization_rules: list[str]
    chunking_strategy_id: str
    chunking_version: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class PromptTrace:
    prompt_version: str
    prompt_template_hash: str
    prompt_inputs_hash: str
    model_name: str
    provider: str
    seed: int


@dataclass(slots=True)
class CandidateQuestion:
    question_id: str
    run_id: str
    document_id: str
    chunk_ids: list[str]
    question: str
    question_type: QuestionType
    topic: str
    prompt_trace: PromptTrace
    quality_signals: dict[str, Any]


@dataclass(slots=True)
class CandidateAnswer:
    question_id: str
    answer: str
    acceptable_answers: list[str]
    citations: list[CitationSpan]
    token_usage: dict[str, int]
    estimated_cost_usd: float
    trace: dict[str, Any]


@dataclass(slots=True)
class ValidationResult:
    question_id: str
    status: ValidationStatus
    confidence_score: float
    hard_fail_reasons: list[str]
    soft_fail_reasons: list[str]
    citation_precision: float
    failure_modes: list[FailureMode]
    grounded: bool
    strict_grounded: bool
    recovered_grounding: bool
    duplicate_of: str | None
    review_required: bool


@dataclass(slots=True)
class DifficultyAssessment:
    difficulty: DifficultyLevel
    rationale: dict[str, Any]


@dataclass(slots=True)
class BenchmarkRecord:
    id: str
    question: str
    answer: str
    acceptable_answers: list[str]
    sources: list[str]
    difficulty: DifficultyLevel
    category: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class CoverageLedgerEntry:
    document_id: str
    topic: str
    chunks_total: int
    chunks_covered: int
    questions_generated: int
    multi_chunk_questions: int
    question_types: dict[str, int]


@dataclass(slots=True)
class DatasetProfile:
    total_questions: int
    difficulty_distribution: dict[str, int]
    question_type_distribution: dict[str, int]
    multi_chunk_ratio: float
    avg_citations_per_question: float
    coverage_summary: dict[str, Any]


@dataclass(slots=True)
class StageSummary:
    started_at: str
    completed_at: str
    record_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RunManifest:
    run_id: str
    pipeline_version: str
    config_hash: str
    input_corpus_hashes: list[str]
    stages: dict[str, StageSummary]
    outputs: dict[str, str]


@dataclass(slots=True)
class EvaluationRecord:
    benchmark_id: str
    model_name: str
    response: str
    exact_match: bool
    support_rate: float
    refused: bool
    refusal_type: str | None
    scoring_trace: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationSummary:
    models: dict[str, dict[str, Any]]


def to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {k: to_primitive(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: to_primitive(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_primitive(item) for item in value]
    return value
