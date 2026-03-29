from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict

from abgs.config import PipelineConfig
from abgs.contracts import (
    CandidateAnswer,
    CandidateQuestion,
    ChunkRecord,
    CitationSpan,
    CoverageLedgerEntry,
    DocumentRecord,
    PromptTrace,
    QuestionType,
)
from abgs.hashing import sha256_json, sha256_text
from abgs.matching import match_quote_to_text
from abgs.generate.gemini_provider import GeminiProviderError, generate_question_answer

LOGGER = logging.getLogger(__name__)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "could",
    "for",
    "from",
    "has",
    "have",
    "how",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "should",
    "such",
    "that",
    "the",
    "their",
    "there",
    "these",
    "this",
    "those",
    "through",
    "to",
    "under",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "will",
    "with",
    "would",
}
GENERIC_TOPIC_TOKENS = {
    "appendix",
    "chapter",
    "classified",
    "contents",
    "executive",
    "figure",
    "history",
    "introduction",
    "january",
    "july",
    "memorandum",
    "page",
    "plan",
    "policy",
    "revision",
    "section",
    "strategy",
    "subject",
    "summary",
    "table",
    "unclassified",
    "version",
}


def generate_candidates(
    run_id: str,
    documents: list[DocumentRecord],
    chunks: list[ChunkRecord],
    config: PipelineConfig,
) -> tuple[list[CandidateQuestion], list[CoverageLedgerEntry], list[CandidateAnswer], dict[str, object]]:
    doc_chunks = _group_by_document(chunks)
    questions: list[CandidateQuestion] = []
    answers: list[CandidateAnswer] = []
    coverage_state = _init_coverage(documents, chunks)
    total_questions = max(len(chunks), len(chunks) * config.generation.target_questions_per_chunk)
    if config.generation.max_questions is not None:
        total_questions = min(total_questions, config.generation.max_questions)
    multi_chunk_target = max(1, int(total_questions * config.generation.minimum_multi_chunk_ratio))
    question_signatures: set[str] = set()
    unique_topics: set[str] = set()
    generation_summary = {
        "target_questions": total_questions,
        "attempted_questions": 0,
        "generated_questions": 0,
        "skipped_duplicate_signatures": 0,
        "skipped_low_quality_topics": 0,
        "unique_topic_count": 0,
    }
    max_attempts = max(total_questions * 8, len(chunks) * 8)

    while len(questions) < total_questions and generation_summary["attempted_questions"] < max_attempts:
        chunk = _select_next_chunk(doc_chunks, coverage_state)
        if chunk is None:
            break
        generation_summary["attempted_questions"] += 1
        question_type = _pick_question_type(coverage_state[chunk.document_id])
        use_multi_chunk = (
            len(questions) < multi_chunk_target
            and chunk.chunk_index + 1 < len(doc_chunks[chunk.document_id])
        )
        selected_chunks = [chunk]
        if use_multi_chunk:
            selected_chunks.append(doc_chunks[chunk.document_id][chunk.chunk_index + 1])

        topic, topic_quality = _infer_topic(" ".join(item.text for item in selected_chunks))
        if topic is None:
            generation_summary["skipped_low_quality_topics"] += 1
            _record_chunk_attempt(coverage_state[chunk.document_id], selected_chunks)
            continue

        signature = _question_signature(question_type, topic)
        if signature in question_signatures:
            generation_summary["skipped_duplicate_signatures"] += 1
            _record_chunk_attempt(coverage_state[chunk.document_id], selected_chunks)
            continue

        question_signatures.add(signature)
        unique_topics.add(topic)
        prompt_trace = _prompt_trace(chunk, selected_chunks, question_type, config)
        question_id = f"{run_id}-q-{len(questions):04d}"
        rendered = _render_generation(
            question_type=question_type,
            topic=topic,
            selected_chunks=selected_chunks,
            prompt_trace=prompt_trace,
            config=config,
        )
        final_topic = rendered["topic"]
        if not final_topic or not _is_valid_topic_for_output(final_topic):
            generation_summary["skipped_low_quality_topics"] += 1
            _record_chunk_attempt(coverage_state[chunk.document_id], selected_chunks)
            question_signatures.discard(signature)
            unique_topics.discard(topic)
            continue

        question_text = rendered["question"]
        quality_signals = {
            "multi_chunk_required": use_multi_chunk,
            "chunk_count": len(selected_chunks),
            "topic": final_topic,
            "topic_quality": rendered["topic_quality"],
        }

        question = CandidateQuestion(
            question_id=question_id,
            run_id=run_id,
            document_id=chunk.document_id,
            chunk_ids=[item.chunk_id for item in selected_chunks],
            question=question_text,
            question_type=question_type,
            topic=final_topic,
            prompt_trace=prompt_trace,
            quality_signals=quality_signals,
        )
        answer = _render_answer(question, selected_chunks, rendered)
        questions.append(question)
        answers.append(answer)
        _update_coverage(coverage_state[chunk.document_id], selected_chunks, question_type, use_multi_chunk, final_topic)
        generation_summary["generated_questions"] += 1

    ledger = [
        CoverageLedgerEntry(
            document_id=document.document_id,
            topic=state["topic"],
            chunks_total=state["chunks_total"],
            chunks_covered=state["chunks_covered"],
            questions_generated=state["questions_generated"],
            multi_chunk_questions=state["multi_chunk_questions"],
            question_types=dict(state["question_types"]),
        )
        for document in documents
        for state in [coverage_state[document.document_id]]
    ]
    generation_summary["unique_topic_count"] = len(unique_topics)
    return questions, ledger, answers, generation_summary


def _group_by_document(chunks: list[ChunkRecord]) -> dict[str, list[ChunkRecord]]:
    grouped: dict[str, list[ChunkRecord]] = defaultdict(list)
    for chunk in chunks:
        grouped[chunk.document_id].append(chunk)
    return grouped


def _init_coverage(documents: list[DocumentRecord], chunks: list[ChunkRecord]) -> dict[str, dict[str, object]]:
    chunk_counts = Counter(chunk.document_id for chunk in chunks)
    return {
        document.document_id: {
            "topic": document.document_id,
            "chunks_total": chunk_counts[document.document_id],
            "chunks_covered": 0,
            "questions_generated": 0,
            "multi_chunk_questions": 0,
            "question_types": Counter(),
            "seen_chunks": set(),
            "chunk_use_counts": Counter(),
        }
        for document in documents
    }


def _select_next_chunk(
    doc_chunks: dict[str, list[ChunkRecord]],
    coverage_state: dict[str, dict[str, object]],
) -> ChunkRecord | None:
    scored: list[tuple[float, ChunkRecord]] = []
    for document_id, chunks in doc_chunks.items():
        state = coverage_state[document_id]
        coverage_ratio = state["chunks_covered"] / max(1, state["chunks_total"])
        for chunk in chunks:
            use_count = state["chunk_use_counts"][chunk.chunk_id]
            score = coverage_ratio + use_count + (chunk.chunk_index / max(1, len(chunks)))
            scored.append((score, chunk))
    if not scored:
        return None
    return min(scored, key=lambda item: item[0])[1]


def _pick_question_type(state: dict[str, object]) -> QuestionType:
    counts: Counter = state["question_types"]
    ordered = [
        QuestionType.FACTUAL,
        QuestionType.PROCEDURAL,
        QuestionType.ANALYTICAL,
        QuestionType.EDGE_CASE,
    ]
    return min(ordered, key=lambda item: counts[item.value])


def _infer_topic(text: str) -> tuple[str | None, dict[str, object]]:
    sentence = _first_sentence(text).lower()
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]+", sentence)
    filtered: list[tuple[int, str]] = []

    for index, token in enumerate(tokens):
        if _is_valid_topic_token(token):
            filtered.append((index, token))

    if not filtered:
        return None, {"status": "rejected", "reason": "no_valid_topic_tokens"}

    phrase_candidates = _phrase_candidates(tokens, filtered)
    if phrase_candidates:
        best_phrase = max(phrase_candidates, key=lambda item: item[1])[0]
        return best_phrase, {"status": "accepted", "source": "phrase"}

    counts = Counter(token for _, token in filtered)
    best_token = max(counts, key=lambda token: (counts[token], len(token)))
    return best_token, {"status": "accepted", "source": "token"}


def _prompt_trace(
    chunk: ChunkRecord,
    selected_chunks: list[ChunkRecord],
    question_type: QuestionType,
    config: PipelineConfig,
) -> PromptTrace:
    template = "Generate a {question_type} benchmark question grounded in the provided chunk context."
    prompt_inputs = {
        "chunk_ids": [item.chunk_id for item in selected_chunks],
        "chunk_hashes": [item.chunk_hash for item in selected_chunks],
        "question_type": question_type.value,
        "document_id": chunk.document_id,
    }
    return PromptTrace(
        prompt_version=config.generation.prompt_version,
        prompt_template_hash=sha256_text(template),
        prompt_inputs_hash=sha256_json(prompt_inputs),
        model_name=config.generation.model_name,
        provider=config.generation.provider,
        seed=config.generation.seed,
    )


def _render_question(question_type: QuestionType, topic: str, chunks: list[ChunkRecord]) -> str:
    if question_type is QuestionType.FACTUAL:
        return f"What does the corpus state about {topic}?"
    if question_type is QuestionType.PROCEDURAL:
        return f"What procedure is described for {topic}?"
    if question_type is QuestionType.ANALYTICAL:
        return f"How should the reader synthesize the guidance about {topic} across the cited material?"
    return f"What edge case or operational risk is associated with {topic}?"


def _render_generation(
    *,
    question_type: QuestionType,
    topic: str,
    selected_chunks: list[ChunkRecord],
    prompt_trace: PromptTrace,
    config: PipelineConfig,
) -> dict[str, object]:
    if config.generation.provider == "gemini":
        try:
            generated = generate_question_answer(
                question_type=question_type,
                inferred_topic=topic,
                chunks=selected_chunks,
                config=config,
            )
            prompt_trace.model_name = generated["model_name"]
            prompt_trace.provider = "gemini"
            return {
                "topic": generated["topic"],
                "question": generated["question"],
                "answer": generated["answer"],
                "acceptable_answers": generated["acceptable_answers"],
                "support_quotes": generated["support_quotes"],
                "topic_quality": {"status": "accepted", "source": "provider"},
                "provider_trace": generated["raw_response"],
            }
        except GeminiProviderError as exc:
            LOGGER.warning("Gemini generation failed for topic '%s'; falling back to deterministic mode: %s", topic, exc)

    return {
        "topic": topic,
        "question": _render_question(question_type, topic, selected_chunks),
        "answer": " ".join(_first_sentence(chunk.text) for chunk in selected_chunks).strip(),
        "acceptable_answers": [" ".join(_first_sentence(chunk.text) for chunk in selected_chunks).strip()],
        "support_quotes": [_first_sentence(chunk.text) for chunk in selected_chunks],
        "topic_quality": {"status": "accepted", "source": "heuristic"},
        "provider_trace": {"fallback": "deterministic"},
    }


def _render_answer(question: CandidateQuestion, chunks: list[ChunkRecord], rendered: dict[str, object]) -> CandidateAnswer:
    citation_text = str(rendered["answer"]).strip()
    support_quotes = [str(item).strip() for item in rendered.get("support_quotes", []) if str(item).strip()]
    support_quote_matches = []
    citations: list[CitationSpan] = []
    for quote in support_quotes:
        match = _best_citation_for_quote(chunks, quote)
        support_quote_matches.append(match)
        if match["matched"] and match["citation"] is not None:
            citations.append(match["citation"])
    return CandidateAnswer(
        question_id=question.question_id,
        answer=citation_text,
        acceptable_answers=list(rendered["acceptable_answers"]),
        citations=citations,
        token_usage={"prompt_tokens": len(question.question.split()), "completion_tokens": len(citation_text.split())},
        estimated_cost_usd=0.0,
        trace={
            "source_chunk_ids": question.chunk_ids,
            "provider_trace": rendered["provider_trace"],
            "support_quotes": support_quotes,
            "support_quote_matches": support_quote_matches,
        },
    )


def _first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)
    return parts[0].strip() if parts and parts[0].strip() else text.strip()


def _update_coverage(
    state: dict[str, object],
    chunks: list[ChunkRecord],
    question_type: QuestionType,
    use_multi_chunk: bool,
    topic: str,
) -> None:
    state["topic"] = topic
    seen_chunks: set[str] = state["seen_chunks"]
    chunk_use_counts: Counter = state["chunk_use_counts"]
    before = len(seen_chunks)
    seen_chunks.update(chunk.chunk_id for chunk in chunks)
    for chunk in chunks:
        chunk_use_counts[chunk.chunk_id] += 1
    state["chunks_covered"] += len(seen_chunks) - before
    state["questions_generated"] += 1
    if use_multi_chunk:
        state["multi_chunk_questions"] += 1
    state["question_types"][question_type.value] += 1


def _record_chunk_attempt(state: dict[str, object], chunks: list[ChunkRecord]) -> None:
    chunk_use_counts: Counter = state["chunk_use_counts"]
    for chunk in chunks:
        chunk_use_counts[chunk.chunk_id] += 1


def _is_valid_topic_token(token: str) -> bool:
    if token in STOPWORDS or token in GENERIC_TOPIC_TOKENS:
        return False
    if len(token) < 4:
        return False
    if len(set(token)) <= 2 and len(token) >= 6:
        return False
    if not re.search(r"[aeiou]", token):
        return False
    return True


def _phrase_candidates(tokens: list[str], filtered: list[tuple[int, str]]) -> list[tuple[str, int]]:
    candidates: list[tuple[str, int]] = []
    for idx in range(len(filtered) - 1):
        left_pos, left_token = filtered[idx]
        right_pos, right_token = filtered[idx + 1]
        if right_pos == left_pos + 1:
            phrase = f"{left_token} {right_token}"
            candidates.append((phrase, len(left_token) + len(right_token) + 4))
    return candidates


def _question_signature(question_type: QuestionType, topic: str) -> str:
    return f"{question_type.value}|{topic}"


def _is_valid_topic_for_output(topic: str) -> bool:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]+", topic.lower())
    if not tokens:
        return False
    return any(_is_valid_topic_token(token) for token in tokens)


def _best_citation_for_quote(chunks: list[ChunkRecord], quote: str) -> dict[str, object]:
    best_match: dict[str, object] | None = None
    for chunk in chunks:
        quote_match = match_quote_to_text(chunk.text, quote)
        if not quote_match.matched:
            continue
        citation = CitationSpan(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            chunk_hash=chunk.chunk_hash,
            start_char=quote_match.start_char,
            end_char=quote_match.end_char,
            text=quote_match.text,
        )
        candidate = {
            "quote": quote,
            "matched": True,
            "match_mode": quote_match.mode,
            "score": quote_match.score,
            "recovered": quote_match.recovered,
            "chunk_id": chunk.chunk_id,
            "citation": citation,
        }
        if quote_match.mode == "strict_exact":
            return candidate
        if best_match is None or float(candidate["score"]) > float(best_match["score"]):
            best_match = candidate

    if best_match is not None:
        return best_match
    return {
        "quote": quote,
        "matched": False,
        "match_mode": "unmatched",
        "score": 0.0,
        "recovered": False,
        "chunk_id": None,
        "citation": None,
    }
