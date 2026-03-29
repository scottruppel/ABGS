from __future__ import annotations

from unittest.mock import patch

from abgs.contracts import BenchmarkRecord, DifficultyLevel
from abgs.evaluate.gemini_provider import GeminiEvaluationError
from abgs.evaluate.pipeline import LIVE_EVAL_FAILURE_SENTINEL, evaluate


def _minimal_record(rid: str = "b1") -> BenchmarkRecord:
    return BenchmarkRecord(
        id=rid,
        question="Q?",
        answer="A",
        acceptable_answers=[],
        sources=[],
        difficulty=DifficultyLevel.L1,
        category="test",
        metadata={
            "citations": [{"text": "cite"}],
            "failure_modes": [],
            "generation_trace": {"question_type": "factual"},
            "quality_signals": {"multi_chunk_required": False},
        },
    )


@patch("abgs.evaluate.pipeline.answer_question")
def test_live_api_failure_sets_evaluation_failure_refusal(mock_ans, monkeypatch) -> None:
    mock_ans.side_effect = GeminiEvaluationError("network")

    rec = _minimal_record()
    ev, summary = evaluate([rec], ["gemini:gemini-2.5-flash"])

    assert len(ev) == 1
    assert ev[0].refusal_type == "evaluation_failure"
    assert ev[0].response == LIVE_EVAL_FAILURE_SENTINEL
    assert ev[0].scoring_trace.get("mode") == "live_eval_failed"
    overall = summary.models["gemini:gemini-2.5-flash"]["overall"]
    assert overall["evaluation_failure_rate"] == 1.0
    assert overall["inappropriate_refusal_rate"] == 0.0
    assert overall["appropriate_refusal_rate"] == 0.0


def test_model_refusal_uses_benchmark_refusal_type() -> None:
    rec = _minimal_record()
    rec.metadata["failure_modes"] = ["hallucination_risk"]
    ev, summary = evaluate([rec], ["cautious_refuser"])
    assert ev[0].refused is True
    assert ev[0].refusal_type == "appropriate_refusal"
    assert summary.models["cautious_refuser"]["overall"]["evaluation_failure_rate"] == 0.0
