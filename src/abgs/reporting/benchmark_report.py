from __future__ import annotations

from pathlib import Path
from typing import Any

from abgs.contracts import BenchmarkRecord, EvaluationRecord
from abgs.io_utils import ensure_directory, write_json
from abgs.reporting.model_profiles import build_model_profiles, build_use_case_guidance


def write_benchmark_report(
    output_dir: str | Path,
    records: list[BenchmarkRecord],
    dataset_profile: object,
    validation_summary: dict[str, object],
    evaluation_records: list[EvaluationRecord],
    evaluation_summary: dict[str, dict[str, object]],
    *,
    evaluation_protocol: dict[str, object] | None = None,
    resolved_models: dict[str, str] | None = None,
) -> dict[str, object]:
    report = build_benchmark_report(
        records=records,
        dataset_profile=dataset_profile,
        validation_summary=validation_summary,
        evaluation_records=evaluation_records,
        evaluation_summary=evaluation_summary,
        evaluation_protocol=evaluation_protocol,
        resolved_models=resolved_models,
    )
    output_root = ensure_directory(output_dir)
    write_json(output_root / "benchmark_report.json", report)
    (output_root / "benchmark_report.md").write_text(render_benchmark_report_markdown(report), encoding="utf-8")
    if evaluation_protocol:
        write_json(output_root / "evaluation_protocol.json", evaluation_protocol)
    return report


def build_benchmark_report(
    *,
    records: list[BenchmarkRecord],
    dataset_profile: object,
    validation_summary: dict[str, object],
    evaluation_records: list[EvaluationRecord],
    evaluation_summary: dict[str, dict[str, object]],
    evaluation_protocol: dict[str, object] | None = None,
    resolved_models: dict[str, str] | None = None,
) -> dict[str, object]:
    model_comparison = {
        model_name: {
            "exact_match_rate": metrics["exact_match_rate"],
            "answer_support_rate": metrics["answer_support_rate"],
            "citation_support_rate": metrics.get("citation_support_rate", 0.0),
            "answer_alignment_rate": metrics.get("answer_alignment_rate", 0.0),
            "refusal_rate": metrics["refusal_rate"],
            "appropriate_refusal_rate": metrics["appropriate_refusal_rate"],
            "inappropriate_refusal_rate": metrics["inappropriate_refusal_rate"],
            "evaluation_failure_rate": metrics.get("overall", {}).get("evaluation_failure_rate", 0.0),
        }
        for model_name, metrics in evaluation_summary.items()
    }
    demo_grade_slice = _demo_grade_slice(records, evaluation_records)
    profiles = build_model_profiles(evaluation_summary, resolved_models=resolved_models)
    use_case_guidance = build_use_case_guidance(evaluation_summary, resolved_models=resolved_models)
    vpr = _validation_pass_rate(validation_summary)
    rgr = float(validation_summary.get("recovered_grounding_rate", 0.0))
    payload: dict[str, object] = {
        "corpus_health": _corpus_health_payload(dataset_profile, vpr, rgr),
        "dataset_overview": {
            "size": dataset_profile.total_questions,
            "difficulty_distribution": dataset_profile.difficulty_distribution,
            "question_type_distribution": dataset_profile.question_type_distribution,
            "multi_chunk_ratio": dataset_profile.multi_chunk_ratio,
            "validation_pass_rate": vpr,
            "recovered_grounding_rate": rgr,
        },
        "executive_summary": _executive_summary(model_comparison, demo_grade_slice),
        "model_comparison": model_comparison,
        "breakdown_by_difficulty": {
            model_name: metrics.get("by_difficulty", {})
            for model_name, metrics in evaluation_summary.items()
        },
        "breakdown_by_question_type": {
            model_name: metrics.get("by_question_type", {})
            for model_name, metrics in evaluation_summary.items()
        },
        "multi_chunk_performance": {
            model_name: metrics.get("by_chunk_mode", {})
            for model_name, metrics in evaluation_summary.items()
        },
        "demo_grade_slice": demo_grade_slice,
        "example_failures": _example_failures(records, evaluation_records),
        "model_behavior_profiles": profiles,
        "use_case_guidance": use_case_guidance,
    }
    if evaluation_protocol:
        payload["evaluation_protocol"] = evaluation_protocol
    return payload


def render_benchmark_report_markdown(report: dict[str, object]) -> str:
    overview = report["dataset_overview"]
    executive = report["executive_summary"]
    comparison = report["model_comparison"]
    difficulty = report["breakdown_by_difficulty"]
    question_type = report["breakdown_by_question_type"]
    chunk_mode = report["multi_chunk_performance"]
    demo_slice = report["demo_grade_slice"]
    failures = report["example_failures"]
    profiles = report.get("model_behavior_profiles") or {}
    use_cases = report.get("use_case_guidance") or []
    protocol = report.get("evaluation_protocol")

    corpus_health = report.get("corpus_health") or {}
    lines = [
        "# Benchmark Report",
        "",
        "## Executive Summary",
        "",
        f"- Best overall hybrid support: `{executive['best_overall_support_model']}` at `{executive['best_overall_support_rate']:.3f}`",
        f"- Best demo-slice hybrid support: `{executive['best_demo_slice_model']}` at `{executive['best_demo_slice_support_rate']:.3f}`",
        f"- Strongest cautious behavior: `{executive['best_refusal_model']}` at `{executive['best_refusal_rate']:.3f}` appropriate refusal",
        executive["headline"],
        "",
        "## Benchmark difficulty context",
        "",
        *_corpus_health_markdown(corpus_health),
        "## Model Behavior Profile",
        "",
        *_render_profile_markdown(profiles),
        "## Use Case Guidance",
        "",
        *(use_cases if use_cases else ["- Add at least two live models (e.g. Gemini + Anthropic) to generate conditional guidance."]),
        "",
    ]
    if protocol:
        lines.extend(
            [
                "## Evaluation Protocol (reproducibility)",
                "",
                *_render_protocol_markdown(protocol),
                "",
            ]
        )
    lines.extend(
        [
            "## Beyond accuracy: what this benchmark measures",
            "",
            *_epistemology_markdown(),
            "",
        ]
    )
    lines.extend(
        [
        "## Dataset Overview",
        "",
        f"- Size: `{overview['size']}`",
        f"- Validation pass rate: `{overview['validation_pass_rate']:.3f}`",
        f"- Recovered grounding rate: `{overview['recovered_grounding_rate']:.3f}`",
        f"- Multi-chunk ratio: `{overview['multi_chunk_ratio']:.3f}`",
        f"- Difficulty distribution: `{overview['difficulty_distribution']}`",
        f"- Question type distribution: `{overview['question_type_distribution']}`",
        "",
        ]
    )
    lines.extend(
        [
        "## Model Comparison Table",
        "",
        _comparison_table(comparison),
        "",
        "## Breakdown by Difficulty",
        "",
        _slice_table(difficulty, ("L1", "L2", "L3")),
        "",
        "## Breakdown by Question Type",
        "",
        _slice_table(question_type, ("factual", "procedural", "analytical", "edge_case")),
        "",
        "## Multi-Chunk Performance",
        "",
        _slice_table(chunk_mode, ("single_chunk", "multi_chunk")),
        "",
        "## Demo-Grade Slice",
        "",
        "This slice keeps only `L2` and `L3` questions that also require `multi_chunk` synthesis.",
        "",
        _comparison_table(demo_slice),
        "",
        "## Example Failures",
        "",
        ]
    )

    for model_name, items in failures.items():
        lines.append(f"### {model_name}")
        lines.append("")
        if not items:
            lines.append("- No representative failures selected.")
            lines.append("")
            continue
        for item in items:
            lines.append(f"- Question: {item['question']}")
            lines.append(f"- Benchmark answer: {item['benchmark_answer']}")
            lines.append(f"- Model output: {item['model_output']}")
            lines.append(
                f"- Support/refusal: support `{item['support_rate']:.3f}`, refused `{item['refused']}`, refusal_type `{item['refusal_type']}`"
            )
            lines.append(
                f"- Scoring trace: citation `{item['citation_support_rate']:.3f}`, alignment `{item['answer_alignment_score']:.3f}`, mode `{item['scoring_mode']}`"
            )
            lines.append(f"- Difficulty/failure modes: `{item['difficulty']}`, `{item['failure_modes']}`")
            lines.append("")

    return "\n".join(lines)


def _corpus_health_payload(
    dataset_profile: object,
    validation_pass_rate: float,
    recovered_grounding_rate: float,
) -> dict[str, object]:
    n = int(dataset_profile.total_questions)
    mcr = float(dataset_profile.multi_chunk_ratio)
    if validation_pass_rate < 0.6:
        interpretation = (
            "Validation pass rate is below the typical operator band (0.60–0.85); "
            "scalar metrics are likely domain- or extraction-stressed."
        )
    elif validation_pass_rate < 0.75:
        interpretation = "Moderate validation pass rate; compare absolute scores across corpora cautiously."
    else:
        interpretation = (
            "Validation pass rate is in a typical range for well-behaved text; "
            "cross-run headline comparisons are more comparable."
        )
    return {
        "accepted_benchmark_size": n,
        "validation_pass_rate": validation_pass_rate,
        "recovered_grounding_rate": recovered_grounding_rate,
        "multi_chunk_ratio": mcr,
        "interpretation": interpretation,
    }


def _corpus_health_markdown(corpus_health: dict[str, object]) -> list[str]:
    if not corpus_health:
        return ["- (no corpus health payload)", ""]
    return [
        f"- Accepted benchmark size: `{corpus_health.get('accepted_benchmark_size', 'n/a')}`",
        f"- Validation pass rate: `{corpus_health.get('validation_pass_rate', 0.0):.3f}`",
        f"- Recovered grounding rate: `{corpus_health.get('recovered_grounding_rate', 0.0):.3f}`",
        f"- Multi-chunk ratio: `{corpus_health.get('multi_chunk_ratio', 0.0):.3f}`",
        f"- Interpretation: {corpus_health.get('interpretation', '')}",
        "",
    ]


def _validation_pass_rate(validation_summary: dict[str, object]) -> float:
    status_counts = validation_summary.get("status_counts", {})
    total = sum(status_counts.values())
    passed = status_counts.get("accepted", 0) + status_counts.get("soft_fail", 0)
    return round(passed / max(1, total), 3)


def _comparison_table(comparison: dict[str, dict[str, float]]) -> str:
    if not comparison:
        return "No model data available."
    lines = [
        "| Metric | " + " | ".join(comparison.keys()) + " |",
        "| --- | " + " | ".join("---" for _ in comparison) + " |",
        "| Exact Match | " + " | ".join(f"{metrics['exact_match_rate']:.3f}" for metrics in comparison.values()) + " |",
        "| Answer Support Rate | "
        + " | ".join(f"{metrics['answer_support_rate']:.3f}" for metrics in comparison.values())
        + " |",
        "| Citation Support Rate | "
        + " | ".join(f"{metrics.get('citation_support_rate', 0.0):.3f}" for metrics in comparison.values())
        + " |",
        "| Answer Alignment Rate | "
        + " | ".join(f"{metrics.get('answer_alignment_rate', 0.0):.3f}" for metrics in comparison.values())
        + " |",
        "| Refusal Rate | " + " | ".join(f"{metrics['refusal_rate']:.3f}" for metrics in comparison.values()) + " |",
        "| Appropriate Refusal | "
        + " | ".join(f"{metrics['appropriate_refusal_rate']:.3f}" for metrics in comparison.values())
        + " |",
        "| Evaluation Failure (API/transport) | "
        + " | ".join(f"{metrics.get('evaluation_failure_rate', 0.0):.3f}" for metrics in comparison.values())
        + " |",
    ]
    return "\n".join(lines)


def _slice_table(slice_payload: dict[str, dict[str, Any]], labels: tuple[str, ...]) -> str:
    models = list(slice_payload.keys())
    if not models:
        return "No slice data available."
    lines = [
        "| Slice | " + " | ".join(models) + " |",
        "| --- | " + " | ".join("---" for _ in models) + " |",
    ]
    for label in labels:
        values = []
        for model_name in models:
            metrics = slice_payload[model_name].get(label, {})
            exact = metrics.get("exact_match_rate", 0.0)
            support = metrics.get("answer_support_rate", 0.0)
            values.append(f"{exact:.3f}/{support:.3f}")
        lines.append("| " + label + " | " + " | ".join(values) + " |")
    return "\n".join(lines)


def _example_failures(records: list[BenchmarkRecord], evaluations: list[EvaluationRecord], limit: int = 5) -> dict[str, list[dict[str, object]]]:
    benchmark_index = {record.id: record for record in records}
    failures: dict[str, list[dict[str, object]]] = {}
    ranked = sorted(
        evaluations,
        key=lambda item: (
            0 if item.refused else 1,
            item.support_rate,
            float(item.scoring_trace.get("answer_alignment_score", 0.0)),
        ),
    )
    for evaluation in ranked:
        benchmark = benchmark_index[evaluation.benchmark_id]
        if not evaluation.refused and evaluation.support_rate >= 0.95:
            continue
        failures.setdefault(evaluation.model_name, [])
        if len(failures[evaluation.model_name]) >= limit:
            continue
        failures[evaluation.model_name].append(
            {
                "benchmark_id": evaluation.benchmark_id,
                "question": benchmark.question,
                "benchmark_answer": benchmark.answer,
                "model_output": evaluation.response,
                "support_rate": evaluation.support_rate,
                "refused": evaluation.refused,
                "refusal_type": evaluation.refusal_type,
                "citation_support_rate": evaluation.scoring_trace.get("citation_support_rate", 0.0),
                "answer_alignment_score": evaluation.scoring_trace.get("answer_alignment_score", 0.0),
                "scoring_mode": evaluation.scoring_trace.get("mode", "unknown"),
                "difficulty": benchmark.difficulty.value,
                "question_type": benchmark.metadata["generation_trace"]["question_type"],
                "failure_modes": benchmark.metadata["failure_modes"],
            }
        )
    return failures


def _executive_summary(
    model_comparison: dict[str, dict[str, float]],
    demo_grade_slice: dict[str, dict[str, float]],
) -> dict[str, object]:
    if not model_comparison:
        return {
            "best_overall_support_model": "n/a",
            "best_overall_support_rate": 0.0,
            "best_demo_slice_model": "n/a",
            "best_demo_slice_support_rate": 0.0,
            "best_refusal_model": "n/a",
            "best_refusal_rate": 0.0,
            "headline": "- No model comparison data available yet.",
        }
    best_overall_model, best_overall_metrics = max(
        model_comparison.items(),
        key=lambda item: item[1]["answer_support_rate"],
    )
    if demo_grade_slice:
        best_demo_model, best_demo_metrics = max(
            demo_grade_slice.items(),
            key=lambda item: item[1]["answer_support_rate"],
        )
    else:
        best_demo_model, best_demo_metrics = "n/a", {"answer_support_rate": 0.0}
    best_refusal_model, best_refusal_metrics = max(
        model_comparison.items(),
        key=lambda item: item[1]["appropriate_refusal_rate"],
    )
    headline = (
        f"- The benchmark separates grounded extractive behavior from abstention-heavy behavior and from abstractive answering."
    )
    return {
        "best_overall_support_model": best_overall_model,
        "best_overall_support_rate": best_overall_metrics["answer_support_rate"],
        "best_demo_slice_model": best_demo_model,
        "best_demo_slice_support_rate": best_demo_metrics["answer_support_rate"],
        "best_refusal_model": best_refusal_model,
        "best_refusal_rate": best_refusal_metrics["appropriate_refusal_rate"],
        "headline": headline,
    }


def _demo_grade_slice(records: list[BenchmarkRecord], evaluations: list[EvaluationRecord]) -> dict[str, dict[str, float]]:
    benchmark_index = {record.id: record for record in records}
    filtered: dict[str, list[EvaluationRecord]] = {}
    for evaluation in evaluations:
        benchmark = benchmark_index[evaluation.benchmark_id]
        if benchmark.difficulty.value not in {"L2", "L3"}:
            continue
        if not benchmark.metadata["quality_signals"].get("multi_chunk_required", False):
            continue
        filtered.setdefault(evaluation.model_name, []).append(evaluation)

    return {
        model_name: _evaluation_bucket(items)
        for model_name, items in filtered.items()
    }


def _evaluation_bucket(items: list[EvaluationRecord]) -> dict[str, float]:
    total = len(items)
    if total == 0:
        return {
            "exact_match_rate": 0.0,
            "answer_support_rate": 0.0,
            "citation_support_rate": 0.0,
            "answer_alignment_rate": 0.0,
            "refusal_rate": 0.0,
            "appropriate_refusal_rate": 0.0,
            "inappropriate_refusal_rate": 0.0,
            "evaluation_failure_rate": 0.0,
        }
    return {
        "exact_match_rate": round(sum(1 for item in items if item.exact_match) / total, 3),
        "answer_support_rate": round(sum(item.support_rate for item in items) / total, 3),
        "citation_support_rate": round(
            sum(float(item.scoring_trace.get("citation_support_rate", 0.0)) for item in items) / total,
            3,
        ),
        "answer_alignment_rate": round(
            sum(float(item.scoring_trace.get("answer_alignment_score", 0.0)) for item in items) / total,
            3,
        ),
        "refusal_rate": round(sum(1 for item in items if item.refused) / total, 3),
        "appropriate_refusal_rate": round(sum(1 for item in items if item.refusal_type == "appropriate_refusal") / total, 3),
        "inappropriate_refusal_rate": round(sum(1 for item in items if item.refusal_type == "inappropriate_refusal") / total, 3),
        "evaluation_failure_rate": round(sum(1 for item in items if item.refusal_type == "evaluation_failure") / total, 3),
    }


def _render_profile_markdown(profiles: dict[str, object]) -> list[str]:
    if not profiles:
        return [
            "- No comparative profile generated (add live API models such as `gemini:...` and `anthropic`).",
            "",
        ]
    out: list[str] = []
    for _key, p in profiles.items():
        disp = str(p.get("display_name", _key))
        out.append(f"### {disp}")
        out.append("")
        strengths = p.get("strengths") or []
        weaknesses = p.get("weaknesses") or []
        out.append("**Strengths:**")
        if strengths:
            for s in strengths:
                out.append(f"- {s}")
        else:
            out.append("- (none above relative threshold vs peers)")
        out.append("")
        out.append("**Weaknesses:**")
        if weaknesses:
            for w in weaknesses:
                out.append(f"- {w}")
        else:
            out.append("- (none above relative threshold vs peers)")
        out.append("")
        out.append(f"**Behavioral tendency:** {p.get('behavioral_tendency', 'n/a')}")
        out.append("")
    return out


def _render_protocol_markdown(protocol: dict[str, object]) -> list[str]:
    lines = [
        f"- **ABGS version:** `{protocol.get('abgs_version')}`",
        f"- **Evaluation protocol ID:** `{protocol.get('evaluation_protocol_id')}` (bump when hybrid scoring or refusal taxonomy changes).",
        f"- **validated_qa SHA-256:** `{protocol.get('validated_qa_sha256')}`",
        f"- **run_manifest SHA-256:** `{protocol.get('run_manifest_sha256')}`",
        f"- **Run id:** `{protocol.get('run_id')}`",
        f"- **Config hash (generation):** `{protocol.get('config_hash')}`",
    ]
    if protocol.get("resolved_models"):
        lines.append("- **Resolved models (no secrets):**")
        for k, v in protocol["resolved_models"].items():
            lines.append(f"  - `{k}`: `{v}`")
    return lines


def _epistemology_markdown() -> list[str]:
    return [
        "ABGS reports measure **answer policy** and **epistemic stance**, not only scalar accuracy:",
        "",
        "- **When models answer vs refuse** — refusal rate, appropriate vs inappropriate refusal given benchmark expectations; "
        "**evaluation_failure** rows count API/transport failures separately from model abstention.",
        "- **How answers relate to sources** — citation-style overlap (quote presence) and hybrid alignment with reference answers.",
        "- **Why refusals happen** — inspect `refusal_type` and example failures; models differ in how often they abstain on answerable items.",
        "",
        "Together, this supports **model epistemology** comparisons: conservative grounding vs assertive completion, "
        "under the same items and scoring rubric.",
    ]
