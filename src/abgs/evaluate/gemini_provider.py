from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from abgs.contracts import BenchmarkRecord


class GeminiEvaluationError(RuntimeError):
    """Raised when Gemini evaluation cannot complete."""


def answer_question(model_name: str, record: BenchmarkRecord) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiEvaluationError("Missing GEMINI_API_KEY. Add it to the repo-root .env file or environment.")

    prompt = _build_prompt(record)
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise GeminiEvaluationError(f"Gemini HTTP error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise GeminiEvaluationError(f"Gemini request failed: {exc}") from exc

    text = _extract_text(raw)
    parsed = _parse_json(text)
    answer = str(parsed.get("answer", "")).strip()
    refused = bool(parsed.get("refused", False))
    if not answer:
        raise GeminiEvaluationError("Gemini evaluation response did not include an answer.")
    return {
        "answer": answer,
        "refused": refused,
        "raw_response": parsed,
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
    candidates = payload.get("candidates", [])
    if not candidates:
        raise GeminiEvaluationError("Gemini response contained no candidates.")
    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    result = "\n".join(texts).strip()
    if not result:
        raise GeminiEvaluationError("Gemini response contained no text.")
    return result


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiEvaluationError(f"Could not parse Gemini JSON response: {cleaned[:400]}") from exc
