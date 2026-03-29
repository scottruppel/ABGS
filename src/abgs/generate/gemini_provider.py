from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from abgs.config import PipelineConfig
from abgs.contracts import ChunkRecord, QuestionType


class GeminiProviderError(RuntimeError):
    """Raised when Gemini generation cannot complete."""


def generate_question_answer(
    *,
    question_type: QuestionType,
    inferred_topic: str,
    chunks: list[ChunkRecord],
    config: PipelineConfig,
) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiProviderError("Missing GEMINI_API_KEY. Add it to the repo-root .env file or environment.")

    model_name = os.getenv("GEMINI_MODEL", config.generation.model_name)
    prompt = _build_prompt(question_type, inferred_topic, chunks)
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
            "temperature": config.generation.temperature,
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
        raise GeminiProviderError(f"Gemini HTTP error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise GeminiProviderError(f"Gemini request failed: {exc}") from exc

    text = _extract_text(raw)
    parsed = _parse_json(text)
    question = parsed.get("question", "").strip()
    answer = parsed.get("answer", "").strip()
    topic = parsed.get("topic", "").strip().lower()
    acceptable_answers = [
        item.strip()
        for item in parsed.get("acceptable_answers", [])
        if isinstance(item, str) and item.strip()
    ]
    support_quotes = [
        item.strip()
        for item in parsed.get("support_quotes", [])
        if isinstance(item, str) and item.strip()
    ]
    if not question or not answer or not support_quotes:
        raise GeminiProviderError("Gemini response did not include question, answer, and support_quotes.")

    return {
        "question": question,
        "answer": answer,
        "topic": topic or inferred_topic,
        "acceptable_answers": acceptable_answers or [answer],
        "support_quotes": support_quotes,
        "raw_response": parsed,
        "model_name": model_name,
    }


def _build_prompt(question_type: QuestionType, inferred_topic: str, chunks: list[ChunkRecord]) -> str:
    chunk_text = "\n\n".join(
        f"Chunk {index + 1} ({chunk.chunk_id}):\n{chunk.text}"
        for index, chunk in enumerate(chunks)
    )
    return (
        "You are generating a benchmark item from grounded source text.\n"
        "Return JSON only with keys: topic, question, answer, acceptable_answers, support_quotes.\n"
        "Rules:\n"
        "- Topic must be a concise 1-3 word phrase.\n"
        f"- Generate one {question_type.value} question.\n"
        "- The question must be specific, useful, and grounded in the provided chunks.\n"
        "- The answer may be concise and abstractive, but it must be directly supported by the provided chunks.\n"
        "- acceptable_answers must be a short list of semantically equivalent answers.\n"
        "- support_quotes must be 1-2 exact verbatim quotes copied directly from the provided chunks.\n"
        "- Every support quote must be sufficient evidence for the answer and must preserve the original wording.\n"
        f"- Prefer the inferred topic '{inferred_topic}' if it fits the content, but improve it if a better grounded topic exists.\n"
        "- Do not mention chunk ids in the output.\n\n"
        f"{chunk_text}\n"
    )


def _extract_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates", [])
    if not candidates:
        raise GeminiProviderError("Gemini response contained no candidates.")
    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    result = "\n".join(texts).strip()
    if not result:
        raise GeminiProviderError("Gemini response contained no text.")
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
        raise GeminiProviderError(f"Could not parse Gemini JSON response: {cleaned[:400]}") from exc
