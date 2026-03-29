from __future__ import annotations

from abgs.evaluate.pipeline import EVALUATION_PROTOCOL_ID
from abgs.reporting.evaluation_protocol import build_evaluation_protocol
from abgs.reporting.model_profiles import METRIC_GAP, build_model_profiles, build_use_case_guidance


def _pair(g_overall: dict, a_overall: dict, g_mc: float, a_mc: float) -> dict:
    return {
        "gemini:gemini-2.5-flash": {
            "overall": g_overall,
            "by_chunk_mode": {"multi_chunk": {"answer_support_rate": g_mc}},
        },
        "anthropic": {
            "overall": a_overall,
            "by_chunk_mode": {"multi_chunk": {"answer_support_rate": a_mc}},
        },
    }


def test_profiles_favor_gemini_on_citation_and_claude_on_refusal() -> None:
    g_overall = {
        "citation_support_rate": 0.5,
        "answer_support_rate": 0.8,
        "answer_alignment_rate": 0.7,
        "refusal_rate": 0.15,
        "appropriate_refusal_rate": 0.05,
        "inappropriate_refusal_rate": 0.05,
    }
    a_overall = {
        "citation_support_rate": 0.3,
        "answer_support_rate": 0.75,
        "answer_alignment_rate": 0.68,
        "refusal_rate": 0.08,
        "appropriate_refusal_rate": 0.02,
        "inappropriate_refusal_rate": 0.04,
    }
    summary = _pair(g_overall, a_overall, 0.75, 0.55)
    profiles = build_model_profiles(summary, resolved_models={"anthropic": "claude-sonnet-4-20250514"})
    assert "Gemini 2.5 Flash" in profiles["gemini:gemini-2.5-flash"]["display_name"]
    assert any("citation" in s.lower() for s in profiles["gemini:gemini-2.5-flash"]["strengths"])
    assert any("refusal" in s.lower() for s in profiles["gemini:gemini-2.5-flash"]["weaknesses"])
    assert any("refusal" in s.lower() for s in profiles["anthropic"]["strengths"])


def test_use_case_guidance_emits_when_gaps_exceed_threshold() -> None:
    g_overall = {
        "citation_support_rate": 0.5,
        "answer_support_rate": 0.8,
        "answer_alignment_rate": 0.7,
        "refusal_rate": 0.2,
        "appropriate_refusal_rate": 0.05,
        "inappropriate_refusal_rate": 0.05,
    }
    a_overall = {
        "citation_support_rate": 0.3,
        "answer_support_rate": 0.75,
        "answer_alignment_rate": 0.68,
        "refusal_rate": 0.08,
        "appropriate_refusal_rate": 0.02,
        "inappropriate_refusal_rate": 0.04,
    }
    summary = _pair(g_overall, a_overall, 0.8, 0.5)
    lines = build_use_case_guidance(summary, resolved_models={"anthropic": "claude-sonnet-4-20250514"})
    text = "\n".join(lines)
    assert "Compliance" in text or "grounding" in text
    assert "Exploratory" in text or "friction" in text


def test_metric_gap_constant() -> None:
    assert METRIC_GAP >= 0.0


def test_build_evaluation_protocol_hashes(tmp_path) -> None:
    vq = tmp_path / "validated_qa.jsonl"
    vq.write_text('{"id":"1"}\n', encoding="utf-8")
    mf = tmp_path / "run_manifest.json"
    mf.write_text('{"run_id":"abc","pipeline_version":"0.1.0","config_hash":"x","input_corpus_hashes":[]}', encoding="utf-8")
    p = build_evaluation_protocol(
        validated_qa_path=vq,
        run_manifest_path=mf,
        resolved_models={"gemini": "gemini-2.5-flash", "anthropic": "claude-sonnet-4-20250514"},
    )
    assert len(p["validated_qa_sha256"]) == 64
    assert len(p["run_manifest_sha256"]) == 64
    assert p["evaluation_protocol_id"] == EVALUATION_PROTOCOL_ID
    assert p["resolved_models"]["anthropic"] == "claude-sonnet-4-20250514"
