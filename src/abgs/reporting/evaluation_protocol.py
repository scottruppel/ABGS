"""Build reproducibility metadata for benchmark reports (no secrets)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from abgs import __version__
from abgs.evaluate.pipeline import EVALUATION_PROTOCOL_ID
from abgs.hashing import hash_file, sha256_json


def build_evaluation_protocol(
    *,
    validated_qa_path: str | Path,
    run_manifest_path: str | Path | None = None,
    run_manifest_obj: dict[str, Any] | None = None,
    resolved_models: dict[str, str],
) -> dict[str, Any]:
    """Hashes and IDs for third-party reproduction of published numbers."""
    vq = Path(validated_qa_path)
    if run_manifest_obj is not None:
        manifest_obj = run_manifest_obj
        manifest_sha = sha256_json(manifest_obj)
        manifest_path_str = str(run_manifest_path) if run_manifest_path else ""
    else:
        mf = Path(run_manifest_path or "")
        manifest_obj = json.loads(mf.read_text(encoding="utf-8"))
        manifest_sha = hash_file(mf)
        manifest_path_str = str(mf).replace("\\", "/")
    return {
        "abgs_version": __version__,
        "evaluation_protocol_id": EVALUATION_PROTOCOL_ID,
        "validated_qa_sha256": hash_file(vq),
        "validated_qa_path": str(vq).replace("\\", "/"),
        "run_manifest_sha256": manifest_sha,
        "run_manifest_path": manifest_path_str,
        "run_id": manifest_obj.get("run_id"),
        "pipeline_version": manifest_obj.get("pipeline_version"),
        "config_hash": manifest_obj.get("config_hash"),
        "input_corpus_hashes": manifest_obj.get("input_corpus_hashes", []),
        "resolved_models": dict(resolved_models),
    }
