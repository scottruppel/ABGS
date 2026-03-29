from __future__ import annotations

from abgs.contracts import BenchmarkRecord, DifficultyLevel, EvaluationRecord
from abgs.evaluate import critic as critic_mod
from abgs.evaluate.critic import CRITIC_PROTOCOL_ID, apply_critic_to_evaluations


def _record() -> BenchmarkRecord:
    return BenchmarkRecord(
        id="b1",
        question="What hook size?",
        answer="Size 2",
        acceptable_answers=["2"],
        sources=["c1"],
        difficulty=DifficultyLevel.L1,
        category="test",
        metadata={
            "citations": [{"text": "We use size 2 hooks for bass."}],
            "failure_modes": [],
            "quality_signals": {"multi_chunk_required": False},
            "generation_trace": {"question_type": "factual"},
        },
    )


def test_apply_critic_skips_baselines(monkeypatch) -> None:
    rec = _record()
    evs = [
        EvaluationRecord(
            benchmark_id="b1",
            model_name="extractive_baseline",
            response="x",
            exact_match=False,
            support_rate=0.5,
            refused=False,
            refusal_type=None,
            scoring_trace={},
        ),
        EvaluationRecord(
            benchmark_id="b1",
            model_name="gemini:gemini-2.5-flash",
            response="y",
            exact_match=False,
            support_rate=0.5,
            refused=False,
            refusal_type=None,
            scoring_trace={},
        ),
    ]

    def fake(*_a, **_k):
        return {
            "classification": "PASS",
            "reasoning": "",
            "source_gap": "",
            "critic_model": "gemini:gemini-2.5-flash",
            "critic_protocol_id": CRITIC_PROTOCOL_ID,
        }

    monkeypatch.setattr(critic_mod, "critique_response", fake)
    out = apply_critic_to_evaluations([rec], evs, "gemini:gemini-2.5-flash")
    assert out[0].scoring_trace.get("critic") is None
    assert out[1].scoring_trace.get("critic", {}).get("classification") == "PASS"


def test_apply_critic_annotates_gemini(monkeypatch) -> None:
    rec = _record()
    evs = [
        EvaluationRecord(
            benchmark_id="b1",
            model_name="gemini:gemini-2.5-flash",
            response="y",
            exact_match=False,
            support_rate=0.5,
            refused=False,
            refusal_type=None,
            scoring_trace={},
        ),
    ]

    def fake(cm, r, resp, ref):
        return {
            "classification": "PASS",
            "reasoning": "ok",
            "source_gap": "",
            "critic_model": cm,
            "critic_protocol_id": CRITIC_PROTOCOL_ID,
        }

    monkeypatch.setattr(critic_mod, "critique_response", fake)
    out = apply_critic_to_evaluations([rec], evs, "gemini:gemini-2.5-flash")
    assert out[0].scoring_trace["critic"]["classification"] == "PASS"


