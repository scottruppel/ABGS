from __future__ import annotations

import logging
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from abgs import __version__
from abgs.config import PipelineConfig
from abgs.contracts import RunManifest, StageSummary
from abgs.dataset.pipeline import build_dataset_profile
from abgs.evaluate.pipeline import evaluate
from abgs.generate.pipeline import generate_candidates
from abgs.hashing import hash_file, sha256_json
from abgs.ingest.pipeline import ingest_corpus
from abgs.io_utils import ensure_directory, write_json, write_jsonl
from abgs.reporting.benchmark_report import write_benchmark_report
from abgs.reporting.evaluation_protocol import build_evaluation_protocol
from abgs.validate.pipeline import validate_records, validation_summary

LOGGER = logging.getLogger(__name__)


def run_pipeline(input_dir: str | Path, output_dir: str | Path, config: PipelineConfig) -> RunManifest:
    run_id = uuid4().hex[:12]
    output_root = ensure_directory(output_dir)
    stage_summaries: dict[str, StageSummary] = {}
    LOGGER.info("Starting ABGS run %s", run_id)
    LOGGER.info("Input corpus: %s", input_dir)
    LOGGER.info("Output directory: %s", output_root)
    LOGGER.info("Configured models: %s", ", ".join(config.evaluation.models))

    ingest_started = _now()
    documents, chunks, content_index, ingestion_summary = ingest_corpus(input_dir, config)
    write_jsonl(output_root / "documents.jsonl", documents)
    write_jsonl(output_root / "chunks.jsonl", chunks)
    write_json(output_root / "content_index.json", content_index)
    write_json(output_root / "ingestion_summary.json", ingestion_summary)
    write_jsonl(output_root / "filtered_chunks.jsonl", ingestion_summary["filtered_chunks"])
    stage_summaries["ingest"] = StageSummary(
        started_at=ingest_started,
        completed_at=_now(),
        record_count=len(chunks),
        metadata={
            "documents": len(documents),
            "raw_chunks": ingestion_summary["raw_chunk_count"],
            "filtered_chunks": ingestion_summary["filtered_chunk_count"],
        },
    )
    LOGGER.info(
        "Ingestion complete: %d documents, %d accepted chunks, %d filtered chunks",
        len(documents),
        len(chunks),
        ingestion_summary["filtered_chunk_count"],
    )

    generation_started = _now()
    questions, coverage, answers, generation_summary = generate_candidates(run_id, documents, chunks, config)
    write_jsonl(output_root / "candidate_questions.jsonl", questions)
    write_jsonl(output_root / "coverage_ledger.jsonl", coverage)
    write_jsonl(output_root / "candidate_qa.jsonl", answers)
    write_json(output_root / "generation_summary.json", generation_summary)
    stage_summaries["question_generation"] = StageSummary(
        started_at=generation_started,
        completed_at=_now(),
        record_count=len(questions),
        metadata={
            "coverage_entries": len(coverage),
            "skipped_duplicate_signatures": generation_summary["skipped_duplicate_signatures"],
            "skipped_low_quality_topics": generation_summary["skipped_low_quality_topics"],
        },
    )
    stage_summaries["answer_generation"] = StageSummary(
        started_at=generation_started,
        completed_at=_now(),
        record_count=len(answers),
    )
    LOGGER.info(
        "Generation complete: %d questions, %d answers, %d duplicate signatures skipped, %d low-quality topics skipped",
        len(questions),
        len(answers),
        generation_summary["skipped_duplicate_signatures"],
        generation_summary["skipped_low_quality_topics"],
    )

    validation_started = _now()
    accepted, rejected, validations = validate_records(questions, answers, config)
    validation_metrics = validation_summary(validations)
    write_jsonl(output_root / "validated_qa.jsonl", accepted)
    write_jsonl(output_root / "rejected_qa.jsonl", rejected)
    write_json(output_root / "validation_summary.json", validation_metrics)
    stage_summaries["validation"] = StageSummary(
        started_at=validation_started,
        completed_at=_now(),
        record_count=len(validations),
        metadata={"accepted": len(accepted), "rejected": len(rejected)},
    )
    LOGGER.info("Validation complete: %d accepted, %d rejected", len(accepted), len(rejected))

    dataset_profile = build_dataset_profile(accepted, coverage)
    write_json(output_root / "dataset_profile.json", dataset_profile)
    LOGGER.info(
        "Dataset profile: %d questions, %.3f multi-chunk ratio",
        dataset_profile.total_questions,
        dataset_profile.multi_chunk_ratio,
    )

    evaluations, evaluation_summary = evaluate(
        accepted,
        config.evaluation.models,
        critic_model=config.evaluation.critic_model,
    )
    write_jsonl(output_root / "evaluation_records.jsonl", evaluations)
    write_json(output_root / "evaluation_summary.json", evaluation_summary)

    manifest = RunManifest(
        run_id=run_id,
        pipeline_version=__version__,
        config_hash=_config_hash(config),
        input_corpus_hashes=[hash_file(path) for path in sorted(Path(input_dir).glob("*")) if path.is_file()],
        stages=stage_summaries,
        outputs={
            "accepted": str(output_root / "validated_qa.jsonl"),
            "rejected": str(output_root / "rejected_qa.jsonl"),
            "dataset_profile": str(output_root / "dataset_profile.json"),
            "evaluation_summary": str(output_root / "evaluation_summary.json"),
            "benchmark_report_json": str(output_root / "benchmark_report.json"),
            "benchmark_report_markdown": str(output_root / "benchmark_report.md"),
            "evaluation_protocol": str(output_root / "evaluation_protocol.json"),
            "operator_summary": str(output_root / "operator_summary.json"),
            "ingestion_summary": str(output_root / "ingestion_summary.json"),
            "generation_summary": str(output_root / "generation_summary.json"),
        },
    )
    write_json(output_root / "run_manifest.json", manifest)

    gemini_model_id = config.generation.model_name
    for m in config.evaluation.models:
        if m.startswith("gemini:"):
            gemini_model_id = m.split(":", 1)[1]
            break
    evaluation_protocol = build_evaluation_protocol(
        validated_qa_path=output_root / "validated_qa.jsonl",
        run_manifest_path=output_root / "run_manifest.json",
        resolved_models={
            "gemini": gemini_model_id,
            "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        },
    )
    write_benchmark_report(
        output_dir=output_root,
        records=accepted,
        dataset_profile=dataset_profile,
        validation_summary=validation_metrics,
        evaluation_records=evaluations,
        evaluation_summary=evaluation_summary.models,
        evaluation_protocol=evaluation_protocol,
        resolved_models=evaluation_protocol["resolved_models"],
    )
    operator_summary = _build_operator_summary(
        dataset_profile=dataset_profile,
        ingestion_summary=ingestion_summary,
        generation_summary=generation_summary,
        validation_metrics=validation_metrics,
        evaluation_summary=evaluation_summary.models,
        config=config,
    )
    write_json(output_root / "operator_summary.json", operator_summary)
    _log_operator_summary(operator_summary)

    LOGGER.info("Artifacts written under %s", output_root)
    LOGGER.info("Completed pipeline run %s", run_id)
    return manifest


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _config_hash(config: PipelineConfig) -> str:
    return sha256_json(asdict(config))


def _build_operator_summary(
    dataset_profile: object,
    ingestion_summary: dict[str, object],
    generation_summary: dict[str, object],
    validation_metrics: dict[str, object],
    evaluation_summary: dict[str, dict[str, object]],
    config: PipelineConfig,
) -> dict[str, object]:
    status_counts = validation_metrics.get("status_counts", {})
    total_validation = sum(status_counts.values())
    accepted = status_counts.get("accepted", 0)
    validation_pass_rate = accepted / max(1, total_validation)

    model_guidance = {}
    warnings: list[str] = []
    for model_name, metrics in evaluation_summary.items():
        support_rate = float(metrics.get("answer_support_rate", 0.0))
        status = "target"
        if support_rate < config.quality.answer_support_warning:
            status = "warning"
            warnings.append(
                f"Model '{model_name}' answer support rate is below warning threshold at {support_rate:.3f}."
            )
        elif support_rate < config.quality.answer_support_target:
            status = "watch"
        model_guidance[model_name] = {
            "answer_support_rate": support_rate,
            "status": status,
        }

    multi_chunk_status = "target"
    if dataset_profile.multi_chunk_ratio < config.quality.multi_chunk_warning:
        multi_chunk_status = "warning"
        warnings.append(
            f"Multi-chunk ratio is low at {dataset_profile.multi_chunk_ratio:.3f}; investigate coverage or prompt diversity."
        )
    elif dataset_profile.multi_chunk_ratio < config.quality.multi_chunk_target:
        multi_chunk_status = "watch"

    validation_status = "target"
    if validation_pass_rate < config.quality.validation_pass_warning:
        validation_status = "warning"
        warnings.append(
            f"Validation pass rate is low at {validation_pass_rate:.3f}; investigate grounding or source quality."
        )
    elif (
        validation_pass_rate < config.quality.validation_pass_target_min
        or validation_pass_rate > config.quality.validation_pass_target_max
    ):
        validation_status = "watch"

    return {
        "benchmark_quality_guidelines": {
            "multi_chunk_ratio": {
                "actual": round(dataset_profile.multi_chunk_ratio, 3),
                "target": config.quality.multi_chunk_target,
                "warning": config.quality.multi_chunk_warning,
                "status": multi_chunk_status,
            },
            "validation_pass_rate": {
                "actual": round(validation_pass_rate, 3),
                "target_range": [
                    config.quality.validation_pass_target_min,
                    config.quality.validation_pass_target_max,
                ],
                "warning": config.quality.validation_pass_warning,
                "status": validation_status,
            },
            "answer_support_rate": {
                "target": config.quality.answer_support_target,
                "warning": config.quality.answer_support_warning,
                "models": model_guidance,
            },
            "grounding_recovery": {
                "strict_grounding_rate": validation_metrics.get("strict_grounding_rate", 0.0),
                "recovered_grounding_rate": validation_metrics.get("recovered_grounding_rate", 0.0),
                "recovered_grounding_count": validation_metrics.get("recovered_grounding_count", 0),
            },
        },
        "cost_controls": {
            "max_cost_usd": config.evaluation.max_cost_usd,
            "max_tokens_total": config.evaluation.max_tokens_total,
            "enforced": False,
            "note": "Budget guards are configured now and intended for enforcement once live provider integrations are enabled.",
        },
        "preprocessing_summary": {
            "raw_chunk_count": ingestion_summary["raw_chunk_count"],
            "accepted_chunk_count": ingestion_summary["accepted_chunk_count"],
            "filtered_chunk_count": ingestion_summary["filtered_chunk_count"],
            "filtered_reason_counts": ingestion_summary["filtered_reason_counts"],
        },
        "generation_summary": {
            "target_questions": generation_summary["target_questions"],
            "generated_questions": generation_summary["generated_questions"],
            "skipped_duplicate_signatures": generation_summary["skipped_duplicate_signatures"],
            "skipped_low_quality_topics": generation_summary["skipped_low_quality_topics"],
            "unique_topic_count": generation_summary["unique_topic_count"],
        },
        "common_failure_scenarios": [
            {
                "symptom": "Extremely low question diversity",
                "likely_cause": "Coverage settings are too narrow or prompts over-focus on easy sections.",
            },
            {
                "symptom": "High duplicate rejection",
                "likely_cause": "Chunking is too coarse or question prompts are too repetitive.",
            },
            {
                "symptom": "Low grounding rate",
                "likely_cause": "Answer generation is insufficiently constrained to cited source spans.",
            },
            {
                "symptom": "High soft-fail rate",
                "likely_cause": "Source material is ambiguous or validation heuristics need refinement.",
            },
        ],
        "warnings": warnings,
    }


def _log_operator_summary(operator_summary: dict[str, object]) -> None:
    guidelines = operator_summary["benchmark_quality_guidelines"]
    LOGGER.info(
        "Quality guidance: multi-chunk %.3f (%s), validation pass %.3f (%s), recovered grounding %.3f",
        guidelines["multi_chunk_ratio"]["actual"],
        guidelines["multi_chunk_ratio"]["status"],
        guidelines["validation_pass_rate"]["actual"],
        guidelines["validation_pass_rate"]["status"],
        guidelines["grounding_recovery"]["recovered_grounding_rate"],
    )
    LOGGER.info(
        "Cost controls: max_cost_usd=%s, max_tokens_total=%s",
        operator_summary["cost_controls"]["max_cost_usd"],
        operator_summary["cost_controls"]["max_tokens_total"],
    )
    LOGGER.info(
        "Preprocessing summary: %d raw chunks, %d filtered, generation skipped %d duplicate signatures",
        operator_summary["preprocessing_summary"]["raw_chunk_count"],
        operator_summary["preprocessing_summary"]["filtered_chunk_count"],
        operator_summary["generation_summary"]["skipped_duplicate_signatures"],
    )
    for warning in operator_summary["warnings"]:
        LOGGER.warning(warning)
