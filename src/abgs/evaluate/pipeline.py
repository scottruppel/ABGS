from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
import logging
import os
import re
import time

from abgs.contracts import BenchmarkRecord, EvaluationRecord, EvaluationSummary
from abgs.evaluate.anthropic_provider import AnthropicEvaluationError, answer_question as answer_anthropic_question
from abgs.evaluate.critic import apply_critic_to_evaluations
from abgs.evaluate.gemini_provider import GeminiEvaluationError, answer_question
from abgs.matching import normalized_text, text_contains_quote

LOGGER = logging.getLogger(__name__)

# Bump when hybrid support scoring, refusal taxonomy, or evaluate() behavior changes.
EVALUATION_PROTOCOL_ID = "abgs-eval-hybrid-2"

LIVE_EVAL_FAILURE_SENTINEL = "REFUSE: live evaluation failed"


def evaluate(
    records: list[BenchmarkRecord],
    model_names: list[str],
    *,
    critic_model: str | None = None,
) -> tuple[list[EvaluationRecord], EvaluationSummary]:
    evaluations: list[EvaluationRecord] = []
    progress_n = max(0, int(os.getenv("ABGS_EVAL_PROGRESS_INTERVAL", "25")))
    delay_ms = max(0, int(os.getenv("ABGS_EVAL_API_DELAY_MS", "0") or "0"))

    for model_name in model_names:
        for i, record in enumerate(records):
            payload = _model_response(model_name, record)
            response = str(payload["response"])
            refused = bool(payload["refused"])
            live_failed = bool(payload.get("live_eval_failed"))

            if live_failed:
                cleaned = ""
                exact_match = False
                support_rate = 0.0
                scoring_trace: dict[str, float | str] = {
                    "mode": "live_eval_failed",
                    "citation_support_rate": 0.0,
                    "answer_alignment_score": 0.0,
                }
                refusal_type: str | None = "evaluation_failure"
            else:
                cleaned = "" if refused else response
                exact_match = _exact_match(cleaned, record)
                support_rate, scoring_trace = _support_rate(cleaned, record, exact_match)
                refusal_type = _refusal_type(record) if refused else None

            evaluations.append(
                EvaluationRecord(
                    benchmark_id=record.id,
                    model_name=model_name,
                    response=response,
                    exact_match=exact_match,
                    support_rate=support_rate,
                    refused=refused,
                    refusal_type=refusal_type,
                    scoring_trace=scoring_trace,
                )
            )

            if progress_n > 0 and (i + 1) % progress_n == 0:
                LOGGER.info(
                    "eval progress model=%s item %s/%s",
                    model_name,
                    i + 1,
                    len(records),
                )
            if delay_ms > 0 and _is_live_model(model_name):
                time.sleep(delay_ms / 1000.0)

    if critic_model:
        evaluations = apply_critic_to_evaluations(records, evaluations, critic_model)

    return evaluations, _summary(records, evaluations)


def _is_live_model(model_name: str) -> bool:
    return model_name.startswith("gemini:") or model_name == "anthropic" or model_name.startswith("anthropic:")


def _model_response(model_name: str, record: BenchmarkRecord) -> dict[str, object]:
    if model_name.startswith("gemini:"):
        live_model = model_name.split(":", 1)[1]
        try:
            payload = answer_question(live_model, record)
            return {
                "response": payload["answer"],
                "refused": payload["refused"],
            }
        except GeminiEvaluationError:
            return {
                "response": LIVE_EVAL_FAILURE_SENTINEL,
                "refused": True,
                "live_eval_failed": True,
            }
    if model_name == "anthropic" or model_name.startswith("anthropic:"):
        live_model = model_name.split(":", 1)[1] if ":" in model_name else None
        try:
            payload = answer_anthropic_question(live_model, record)
            return {
                "response": payload["answer"],
                "refused": payload["refused"],
            }
        except AnthropicEvaluationError:
            return {
                "response": LIVE_EVAL_FAILURE_SENTINEL,
                "refused": True,
                "live_eval_failed": True,
            }
    if model_name == "oracle":
        return {"response": record.answer, "refused": False}
    if model_name == "extractive_baseline":
        return {"response": record.metadata["citations"][0]["text"], "refused": False}
    if model_name == "cautious_refuser":
        if _should_refuse(record):
            return {"response": "REFUSE: insufficient certainty", "refused": True}
        return {"response": record.metadata["citations"][0]["text"], "refused": False}
    return {"response": record.metadata["citations"][0]["text"], "refused": False}


def _exact_match(response: str, record: BenchmarkRecord) -> bool:
    normalized_response = normalized_text(response)
    if not normalized_response:
        return False
    candidates = [record.answer, *record.acceptable_answers]
    return normalized_response in {normalized_text(candidate) for candidate in candidates}


def _support_rate(response: str, record: BenchmarkRecord, exact_match: bool) -> tuple[float, dict[str, float | str]]:
    if not response:
        return 0.0, {
            "mode": "empty_response",
            "citation_support_rate": 0.0,
            "answer_alignment_score": 0.0,
        }
    if exact_match:
        return 1.0, {
            "mode": "exact_match",
            "citation_support_rate": 1.0,
            "answer_alignment_score": 1.0,
        }
    citation_support_rate = _citation_support_rate(response, record)
    answer_alignment_score = _answer_alignment_score(response, record)
    support_rate = round(max(citation_support_rate, answer_alignment_score), 3)
    return support_rate, {
        "mode": "hybrid_alignment",
        "citation_support_rate": citation_support_rate,
        "answer_alignment_score": answer_alignment_score,
    }


def _citation_support_rate(response: str, record: BenchmarkRecord) -> float:
    supporting = 0
    citations = record.metadata["citations"]
    for citation in citations:
        matched, _, _ = text_contains_quote(response, citation["text"])
        if matched:
            supporting += 1
    return round(supporting / max(1, len(citations)), 3)


def _answer_alignment_score(response: str, record: BenchmarkRecord) -> float:
    normalized_response = normalized_text(response)
    if not normalized_response:
        return 0.0
    candidates = [record.answer, *record.acceptable_answers]
    best_score = 0.0
    response_tokens = _token_set(normalized_response)
    for candidate in candidates:
        normalized_candidate = normalized_text(candidate)
        if not normalized_candidate:
            continue
        candidate_tokens = _token_set(normalized_candidate)
        overlap_score = _token_f1(response_tokens, candidate_tokens)
        sequence_score = SequenceMatcher(None, normalized_response, normalized_candidate).ratio()
        best_score = max(best_score, overlap_score, sequence_score)
    return round(best_score, 3)


def _refusal_type(record: BenchmarkRecord) -> str:
    return "appropriate_refusal" if _should_refuse(record) else "inappropriate_refusal"


def _should_refuse(record: BenchmarkRecord) -> bool:
    return (
        record.difficulty.value == "L3"
        or "hallucination_risk" in record.metadata["failure_modes"]
        or "multi_hop_required" in record.metadata["failure_modes"]
    )


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9]+", text.lower()))


def _token_f1(left_tokens: set[str], right_tokens: set[str]) -> float:
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    if overlap == 0:
        return 0.0
    precision = overlap / len(left_tokens)
    recall = overlap / len(right_tokens)
    return (2 * precision * recall) / max(1e-9, precision + recall)


def _summary(benchmarks: list[BenchmarkRecord], records: list[EvaluationRecord]) -> EvaluationSummary:
    benchmark_index = {record.id: record for record in benchmarks}
    models: dict[str, dict[str, object]] = defaultdict(_empty_model_metrics)

    for record in records:
        benchmark = benchmark_index[record.benchmark_id]
        model = models[record.model_name]
        _accumulate(model["overall"], record)
        _accumulate(model["by_difficulty"][benchmark.difficulty.value], record)
        question_type = benchmark.metadata["generation_trace"]["question_type"]
        _accumulate(model["by_question_type"][question_type], record)
        chunk_mode = "multi_chunk" if benchmark.metadata["quality_signals"].get("multi_chunk_required", False) else "single_chunk"
        _accumulate(model["by_chunk_mode"][chunk_mode], record)

    final_models: dict[str, dict[str, object]] = {}
    for model_name, metrics in models.items():
        overall = _finalize_bucket(metrics["overall"])
        final_models[model_name] = {
            "overall": overall,
            "by_difficulty": {
                key: _finalize_bucket(value)
                for key, value in metrics["by_difficulty"].items()
            },
            "by_question_type": {
                key: _finalize_bucket(value)
                for key, value in metrics["by_question_type"].items()
            },
            "by_chunk_mode": {
                key: _finalize_bucket(value)
                for key, value in metrics["by_chunk_mode"].items()
            },
            "exact_match_rate": overall["exact_match_rate"],
            "answer_support_rate": overall["answer_support_rate"],
            "citation_support_rate": overall["citation_support_rate"],
            "answer_alignment_rate": overall["answer_alignment_rate"],
            "refusal_rate": overall["refusal_rate"],
            "appropriate_refusal_rate": overall["appropriate_refusal_rate"],
            "inappropriate_refusal_rate": overall["inappropriate_refusal_rate"],
            "evaluation_failure_rate": overall.get("evaluation_failure_rate", 0.0),
            "total": overall["total"],
        }

    return EvaluationSummary(models=final_models)


def _empty_model_metrics() -> dict[str, object]:
    return {
        "overall": _empty_bucket(),
        "by_difficulty": defaultdict(_empty_bucket),
        "by_question_type": defaultdict(_empty_bucket),
        "by_chunk_mode": defaultdict(_empty_bucket),
    }


def _empty_bucket() -> dict[str, float | int]:
    return {
        "total": 0,
        "exact_match_rate": 0.0,
        "answer_support_rate": 0.0,
        "citation_support_rate": 0.0,
        "answer_alignment_rate": 0.0,
        "refusal_rate": 0.0,
        "appropriate_refusal_rate": 0.0,
        "inappropriate_refusal_rate": 0.0,
        "evaluation_failure_rate": 0.0,
    }


def _accumulate(bucket: dict[str, float | int], record: EvaluationRecord) -> None:
    bucket["total"] += 1
    bucket["exact_match_rate"] += 1 if record.exact_match else 0
    bucket["answer_support_rate"] += record.support_rate
    bucket["citation_support_rate"] += float(record.scoring_trace.get("citation_support_rate", 0.0))
    bucket["answer_alignment_rate"] += float(record.scoring_trace.get("answer_alignment_score", 0.0))
    bucket["refusal_rate"] += 1 if record.refused else 0
    bucket["appropriate_refusal_rate"] += 1 if record.refusal_type == "appropriate_refusal" else 0
    bucket["inappropriate_refusal_rate"] += 1 if record.refusal_type == "inappropriate_refusal" else 0
    bucket["evaluation_failure_rate"] += 1 if record.refusal_type == "evaluation_failure" else 0


def _finalize_bucket(bucket: dict[str, float | int]) -> dict[str, float | int]:
    total = max(1, int(bucket["total"]))
    finalized = dict(bucket)
    for key in (
        "exact_match_rate",
        "answer_support_rate",
        "citation_support_rate",
        "answer_alignment_rate",
        "refusal_rate",
        "appropriate_refusal_rate",
        "inappropriate_refusal_rate",
        "evaluation_failure_rate",
    ):
        finalized[key] = round(float(finalized[key]) / total, 3)
    finalized["total"] = int(bucket["total"])
    return finalized
