"""Compare headline metrics across two report directories (evaluation_summary.json)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


METRIC_KEYS = (
    "answer_support_rate",
    "citation_support_rate",
    "answer_alignment_rate",
    "refusal_rate",
    "appropriate_refusal_rate",
    "inappropriate_refusal_rate",
    "evaluation_failure_rate",
)


def _load_models(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads((path / "evaluation_summary.json").read_text(encoding="utf-8"))
    if "models" in data:
        return data["models"]
    return data


def compare_report_summaries(baseline_dir: Path, candidate_dir: Path) -> dict[str, Any]:
    baseline_dir = Path(baseline_dir).resolve()
    candidate_dir = Path(candidate_dir).resolve()
    base = _load_models(baseline_dir)
    cand = _load_models(candidate_dir)
    shared = sorted(set(base.keys()) & set(cand.keys()))
    rows: list[dict[str, Any]] = []
    for model in shared:
        bo = base[model].get("overall", {})
        co = cand[model].get("overall", {})
        row: dict[str, Any] = {"model": model, "metrics": {}}
        for mk in METRIC_KEYS:
            bv = float(bo.get(mk, 0.0))
            cv = float(co.get(mk, 0.0))
            row["metrics"][mk] = {"baseline": bv, "candidate": cv, "delta": round(cv - bv, 3)}
        rows.append(row)
    return {
        "baseline_path": str(baseline_dir),
        "candidate_path": str(candidate_dir),
        "shared_models": shared,
        "rows": rows,
    }


def render_cross_corpus_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Cross-corpus model comparison",
        "",
        f"- Baseline report: `{payload['baseline_path']}`",
        f"- Candidate report: `{payload['candidate_path']}`",
        f"- Shared models: `{', '.join(payload['shared_models']) or '(none)'}`",
        "",
        "Ordinal rank order below is descriptive only (not a significance test).",
        "",
        "## Side-by-side overall metrics",
        "",
    ]
    rows = payload["rows"]
    if not rows:
        lines.append("_No shared model keys between reports._")
        return "\n".join(lines) + "\n"

    header = "| Model | Metric | Baseline | Candidate | Delta |"
    sep = "| --- | --- | --- | --- | --- |"
    lines.extend([header, sep])
    for r in rows:
        model = r["model"]
        for mk in METRIC_KEYS:
            m = r["metrics"][mk]
            lines.append(
                f"| `{model}` | {mk} | {m['baseline']:.3f} | {m['candidate']:.3f} | {m['delta']:+.3f} |"
            )
    lines.append("")
    lines.append("## Rank order (baseline report, higher answer support first)")
    models_by_support = sorted(
        [r["model"] for r in rows],
        key=lambda m: -next(x["metrics"]["answer_support_rate"]["baseline"] for x in rows if x["model"] == m),
    )
    for i, m in enumerate(models_by_support, 1):
        lines.append(f"{i}. `{m}`")
    lines.append("")
    return "\n".join(lines)
