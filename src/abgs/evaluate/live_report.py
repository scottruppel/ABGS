"""Shared live-eval + benchmark report workflow (used by `abgs-run live-eval`)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from abgs.contracts import BenchmarkRecord, DatasetProfile, DifficultyLevel, EvaluationRecord, to_primitive
from abgs.env_utils import load_local_env
from abgs.evaluate.anthropic_provider import AnthropicEvaluationError, answer_question as answer_anthropic
from abgs.evaluate.critic import apply_critic_to_evaluations
from abgs.evaluate.gemini_provider import GeminiEvaluationError, answer_question as answer_gemini
from abgs.evaluate.pipeline import LIVE_EVAL_FAILURE_SENTINEL, _summary, evaluate
from abgs.io_utils import write_json, write_jsonl
from abgs.reporting.benchmark_report import write_benchmark_report
from abgs.reporting.evaluation_protocol import build_evaluation_protocol

Strategy = Literal["full", "anthropic_only"]

DEFAULT_V4_RUN = Path("artifacts/runs/AI_Policy_gemini_pilot_v4")
DEFAULT_V4_OUTPUT = Path("artifacts/reports/ai_policy_v4_with_claude")


def load_benchmark_records(validated_path: Path) -> list[BenchmarkRecord]:
    rows: list[BenchmarkRecord] = []
    for line in validated_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        rows.append(
            BenchmarkRecord(
                id=data["id"],
                question=data["question"],
                answer=data["answer"],
                acceptable_answers=data["acceptable_answers"],
                sources=data["sources"],
                difficulty=DifficultyLevel(data["difficulty"]),
                category=data["category"],
                metadata=data["metadata"],
            )
        )
    return rows


def parse_evaluation_record_line(line: str) -> EvaluationRecord:
    d = json.loads(line)
    return EvaluationRecord(
        benchmark_id=d["benchmark_id"],
        model_name=d["model_name"],
        response=d["response"],
        exact_match=d["exact_match"],
        support_rate=d["support_rate"],
        refused=d["refused"],
        refusal_type=d.get("refusal_type"),
        scoring_trace=d.get("scoring_trace") or {},
    )


def _maybe_apply_critic(
    records: list[BenchmarkRecord], merged: list[EvaluationRecord], repo_root: Path
) -> list[EvaluationRecord]:
    load_local_env(repo_root, override=True)
    raw = os.getenv("ABGS_CRITIC_MODEL", "").strip()
    if not raw or raw.lower() in ("0", "false", "off", "no"):
        return merged
    return apply_critic_to_evaluations(records, merged, raw)


def gemini_model_name(repo_root: Path) -> str:
    load_local_env(repo_root, override=True)
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"


def anthropic_model_name(repo_root: Path) -> str:
    load_local_env(repo_root, override=True)
    return os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514").strip() or "claude-sonnet-4-20250514"


def merge_full_strategy(
    run_dir: Path,
    live_gemini: list[EvaluationRecord],
    live_anthropic: list[EvaluationRecord],
) -> list[EvaluationRecord]:
    base_path = run_dir / "evaluation_records.jsonl"
    if not base_path.is_file():
        raise FileNotFoundError(f"Missing {base_path}; run the pipeline first.")
    by_model: dict[str, list[EvaluationRecord]] = {}
    for line in base_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = parse_evaluation_record_line(line)
        by_model.setdefault(e.model_name, []).append(e)
    for name in ("oracle", "extractive_baseline", "cautious_refuser"):
        if name not in by_model:
            raise KeyError(f"Expected model {name!r} in baseline evaluation_records.jsonl")
    n = len(live_gemini)
    for name in ("oracle", "extractive_baseline", "cautious_refuser"):
        if len(by_model[name]) != n:
            raise ValueError(
                f"Baseline {name} has {len(by_model[name])} rows; live eval has {n}. "
                "Run directory may not match validated_qa."
            )
    return (
        live_gemini
        + live_anthropic
        + by_model["oracle"]
        + by_model["extractive_baseline"]
        + by_model["cautious_refuser"]
    )


def merge_anthropic_only_strategy(run_dir: Path, live_anthropic: list[EvaluationRecord]) -> list[EvaluationRecord]:
    """Reuse Gemini + baselines from disk; replace only Anthropic rows (AI Policy v4 workflow)."""
    base_path = run_dir / "evaluation_records.jsonl"
    if not base_path.is_file():
        raise FileNotFoundError(f"Missing {base_path}; run the pipeline first.")
    by_model: dict[str, list[EvaluationRecord]] = {}
    for line in base_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = parse_evaluation_record_line(line)
        by_model.setdefault(e.model_name, []).append(e)
    gemini_keys = [k for k in by_model if k.startswith("gemini:")]
    if len(gemini_keys) != 1:
        raise ValueError(f"Expected exactly one gemini:* model in baseline; got {gemini_keys!r}")
    gk = gemini_keys[0]
    for name in ("extractive_baseline", "cautious_refuser"):
        if name not in by_model:
            raise KeyError(f"Expected model {name!r} in baseline evaluation_records.jsonl")
    n = len(live_anthropic)
    if len(by_model[gk]) != n or len(by_model["extractive_baseline"]) != n:
        raise ValueError("Baseline row counts do not match live anthropic eval length.")
    return (
        by_model[gk]
        + live_anthropic
        + by_model["extractive_baseline"]
        + by_model["cautious_refuser"]
    )


def write_live_eval_meta(
    output_dir: Path,
    *,
    strategy: str,
    item_count: int,
    resolved_models: dict[str, str],
    live_model_calls: int,
) -> None:
    payload: dict[str, Any] = {
        "strategy": strategy,
        "item_count": item_count,
        "estimated_live_api_calls": live_model_calls,
        "resolved_models": resolved_models,
        "estimated_cost_usd_note": (
            "Not computed: providers do not return usage in the current HTTP clients. "
            "Use provider billing or add token accounting later."
        ),
    }
    write_json(output_dir / "live_eval_meta.json", payload)


def probe_apis(validated_path: Path, repo_root: Path) -> bool:
    load_local_env(repo_root, override=True)
    records = load_benchmark_records(validated_path)
    if not records:
        print("PROBE_FAIL no records", flush=True)
        return False
    r0 = records[0]
    try:
        g = answer_gemini(gemini_model_name(repo_root), r0)
        print("PROBE_OK gemini", str(g.get("answer", ""))[:80], flush=True)
    except GeminiEvaluationError as e:
        print("PROBE_FAIL gemini", e, flush=True)
        return False
    try:
        a = answer_anthropic(None, r0)
        print("PROBE_OK anthropic", str(a.get("answer", ""))[:80], flush=True)
    except AnthropicEvaluationError as e:
        print("PROBE_FAIL anthropic", e, flush=True)
        return False
    return True


def probe_anthropic_only(validated_path: Path, repo_root: Path) -> bool:
    """For anthropic_only strategy: Gemini rows are reused from disk; only Anthropic must work."""
    load_local_env(repo_root, override=True)
    records = load_benchmark_records(validated_path)
    if not records:
        print("PROBE_FAIL no records", flush=True)
        return False
    r0 = records[0]
    try:
        a = answer_anthropic(None, r0)
        print("PROBE_OK anthropic", str(a.get("answer", ""))[:80], flush=True)
    except AnthropicEvaluationError as e:
        print("PROBE_FAIL anthropic", e, flush=True)
        return False
    return True


def run_live_eval_and_report(
    run_dir: Path,
    output_dir: Path,
    strategy: Strategy,
    *,
    repo_root: Path,
    skip_probe: bool = False,
) -> dict[str, Any]:
    """Run live evaluation, merge baselines, write evaluation artifacts + benchmark report + live_eval_meta."""
    if not skip_probe:
        if strategy == "full":
            if not probe_apis(run_dir / "validated_qa.jsonl", repo_root):
                raise RuntimeError("API probe failed; fix keys and retry.")
        elif not probe_anthropic_only(run_dir / "validated_qa.jsonl", repo_root):
            raise RuntimeError("Anthropic API probe failed; fix keys and retry.")

    validated = run_dir / "validated_qa.jsonl"
    records = load_benchmark_records(validated)
    gemini_tag = f"gemini:{gemini_model_name(repo_root)}"
    resolved = {
        "gemini": gemini_model_name(repo_root),
        "anthropic": anthropic_model_name(repo_root),
    }

    if strategy == "full":
        print(f"Live eval: {len(records)} items × 2 models ({gemini_tag}, anthropic)…", flush=True)
        live_evals, _ = evaluate(records, [gemini_tag, "anthropic"])
        by_live: dict[str, list[EvaluationRecord]] = {}
        for e in live_evals:
            by_live.setdefault(e.model_name, []).append(e)
        merged = merge_full_strategy(run_dir, by_live[gemini_tag], by_live["anthropic"])
        live_calls = 2 * len(records)
    else:
        print(f"Live eval: {len(records)} items × anthropic only (strategy anthropic_only)…", flush=True)
        anthropic_evals, _ = evaluate(records, ["anthropic"])
        merged = merge_anthropic_only_strategy(run_dir, anthropic_evals)
        live_calls = len(records)

    merged = _maybe_apply_critic(records, merged, repo_root)
    summary = _summary(records, merged)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "evaluation_records.jsonl", merged)
    write_json(output_dir / "evaluation_summary.json", summary)

    write_live_eval_meta(
        output_dir,
        strategy=strategy,
        item_count=len(records),
        resolved_models=resolved,
        live_model_calls=live_calls,
    )

    dataset_profile = DatasetProfile(
        **json.loads((run_dir / "dataset_profile.json").read_text(encoding="utf-8"))
    )
    validation_summary = json.loads((run_dir / "validation_summary.json").read_text(encoding="utf-8"))
    load_local_env(repo_root, override=True)
    evaluation_protocol = build_evaluation_protocol(
        validated_qa_path=validated,
        run_manifest_path=run_dir / "run_manifest.json",
        resolved_models=resolved,
    )
    write_benchmark_report(
        output_dir=output_dir,
        records=records,
        dataset_profile=dataset_profile,
        validation_summary=validation_summary,
        evaluation_records=merged,
        evaluation_summary=summary.models,
        evaluation_protocol=evaluation_protocol,
        resolved_models=evaluation_protocol["resolved_models"],
    )
    print("Wrote", output_dir, flush=True)
    out: dict[str, Any] = {"output_dir": str(output_dir), "summary": summary}
    for key in (gemini_tag, "anthropic") if strategy == "full" else ("anthropic",):
        if key in summary.models:
            print(key, json.dumps(to_primitive(summary.models[key]["overall"]), indent=2), flush=True)
    return out


def retry_failed_live_eval(
    run_dir: Path,
    output_dir: Path,
    *,
    repo_root: Path,
    strategy: Strategy = "full",
) -> None:
    load_local_env(repo_root, override=True)
    validated = run_dir / "validated_qa.jsonl"
    records_list = load_benchmark_records(validated)
    by_id = {r.id: r for r in records_list}
    gemini_tag = f"gemini:{gemini_model_name(repo_root)}"
    path = output_dir / "evaluation_records.jsonl"
    if not path.is_file():
        raise FileNotFoundError(path)
    merged = [parse_evaluation_record_line(line) for line in path.read_text(encoding="utf-8").splitlines()]
    changed = False
    for i, e in enumerate(merged):
        if e.response != LIVE_EVAL_FAILURE_SENTINEL:
            continue
        if strategy == "full":
            if e.model_name not in (gemini_tag, "anthropic"):
                continue
        elif e.model_name != "anthropic":
            continue
        rec = by_id[e.benchmark_id]
        new_ev, _ = evaluate([rec], [e.model_name])
        merged[i] = new_ev[0]
        changed = True
        print("retried", e.benchmark_id, e.model_name, "->", merged[i].response[:60])
    if not changed:
        print("no failed live-eval rows to retry")
        return
    merged = _maybe_apply_critic(records_list, merged, repo_root)
    summary = _summary(records_list, merged)
    write_jsonl(path, merged)
    write_json(output_dir / "evaluation_summary.json", summary)
    resolved = {
        "gemini": gemini_model_name(repo_root),
        "anthropic": anthropic_model_name(repo_root),
    }
    write_live_eval_meta(
        output_dir,
        strategy=strategy,
        item_count=len(records_list),
        resolved_models=resolved,
        live_model_calls=2 * len(records_list) if strategy == "full" else len(records_list),
    )
    dataset_profile = DatasetProfile(
        **json.loads((run_dir / "dataset_profile.json").read_text(encoding="utf-8"))
    )
    validation_summary = json.loads((run_dir / "validation_summary.json").read_text(encoding="utf-8"))
    evaluation_protocol = build_evaluation_protocol(
        validated_qa_path=validated,
        run_manifest_path=run_dir / "run_manifest.json",
        resolved_models=resolved,
    )
    write_benchmark_report(
        output_dir=output_dir,
        records=records_list,
        dataset_profile=dataset_profile,
        validation_summary=validation_summary,
        evaluation_records=merged,
        evaluation_summary=summary.models,
        evaluation_protocol=evaluation_protocol,
        resolved_models=evaluation_protocol["resolved_models"],
    )
    print("Wrote", output_dir)
