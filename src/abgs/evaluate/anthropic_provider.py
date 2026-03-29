from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from abgs.contracts import BenchmarkRecord


class AnthropicEvaluationError(RuntimeError):
    """Raised when Anthropic evaluation cannot complete."""


def answer_question(model_name: str | None, record: BenchmarkRecord) -> dict[str, Any]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise AnthropicEvaluationError("Missing ANTHROPIC_API_KEY. Add it to the repo-root .env file or environment.")

    resolved_model = model_name or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    prompt = _build_prompt(record)
    payload = {
        "model": resolved_model,
        "max_tokens": 400,
        "temperature": 0.1,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise AnthropicEvaluationError(f"Anthropic HTTP error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise AnthropicEvaluationError(f"Anthropic request failed: {exc}") from exc

    text = _extract_text(raw)
    parsed = _parse_json(text)
    answer = str(parsed.get("answer", "")).strip()
    refused = bool(parsed.get("refused", False))
    if not answer:
        if refused:
            answer = "REFUSE: insufficient source excerpts"
        else:
            raise AnthropicEvaluationError("Anthropic evaluation response did not include an answer.")
    return {
        "answer": answer,
        "refused": refused,
        "raw_response": parsed,
        "model_name": resolved_model,
    }


def _build_prompt(record: BenchmarkRecord) -> str:
    citations = "\n\n".join(
        f"Source {index + 1}:\n{citation['text']}"
        for index, citation in enumerate(record.metadata["citations"])
        if citation["text"]
    )
    return (
        "Answer the benchmark question using only the provided source excerpts.\n"
        "Return JSON only with keys: answer, refused.\n"
        "Rules:\n"
        "- If the excerpts are sufficient, set refused to false and answer concisely.\n"
        "- If the excerpts are insufficient, set refused to true and briefly explain why.\n"
        "- Do not mention source numbers in the answer.\n\n"
        f"Question:\n{record.question}\n\n"
        f"Source excerpts:\n{citations}\n"
    )


def _extract_text(payload: dict[str, Any]) -> str:
    content = payload.get("content", [])
    texts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
    result = "\n".join(texts).strip()
    if not result:
        raise AnthropicEvaluationError("Anthropic response contained no text.")
    return result


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    if start >= 0:
        try:
            obj, _ = json.JSONDecoder().raw_decode(cleaned, start)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    raise AnthropicEvaluationError(f"Could not parse Anthropic JSON response: {cleaned[:400]}")
