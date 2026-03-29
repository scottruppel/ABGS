from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher

from abgs.config import PipelineConfig
from abgs.contracts import (
    BenchmarkRecord,
    CandidateAnswer,
    CandidateQuestion,
    DifficultyAssessment,
    DifficultyLevel,
    FailureMode,
    ValidationResult,
    ValidationStatus,
)
from abgs.matching import text_contains_quote


def validate_records(
    questions: list[CandidateQuestion],
    answers: list[CandidateAnswer],
    config: PipelineConfig,
) -> tuple[list[BenchmarkRecord], list[BenchmarkRecord], list[ValidationResult]]:
    answer_map = {answer.question_id: answer for answer in answers}
    validations: list[ValidationResult] = []
    accepted: list[BenchmarkRecord] = []
    rejected: list[BenchmarkRecord] = []
    seen_questions: dict[str, str] = {}

    for question in questions:
        answer = answer_map[question.question_id]
        duplicate_of = _find_duplicate(question.question, seen_questions, config.quality.duplicate_similarity_threshold)
        support_diagnostics = _support_quote_diagnostics(answer)
        grounded = support_diagnostics["grounded"]
        strict_grounded = support_diagnostics["strict_grounded"]
        recovered_grounding = support_diagnostics["recovered_grounding"]
        citation_precision = _citation_precision(answer, support_diagnostics)
        hard_fail_reasons: list[str] = []
        soft_fail_reasons: list[str] = []

        if not grounded:
            hard_fail_reasons.append("no_retrieval_support")
        if not answer.answer.strip():
            hard_fail_reasons.append("empty_answer")
        if duplicate_of:
            hard_fail_reasons.append("duplicate_question")
        if citation_precision < 0.5:
            soft_fail_reasons.append("partial_grounding")
        if len(answer.answer.split()) < 8:
            soft_fail_reasons.append("low_information_value")

        failure_modes = _failure_modes(question, answer, citation_precision)
        status = _resolve_status(hard_fail_reasons, soft_fail_reasons)
        confidence = _confidence(grounded, duplicate_of is None, citation_precision, soft_fail_reasons)
        assessment = _difficulty(question, answer)

        record = BenchmarkRecord(
            id=question.question_id,
            question=question.question,
            answer=answer.answer,
            acceptable_answers=answer.acceptable_answers,
            sources=[citation.chunk_id for citation in answer.citations],
            difficulty=assessment.difficulty,
            category=question.topic,
            metadata={
                "generation_trace": {
                    "run_id": question.run_id,
                    "chunk_ids": question.chunk_ids,
                    "question_type": question.question_type.value,
                    "prompt_trace": {
                        "prompt_version": question.prompt_trace.prompt_version,
                        "prompt_template_hash": question.prompt_trace.prompt_template_hash,
                        "prompt_inputs_hash": question.prompt_trace.prompt_inputs_hash,
                        "model_name": question.prompt_trace.model_name,
                        "provider": question.prompt_trace.provider,
                        "seed": question.prompt_trace.seed,
                    },
                },
                "confidence_score": confidence,
                "failure_modes": [mode.value for mode in failure_modes],
                "difficulty_rationale": assessment.rationale,
                "citations": [
                    {
                        "document_id": citation.document_id,
                        "chunk_id": citation.chunk_id,
                        "chunk_hash": citation.chunk_hash,
                        "start_char": citation.start_char,
                        "end_char": citation.end_char,
                        "text": citation.text,
                    }
                    for citation in answer.citations
                ],
                "validation": {
                    "status": status.value,
                    "hard_fail_reasons": hard_fail_reasons,
                    "soft_fail_reasons": soft_fail_reasons,
                    "grounded": grounded,
                    "strict_grounded": strict_grounded,
                    "recovered_grounding": recovered_grounding,
                    "citation_precision": citation_precision,
                    "review_required": confidence < config.quality.review_confidence_threshold,
                },
                "quality_signals": question.quality_signals,
            },
        )

        validations.append(
            ValidationResult(
                question_id=question.question_id,
                status=status,
                confidence_score=confidence,
                hard_fail_reasons=hard_fail_reasons,
                soft_fail_reasons=soft_fail_reasons,
                citation_precision=citation_precision,
                failure_modes=failure_modes,
                grounded=grounded,
                strict_grounded=strict_grounded,
                recovered_grounding=recovered_grounding,
                duplicate_of=duplicate_of,
                review_required=confidence < config.quality.review_confidence_threshold,
            )
        )

        if status is ValidationStatus.HARD_FAIL:
            rejected.append(record)
        else:
            accepted.append(record)
            seen_questions[question.question_id] = question.question

    return accepted, rejected, validations


def _find_duplicate(question: str, seen_questions: dict[str, str], threshold: float) -> str | None:
    for question_id, existing in seen_questions.items():
        score = SequenceMatcher(None, question.lower(), existing.lower()).ratio()
        if score >= threshold:
            return question_id
    return None


def _citation_precision(answer: CandidateAnswer, support_diagnostics: dict[str, object]) -> float:
    if not answer.citations:
        return 0.0
    matched = int(support_diagnostics["matched_quotes"])
    return round(matched / max(1, len(answer.citations)), 3)


def _failure_modes(
    question: CandidateQuestion,
    answer: CandidateAnswer,
    citation_precision: float,
) -> list[FailureMode]:
    modes: list[FailureMode] = []
    if citation_precision < 0.5:
        modes.append(FailureMode.HALLUCINATION_RISK)
    if question.question_type.value == "analytical":
        modes.append(FailureMode.MULTI_HOP_REQUIRED)
    if question.question_type.value == "edge_case":
        modes.append(FailureMode.AMBIGUOUS_QUESTION)
    if len(answer.answer.split()) < 8:
        modes.append(FailureMode.LOW_INFORMATION_VALUE)
        modes.append(FailureMode.OVERLY_TRIVIAL)
    return modes


def _support_quote_diagnostics(answer: CandidateAnswer) -> dict[str, object]:
    support_quotes = [
        str(item).strip()
        for item in answer.trace.get("support_quotes", [])
        if isinstance(item, str) and item.strip()
    ]
    if not support_quotes:
        fallback_grounded = all(citation.text and citation.text in answer.answer for citation in answer.citations)
        return {
            "total_quotes": 0,
            "matched_quotes": 0,
            "strict_matches": 0,
            "grounded": fallback_grounded,
            "strict_grounded": fallback_grounded,
            "recovered_grounding": False,
        }

    strict_matches = 0
    matched_quotes = 0
    for quote in support_quotes:
        statuses = [
            text_contains_quote(citation.text, quote)
            for citation in answer.citations
            if citation.text
        ]
        if any(matched for matched, _, _ in statuses):
            matched_quotes += 1
        if any(matched and not recovered for matched, recovered, _ in statuses):
            strict_matches += 1

    grounded = matched_quotes == len(support_quotes)
    strict_grounded = strict_matches == len(support_quotes)
    return {
        "total_quotes": len(support_quotes),
        "matched_quotes": matched_quotes,
        "strict_matches": strict_matches,
        "grounded": grounded,
        "strict_grounded": strict_grounded,
        "recovered_grounding": grounded and not strict_grounded,
    }


def _resolve_status(hard_fail_reasons: list[str], soft_fail_reasons: list[str]) -> ValidationStatus:
    if hard_fail_reasons:
        return ValidationStatus.HARD_FAIL
    if soft_fail_reasons:
        return ValidationStatus.SOFT_FAIL
    return ValidationStatus.ACCEPTED


def _confidence(
    grounded: bool,
    unique_question: bool,
    citation_precision: float,
    soft_fail_reasons: list[str],
) -> float:
    score = 0.5
    score += 0.2 if grounded else -0.3
    score += 0.1 if unique_question else -0.3
    score += 0.2 * citation_precision
    score -= 0.05 * len(soft_fail_reasons)
    return max(0.0, min(1.0, score))


def _difficulty(question: CandidateQuestion, answer: CandidateAnswer) -> DifficultyAssessment:
    features = {
        "multi_chunk_required": question.quality_signals.get("multi_chunk_required", False),
        "num_citations": len(answer.citations),
        "reasoning_steps_estimate": 2 if question.question_type.value in {"analytical", "edge_case"} else 1,
    }
    if features["multi_chunk_required"] and features["reasoning_steps_estimate"] >= 2:
        difficulty = DifficultyLevel.L3
        rule = "multi_chunk_multi_step"
    elif features["multi_chunk_required"] or features["num_citations"] > 1:
        difficulty = DifficultyLevel.L2
        rule = "multi_chunk_or_multi_citation"
    else:
        difficulty = DifficultyLevel.L1
        rule = "single_chunk_retrieval"

    return DifficultyAssessment(
        difficulty=difficulty,
        rationale={"rule": rule, **features},
    )


def validation_summary(validations: list[ValidationResult]) -> dict[str, object]:
    status_counts = Counter(result.status.value for result in validations)
    failure_counts = Counter(mode.value for result in validations for mode in result.failure_modes)
    hard_fail_reason_counts = Counter(reason for result in validations for reason in result.hard_fail_reasons)
    soft_fail_reason_counts = Counter(reason for result in validations for reason in result.soft_fail_reasons)
    strict_grounded_count = sum(1 for result in validations if result.strict_grounded)
    recovered_grounding_count = sum(1 for result in validations if result.recovered_grounding)
    return {
        "status_counts": dict(status_counts),
        "failure_mode_counts": dict(failure_counts),
        "hard_fail_reason_counts": dict(hard_fail_reason_counts),
        "soft_fail_reason_counts": dict(soft_fail_reason_counts),
        "strict_grounded_count": strict_grounded_count,
        "strict_grounding_rate": round(strict_grounded_count / max(1, len(validations)), 3),
        "recovered_grounding_count": recovered_grounding_count,
        "recovered_grounding_rate": round(recovered_grounding_count / max(1, len(validations)), 3),
        "avg_confidence": round(sum(item.confidence_score for item in validations) / max(1, len(validations)), 3),
    }
