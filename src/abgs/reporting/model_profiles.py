"""Data-driven model behavior profiles and use-case guidance from evaluation summaries."""
from __future__ import annotations

from typing import Any

# Minimum gap to attribute a strength/weakness (avoid noise on ties).
METRIC_GAP = 0.02


def _live_model_keys(evaluation_summary: dict[str, dict[str, Any]]) -> list[str]:
    keys = []
    for name in evaluation_summary:
        if name == "anthropic" or name.startswith("gemini:"):
            keys.append(name)
    return sorted(keys)


def _display_name(model_key: str, resolved_models: dict[str, str] | None) -> str:
    resolved_models = resolved_models or {}
    if model_key.startswith("gemini:"):
        mid = model_key.split(":", 1)[1]
        if mid == "gemini-2.5-flash":
            return "Gemini 2.5 Flash"
        return mid.replace("gemini-", "Gemini ").replace("-", " ").title()
    if model_key == "anthropic":
        aid = resolved_models.get("anthropic", "")
        if "sonnet-4" in aid or "claude-sonnet-4" in aid:
            return "Claude Sonnet 4"
        if aid:
            return f"Claude ({aid})"
        return "Claude (Anthropic)"
    return model_key


def _overall(m: dict[str, Any]) -> dict[str, float]:
    return m.get("overall", {})


def _multi(m: dict[str, Any]) -> dict[str, float]:
    return m.get("by_chunk_mode", {}).get("multi_chunk", {})


def build_model_profiles(
    evaluation_summary: dict[str, dict[str, Any]],
    *,
    focus_models: list[str] | None = None,
    resolved_models: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Per-model strengths, weaknesses, and a one-line behavioral tendency (live models only)."""
    focus = focus_models or _live_model_keys(evaluation_summary)
    if len(focus) < 1:
        return {}

    # Pairwise comparisons: for each model, compare to best competitor on each axis.
    profiles: dict[str, dict[str, Any]] = {}

    def get_metric(key: str, getter) -> dict[str, float]:
        return {k: float(getter(evaluation_summary[k])) for k in focus if k in evaluation_summary}

    mc_support = get_metric(
        "mc_support",
        lambda s: _multi(s).get("answer_support_rate", 0.0),
    )
    cit = get_metric("cit", lambda s: _overall(s).get("citation_support_rate", 0.0))
    align = get_metric("align", lambda s: _overall(s).get("answer_alignment_rate", 0.0))
    refuse = get_metric("refuse", lambda s: _overall(s).get("refusal_rate", 0.0))
    bad_ref = get_metric("bad_ref", lambda s: _overall(s).get("inappropriate_refusal_rate", 0.0))

    for mk in focus:
        if mk not in evaluation_summary:
            continue
        others = [k for k in focus if k != mk]
        if not others:
            profiles[mk] = {
                "display_name": _display_name(mk, resolved_models),
                "strengths": [],
                "weaknesses": [],
                "behavioral_tendency": "Insufficient peer models for comparative profile.",
            }
            continue

        strengths: list[str] = []
        weaknesses: list[str] = []

        my_mc = mc_support.get(mk, 0.0)
        best_other_mc = max(mc_support.get(o, 0.0) for o in others)
        if my_mc > best_other_mc + METRIC_GAP:
            strengths.append("Higher hybrid answer support on multi-chunk synthesis (vs other live models).")
        elif my_mc < best_other_mc - METRIC_GAP:
            weaknesses.append("Lower hybrid answer support on multi-chunk synthesis (vs other live models).")

        my_cit = cit.get(mk, 0.0)
        best_other_cit = max(cit.get(o, 0.0) for o in others)
        if my_cit > best_other_cit + METRIC_GAP:
            strengths.append("Higher citation overlap with source excerpts (quote-style grounding).")
        elif my_cit < best_other_cit - METRIC_GAP:
            weaknesses.append("Lower citation overlap with source excerpts.")

        my_ref = refuse.get(mk, 0.0)
        min_other_ref = min(refuse.get(o, 0.0) for o in others)
        if my_ref < min_other_ref - METRIC_GAP:
            strengths.append("Lower overall refusal rate (answers more often).")
        elif my_ref > min_other_ref + METRIC_GAP:
            weaknesses.append("Higher overall refusal rate.")

        my_bad = bad_ref.get(mk, 0.0)
        min_other_bad = min(bad_ref.get(o, 0.0) for o in others)
        if my_bad > min_other_bad + METRIC_GAP:
            weaknesses.append("Higher inappropriate-refusal rate (abstains when benchmark expects an answer).")
        elif my_bad < min_other_bad - METRIC_GAP:
            strengths.append("Lower inappropriate-refusal rate.")

        my_al = align.get(mk, 0.0)
        best_other_al = max(align.get(o, 0.0) for o in others)
        if my_al > best_other_al + METRIC_GAP:
            strengths.append("Higher answer-alignment vs reference answers (paraphrase match).")
        elif my_al < best_other_al - METRIC_GAP:
            weaknesses.append("Lower answer-alignment vs reference answers.")

        peer_best_cit = max(cit.get(o, 0.0) for o in others)
        peer_min_ref = min(refuse.get(o, 0.0) for o in others)
        tendency = _behavioral_tendency(my_cit, my_ref, my_mc, peer_best_cit, peer_min_ref)

        profiles[mk] = {
            "display_name": _display_name(mk, resolved_models),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "behavioral_tendency": tendency,
        }

    return profiles


def _behavioral_tendency(
    my_cit: float,
    my_ref: float,
    my_mc: float,
    peer_best_cit: float,
    peer_min_ref: float,
) -> str:
    grounded = my_cit >= peer_best_cit - METRIC_GAP
    cautious = my_ref >= peer_min_ref + METRIC_GAP
    if grounded and cautious:
        return "Conservative: stays close to source overlap and declines more often."
    if grounded and not cautious:
        return "Grounded but comparatively willing to answer (moderate refusal)."
    if not grounded and not cautious:
        return "More assertive: lower refusal; source-quote overlap is not the strongest signal on this slice."
    return "Mixed: lower citation overlap than peers with comparatively higher refusal—review failure examples."


def build_use_case_guidance(
    evaluation_summary: dict[str, dict[str, Any]],
    *,
    focus_models: list[str] | None = None,
    resolved_models: dict[str, str] | None = None,
) -> list[str]:
    """Conditional bullets: if your priority is X, prefer Y (only when gaps exceed METRIC_GAP)."""
    focus = focus_models or _live_model_keys(evaluation_summary)
    if len(focus) < 2:
        return []

    lines: list[str] = []

    def name(k: str) -> str:
        return _display_name(k, resolved_models)

    # Find winners for citation and multi-chunk support, lower refusal.
    cit_scores = {k: float(_overall(evaluation_summary[k]).get("citation_support_rate", 0.0)) for k in focus}
    mc_scores = {
        k: float(evaluation_summary[k].get("by_chunk_mode", {}).get("multi_chunk", {}).get("answer_support_rate", 0.0))
        for k in focus
    }
    ref_scores = {k: float(_overall(evaluation_summary[k]).get("refusal_rate", 0.0)) for k in focus}

    best_cit = max(cit_scores, key=cit_scores.get)
    worst_cit = min(cit_scores, key=cit_scores.get)
    if cit_scores[best_cit] > cit_scores[worst_cit] + METRIC_GAP:
        lines.append(
            f"- **Compliance / policy interpretation (maximize source grounding):** prefer **`{name(best_cit)}`** "
            f"(higher citation support on this benchmark)."
        )

    best_mc = max(mc_scores, key=mc_scores.get)
    worst_mc = min(mc_scores, key=mc_scores.get)
    if mc_scores[best_mc] > mc_scores[worst_mc] + METRIC_GAP:
        lines.append(
            f"- **Multi-document synthesis:** prefer **`{name(best_mc)}`** "
            f"(higher hybrid support on multi-chunk items)."
        )

    low_ref = min(ref_scores, key=ref_scores.get)
    high_ref = max(ref_scores, key=ref_scores.get)
    if ref_scores[high_ref] > ref_scores[low_ref] + METRIC_GAP:
        lines.append(
            f"- **Exploratory Q&A / lower friction:** consider **`{name(low_ref)}`** "
            f"(lower refusal rate than `{name(high_ref)}` on this benchmark)."
        )

    bad_ref = {
        k: float(_overall(evaluation_summary[k]).get("inappropriate_refusal_rate", 0.0)) for k in focus
    }
    best_bad = min(bad_ref, key=bad_ref.get)
    worst_bad = max(bad_ref, key=bad_ref.get)
    if bad_ref[worst_bad] > bad_ref[best_bad] + METRIC_GAP:
        lines.append(
            f"- **Avoid silent abstention on answerable items:** prefer **`{name(best_bad)}`** "
            f"(lower inappropriate-refusal rate vs `{name(worst_bad)}`)."
        )

    return lines
