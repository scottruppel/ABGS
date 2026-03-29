from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from abgs.io_utils import ensure_directory, write_json


def compare_runs(
    baseline_dir: str | Path,
    candidate_dir: str | Path,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    baseline_path = Path(baseline_dir)
    candidate_path = Path(candidate_dir)

    baseline = _load_run_metrics(baseline_path)
    candidate = _load_run_metrics(candidate_path)
    comparison = {
        "baseline_run": baseline["run_name"],
        "candidate_run": candidate["run_name"],
        "baseline_path": str(baseline_path),
        "candidate_path": str(candidate_path),
        "summary": _summary(baseline, candidate),
        "quality_deltas": _quality_deltas(baseline, candidate),
        "preprocessing_deltas": _preprocessing_deltas(baseline, candidate),
        "generation_deltas": _generation_deltas(baseline, candidate),
        "evaluation_deltas": _evaluation_deltas(baseline, candidate),
    }

    if output_dir is not None:
        out_dir = ensure_directory(output_dir)
        write_json(out_dir / "run_comparison.json", comparison)
        (out_dir / "run_comparison.md").write_text(
            render_comparison_markdown(comparison),
            encoding="utf-8",
        )

    return comparison


def render_comparison_markdown(comparison: dict[str, Any]) -> str:
    summary = comparison["summary"]
    quality = comparison["quality_deltas"]
    preprocessing = comparison["preprocessing_deltas"]
    generation = comparison["generation_deltas"]
    evaluation = comparison["evaluation_deltas"]

    lines = [
        "# Run Comparison",
        "",
        f"- Baseline: `{comparison['baseline_run']}`",
        f"- Candidate: `{comparison['candidate_run']}`",
        "",
        "## Summary",
        "",
        f"- Validation pass rate: `{summary['baseline_validation_pass_rate']:.3f}` -> `{summary['candidate_validation_pass_rate']:.3f}` (`{summary['validation_pass_rate_delta']:+.3f}`)",
        f"- Final benchmark size: `{summary['baseline_dataset_size']}` -> `{summary['candidate_dataset_size']}` (`{summary['dataset_size_delta']:+d}`)",
        f"- Hard fails: `{summary['baseline_hard_fail_count']}` -> `{summary['candidate_hard_fail_count']}` (`{summary['hard_fail_delta']:+d}`)",
        "",
        "## Quality Deltas",
        "",
        f"- Multi-chunk ratio delta: `{quality['multi_chunk_ratio_delta']:+.3f}`",
        f"- Avg citations per question delta: `{quality['avg_citations_per_question_delta']:+.3f}`",
        f"- Avg confidence delta: `{quality['avg_confidence_delta']:+.3f}`",
        f"- Recovered grounding rate delta: `{quality['recovered_grounding_rate_delta']:+.3f}`",
        f"- Duplicate hard-fail delta: `{quality['duplicate_hard_fail_delta']:+d}`",
        f"- Low-information soft-fail delta: `{quality['low_information_soft_fail_delta']:+d}`",
        "",
        "## Preprocessing Deltas",
        "",
        f"- Filtered chunk delta: `{preprocessing['filtered_chunk_count_delta']:+d}`",
        f"- Raw chunk delta: `{preprocessing['raw_chunk_count_delta']:+d}`",
        f"- Accepted chunk delta: `{preprocessing['accepted_chunk_count_delta']:+d}`",
        "",
        "## Generation Deltas",
        "",
        f"- Generated question delta: `{generation['generated_questions_delta']:+d}`",
        f"- Duplicate signatures skipped delta: `{generation['skipped_duplicate_signatures_delta']:+d}`",
        f"- Low-quality topics skipped delta: `{generation['skipped_low_quality_topics_delta']:+d}`",
        f"- Unique topic count delta: `{generation['unique_topic_count_delta']:+d}`",
        "",
        "## Evaluation Deltas",
        "",
    ]

    for model_name, metrics in evaluation["models"].items():
        lines.append(
            f"- `{model_name}` answer support: `{metrics['baseline_answer_support_rate']:.3f}` -> `{metrics['candidate_answer_support_rate']:.3f}` (`{metrics['answer_support_rate_delta']:+.3f}`)"
        )

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            summary["recommendation"],
            "",
        ]
    )
    return "\n".join(lines)


def _load_run_metrics(run_dir: Path) -> dict[str, Any]:
    validation = _read_json(run_dir / "validation_summary.json")
    dataset = _read_json(run_dir / "dataset_profile.json")
    operator = _read_json(run_dir / "operator_summary.json")
    evaluation = _read_json(run_dir / "evaluation_summary.json")
    manifest = _read_json(run_dir / "run_manifest.json")

    return {
        "run_name": run_dir.name,
        "validation": validation,
        "dataset": dataset,
        "operator": operator,
        "evaluation": evaluation,
        "manifest": manifest,
    }


def _summary(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    baseline_status = baseline["validation"]["status_counts"]
    candidate_status = candidate["validation"]["status_counts"]
    baseline_total = sum(baseline_status.values())
    candidate_total = sum(candidate_status.values())
    baseline_pass = (
        baseline_status.get("accepted", 0) + baseline_status.get("soft_fail", 0)
    ) / max(1, baseline_total)
    candidate_pass = (
        candidate_status.get("accepted", 0) + candidate_status.get("soft_fail", 0)
    ) / max(1, candidate_total)

    dataset_size_delta = candidate["dataset"]["total_questions"] - baseline["dataset"]["total_questions"]
    validation_delta = round(candidate_pass - baseline_pass, 3)
    recommendation = (
        "Candidate run is an improvement and should be treated as the new benchmark baseline."
        if validation_delta > 0 and dataset_size_delta >= 0
        else "Candidate run shows mixed results and should be reviewed before replacing the baseline."
    )

    return {
        "baseline_validation_pass_rate": round(baseline_pass, 3),
        "candidate_validation_pass_rate": round(candidate_pass, 3),
        "validation_pass_rate_delta": validation_delta,
        "baseline_dataset_size": baseline["dataset"]["total_questions"],
        "candidate_dataset_size": candidate["dataset"]["total_questions"],
        "dataset_size_delta": dataset_size_delta,
        "baseline_hard_fail_count": baseline_status.get("hard_fail", 0),
        "candidate_hard_fail_count": candidate_status.get("hard_fail", 0),
        "hard_fail_delta": candidate_status.get("hard_fail", 0) - baseline_status.get("hard_fail", 0),
        "recommendation": recommendation,
    }


def _quality_deltas(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    baseline_validation = baseline["validation"]
    candidate_validation = candidate["validation"]

    return {
        "multi_chunk_ratio_delta": round(
            candidate["dataset"]["multi_chunk_ratio"] - baseline["dataset"]["multi_chunk_ratio"], 3
        ),
        "avg_citations_per_question_delta": round(
            candidate["dataset"]["avg_citations_per_question"] - baseline["dataset"]["avg_citations_per_question"], 3
        ),
        "avg_confidence_delta": round(
            candidate_validation["avg_confidence"] - baseline_validation["avg_confidence"], 3
        ),
        "recovered_grounding_rate_delta": round(
            candidate_validation.get("recovered_grounding_rate", 0.0)
            - baseline_validation.get("recovered_grounding_rate", 0.0),
            3,
        ),
        "duplicate_hard_fail_delta": (
            candidate_validation.get("hard_fail_reason_counts", {}).get("duplicate_question", 0)
            - baseline_validation.get("hard_fail_reason_counts", {}).get("duplicate_question", 0)
        ),
        "low_information_soft_fail_delta": (
            candidate_validation.get("soft_fail_reason_counts", {}).get("low_information_value", 0)
            - baseline_validation.get("soft_fail_reason_counts", {}).get("low_information_value", 0)
        ),
    }


def _preprocessing_deltas(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    baseline_prep = baseline["operator"].get("preprocessing_summary", {})
    candidate_prep = candidate["operator"].get("preprocessing_summary", {})
    return {
        "raw_chunk_count_delta": candidate_prep.get("raw_chunk_count", 0) - baseline_prep.get("raw_chunk_count", 0),
        "accepted_chunk_count_delta": candidate_prep.get("accepted_chunk_count", 0)
        - baseline_prep.get("accepted_chunk_count", 0),
        "filtered_chunk_count_delta": candidate_prep.get("filtered_chunk_count", 0)
        - baseline_prep.get("filtered_chunk_count", 0),
        "baseline_filter_reason_counts": baseline_prep.get("filtered_reason_counts", {}),
        "candidate_filter_reason_counts": candidate_prep.get("filtered_reason_counts", {}),
    }


def _generation_deltas(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    baseline_generation = baseline["operator"].get("generation_summary", {})
    candidate_generation = candidate["operator"].get("generation_summary", {})
    return {
        "generated_questions_delta": candidate_generation.get("generated_questions", 0)
        - baseline_generation.get("generated_questions", 0),
        "skipped_duplicate_signatures_delta": candidate_generation.get("skipped_duplicate_signatures", 0)
        - baseline_generation.get("skipped_duplicate_signatures", 0),
        "skipped_low_quality_topics_delta": candidate_generation.get("skipped_low_quality_topics", 0)
        - baseline_generation.get("skipped_low_quality_topics", 0),
        "unique_topic_count_delta": candidate_generation.get("unique_topic_count", 0)
        - baseline_generation.get("unique_topic_count", 0),
    }


def _evaluation_deltas(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    model_names = set(baseline["evaluation"]["models"]) | set(candidate["evaluation"]["models"])
    models: dict[str, dict[str, Any]] = {}
    for model_name in model_names:
        baseline_metrics = baseline["evaluation"]["models"].get(model_name, {})
        candidate_metrics = candidate["evaluation"]["models"].get(model_name, {})
        models[model_name] = {
            "baseline_answer_support_rate": float(baseline_metrics.get("answer_support_rate", 0.0)),
            "candidate_answer_support_rate": float(candidate_metrics.get("answer_support_rate", 0.0)),
            "answer_support_rate_delta": round(
                float(candidate_metrics.get("answer_support_rate", 0.0))
                - float(baseline_metrics.get("answer_support_rate", 0.0)),
                3,
            ),
        }
    return {"models": models}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
