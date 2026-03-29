from __future__ import annotations

import json
from pathlib import Path

from abgs.config import load_config
from abgs.contracts import BenchmarkRecord, CandidateAnswer, CandidateQuestion, CitationSpan, DifficultyLevel, PromptTrace, QuestionType
from abgs.evaluate import pipeline as evaluate_pipeline
from abgs.evaluate.pipeline import _model_response, _support_rate
from abgs.matching import match_quote_to_text
from abgs.pipeline import run_pipeline
from abgs.reporting.comparison import compare_runs, render_comparison_markdown
from abgs.validate.pipeline import validate_records, validation_summary


def test_pipeline_generates_core_artifacts(tmp_path: Path) -> None:
    config = load_config("data/reference_configs/technical_manuals.yaml")
    manifest = run_pipeline("data/samples", tmp_path, config)

    assert manifest.outputs["accepted"].endswith("validated_qa.jsonl")
    assert (tmp_path / "run_manifest.json").exists()
    assert (tmp_path / "dataset_profile.json").exists()
    assert (tmp_path / "evaluation_summary.json").exists()
    assert (tmp_path / "benchmark_report.json").exists()
    assert (tmp_path / "benchmark_report.md").exists()
    assert (tmp_path / "evaluation_protocol.json").exists()
    assert (tmp_path / "operator_summary.json").exists()
    assert (tmp_path / "ingestion_summary.json").exists()
    assert (tmp_path / "generation_summary.json").exists()


def test_dataset_profile_contains_multi_chunk_ratio(tmp_path: Path) -> None:
    config = load_config("data/reference_configs/technical_manuals.yaml")
    run_pipeline("data/samples", tmp_path, config)

    profile = json.loads((tmp_path / "dataset_profile.json").read_text(encoding="utf-8"))
    report = json.loads((tmp_path / "benchmark_report.json").read_text(encoding="utf-8"))
    assert "multi_chunk_ratio" in profile
    assert "demo_grade_slice" in report
    assert "executive_summary" in report
    assert "model_behavior_profiles" in report
    assert "use_case_guidance" in report
    assert "evaluation_protocol" in report
    assert "corpus_health" in report
    assert profile["total_questions"] >= 1


def test_run_manifest_tracks_config_hash(tmp_path: Path) -> None:
    config = load_config("data/reference_configs/policy_docs.yaml")
    run_pipeline("data/samples", tmp_path, config)

    manifest = json.loads((tmp_path / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["config_hash"]
    assert manifest["pipeline_version"] == "0.1.0"


def test_evaluation_summary_tracks_refusals(tmp_path: Path) -> None:
    config = load_config("data/reference_configs/technical_manuals.yaml")
    run_pipeline("data/samples", tmp_path, config)

    summary = json.loads((tmp_path / "evaluation_summary.json").read_text(encoding="utf-8"))
    assert summary["models"]["cautious_refuser"]["refusal_rate"] > 0
    assert "citation_support_rate" in summary["models"]["extractive_baseline"]
    assert "answer_alignment_rate" in summary["models"]["extractive_baseline"]


def test_operator_summary_includes_guidance_and_budget_controls(tmp_path: Path) -> None:
    config = load_config("data/reference_configs/technical_manuals.yaml")
    run_pipeline("data/samples", tmp_path, config)

    summary = json.loads((tmp_path / "operator_summary.json").read_text(encoding="utf-8"))
    assert summary["benchmark_quality_guidelines"]["multi_chunk_ratio"]["target"] == 0.4
    assert summary["cost_controls"]["max_cost_usd"] == 25.0
    assert summary["cost_controls"]["max_tokens_total"] == 250000
    assert "preprocessing_summary" in summary
    assert "generation_summary" in summary


def test_policy_preprocessing_filters_front_matter(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "policy_noise.txt").write_text(
        (
            "TABLE OF CONTENTS\n"
            "Introduction .......... 1\n"
            "Revision History .......... 2\n"
            "Executive Summary .......... 3\n\n"
            "AI governance requires documented evaluation objectives. "
            "Teams must define mission context and operational constraints. "
            "Benchmark review should distinguish unsupported answers from grounded answers. "
            "Reliable policy oversight requires traceable evidence and measurable controls."
        ),
        encoding="utf-8",
    )

    config = load_config("data/reference_configs/policy_docs.yaml")
    config.chunking.target_tokens = 18
    config.generation.target_questions_per_chunk = 1
    run_pipeline(corpus_dir, tmp_path / "out", config)

    ingestion_summary = json.loads((tmp_path / "out" / "ingestion_summary.json").read_text(encoding="utf-8"))
    assert ingestion_summary["filtered_chunk_count"] >= 1
    filtered_lines = (tmp_path / "out" / "filtered_chunks.jsonl").read_text(encoding="utf-8")
    assert "table_of_contents_pattern" in filtered_lines or "front_matter_marker" in filtered_lines


def test_generation_summary_tracks_upstream_duplicate_suppression(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "dup_corpus"
    corpus_dir.mkdir()
    (corpus_dir / "dup.txt").write_text(
        (
            "Cybersecurity risk management requires documented control selection. "
            "Cybersecurity risk management requires documented control selection. "
            "Cybersecurity risk management requires documented control selection. "
            "Cybersecurity risk management requires documented control selection. "
            "Cybersecurity risk management requires documented control selection."
        ),
        encoding="utf-8",
    )

    config = load_config("data/reference_configs/policy_docs.yaml")
    config.chunking.target_tokens = 10
    config.generation.target_questions_per_chunk = 2
    run_pipeline(corpus_dir, tmp_path / "dup_out", config)

    generation_summary = json.loads((tmp_path / "dup_out" / "generation_summary.json").read_text(encoding="utf-8"))
    assert generation_summary["skipped_duplicate_signatures"] > 0


def test_run_comparison_outputs_json_and_markdown(tmp_path: Path) -> None:
    config = load_config("data/reference_configs/technical_manuals.yaml")
    baseline_dir = tmp_path / "baseline"
    candidate_dir = tmp_path / "candidate"
    report_dir = tmp_path / "report"

    run_pipeline("data/samples", baseline_dir, config)
    run_pipeline("data/samples", candidate_dir, config)

    comparison = compare_runs(baseline_dir, candidate_dir, report_dir)
    markdown = render_comparison_markdown(comparison)

    assert (report_dir / "run_comparison.json").exists()
    assert (report_dir / "run_comparison.md").exists()
    assert comparison["summary"]["baseline_dataset_size"] >= 1
    assert "# Run Comparison" in markdown


def test_validation_accepts_support_quotes_without_answer_string_match() -> None:
    config = load_config("data/reference_configs/policy_docs.yaml")
    question = CandidateQuestion(
        question_id="q-1",
        run_id="run-1",
        document_id="doc-1",
        chunk_ids=["doc-1-chunk-1"],
        question="What does the document say about risk tolerance?",
        question_type=QuestionType.FACTUAL,
        topic="risk tolerance",
        prompt_trace=PromptTrace(
            prompt_version="v1",
            prompt_template_hash="hash-a",
            prompt_inputs_hash="hash-b",
            model_name="gemini-2.5-flash",
            provider="gemini",
            seed=1,
        ),
        quality_signals={"multi_chunk_required": False, "chunk_count": 1, "topic": "risk tolerance"},
    )
    answer = CandidateAnswer(
        question_id="q-1",
        answer="Each organization sets its own risk tolerance.",
        acceptable_answers=["Each organization sets its own risk tolerance."],
        citations=[
            CitationSpan(
                document_id="doc-1",
                chunk_id="doc-1-chunk-1",
                chunk_hash="chunk-hash",
                start_char=0,
                end_char=83,
                text="Each DoD organization retains the autonomy to determine its own risk tolerance.",
            )
        ],
        token_usage={"prompt_tokens": 10, "completion_tokens": 8},
        estimated_cost_usd=0.0,
        trace={
            "source_chunk_ids": ["doc-1-chunk-1"],
            "support_quotes": [
                "Each DoD organization retains the autonomy to determine its own risk tolerance."
            ],
        },
    )

    accepted, rejected, validations = validate_records([question], [answer], config)
    assert len(accepted) == 1
    assert len(rejected) == 0
    assert validations[0].grounded is True


def test_quote_matching_recovers_hyphenated_line_wrap() -> None:
    text = "The Department will accelerate AI experi-\nmentation across the force."
    quote = "The Department will accelerate AI experimentation across the force."

    match = match_quote_to_text(text, quote)
    assert match.matched is True
    assert match.recovered is True
    assert match.mode in {"fuzzy_normalized", "fuzzy_window"}


def test_validation_summary_tracks_recovered_grounding(tmp_path: Path) -> None:
    config = load_config("data/reference_configs/policy_docs.yaml")
    question = CandidateQuestion(
        question_id="q-2",
        run_id="run-1",
        document_id="doc-1",
        chunk_ids=["doc-1-chunk-1"],
        question="How is experimentation accelerated?",
        question_type=QuestionType.PROCEDURAL,
        topic="experimentation",
        prompt_trace=PromptTrace(
            prompt_version="v1",
            prompt_template_hash="hash-a",
            prompt_inputs_hash="hash-b",
            model_name="gemini-2.5-flash",
            provider="gemini",
            seed=1,
        ),
        quality_signals={"multi_chunk_required": False, "chunk_count": 1, "topic": "experimentation"},
    )
    answer = CandidateAnswer(
        question_id="q-2",
        answer="The Department accelerates experimentation across the force.",
        acceptable_answers=["The Department accelerates experimentation across the force."],
        citations=[
            CitationSpan(
                document_id="doc-1",
                chunk_id="doc-1-chunk-1",
                chunk_hash="chunk-hash",
                start_char=0,
                end_char=68,
                text="The Department will accelerate AI experi-\nmentation across the force.",
            )
        ],
        token_usage={"prompt_tokens": 10, "completion_tokens": 8},
        estimated_cost_usd=0.0,
        trace={
            "source_chunk_ids": ["doc-1-chunk-1"],
            "support_quotes": [
                "The Department will accelerate AI experimentation across the force."
            ],
        },
    )

    _, _, validations = validate_records([question], [answer], config)
    summary = validation_summary(validations)
    assert validations[0].strict_grounded is False
    assert validations[0].recovered_grounding is True
    assert summary["recovered_grounding_count"] == 1
    assert summary["recovered_grounding_rate"] == 1.0


def test_support_scoring_credits_grounded_paraphrase() -> None:
    record = BenchmarkRecord(
        id="b-1",
        question="What does the policy require?",
        answer="The policy requires documented evaluation objectives and traceable evidence.",
        acceptable_answers=["Documented evaluation objectives and traceable evidence are required."],
        sources=["chunk-1"],
        difficulty=DifficultyLevel.L2,
        category="policy",
        metadata={
            "citations": [
                {
                    "text": "The policy requires documented evaluation objectives and traceable evidence."
                }
            ],
            "failure_modes": [],
            "quality_signals": {"multi_chunk_required": True},
            "generation_trace": {"question_type": "analytical"},
        },
    )

    support_rate, trace = _support_rate(
        "The policy calls for traceable evidence and documented evaluation objectives.",
        record,
        exact_match=False,
    )
    assert support_rate >= 0.75
    assert trace["answer_alignment_score"] > trace["citation_support_rate"]


def test_anthropic_model_response_uses_provider(monkeypatch) -> None:
    record = BenchmarkRecord(
        id="b-2",
        question="What does the policy require?",
        answer="The policy requires documented evaluation objectives.",
        acceptable_answers=["Documented evaluation objectives are required."],
        sources=["chunk-1"],
        difficulty=DifficultyLevel.L1,
        category="policy",
        metadata={
            "citations": [{"text": "The policy requires documented evaluation objectives."}],
            "failure_modes": [],
            "quality_signals": {"multi_chunk_required": False},
            "generation_trace": {"question_type": "factual"},
        },
    )

    def fake_answer(model_name, _record):
        assert model_name == "claude-sonnet-4-20250514"
        return {"answer": "Documented evaluation objectives are required.", "refused": False}

    monkeypatch.setattr(evaluate_pipeline, "answer_anthropic_question", fake_answer)
    payload = _model_response("anthropic:claude-sonnet-4-20250514", record)
    assert payload["response"] == "Documented evaluation objectives are required."
    assert payload["refused"] is False
