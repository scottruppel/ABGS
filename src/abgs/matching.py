from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(slots=True)
class QuoteMatch:
    matched: bool
    start_char: int
    end_char: int
    text: str
    mode: str
    score: float
    recovered: bool


def match_quote_to_text(text: str, quote: str) -> QuoteMatch:
    if not quote.strip() or not text.strip():
        return QuoteMatch(False, -1, -1, "", "unmatched", 0.0, False)

    exact_start = text.find(quote)
    if exact_start >= 0:
        return QuoteMatch(
            True,
            exact_start,
            exact_start + len(quote),
            quote,
            "strict_exact",
            1.0,
            False,
        )

    normalized_text, text_map = _normalize_with_map(text, aggressive=True)
    normalized_quote, _ = _normalize_with_map(quote, aggressive=True)
    normalized_start = normalized_text.find(normalized_quote)
    if normalized_quote and normalized_start >= 0:
        raw_start = text_map[normalized_start][0]
        raw_end = text_map[normalized_start + len(normalized_quote) - 1][1]
        return QuoteMatch(
            True,
            raw_start,
            raw_end,
            text[raw_start:raw_end],
            "fuzzy_normalized",
            1.0,
            True,
        )

    window_match = _best_window_match(text, normalized_quote)
    if window_match is not None:
        return window_match

    return QuoteMatch(False, -1, -1, "", "unmatched", 0.0, False)


def text_contains_quote(text: str, quote: str) -> tuple[bool, bool, str]:
    match = match_quote_to_text(text, quote)
    return match.matched, match.recovered, match.mode


def normalized_text(text: str) -> str:
    normalized, _ = _normalize_with_map(text, aggressive=True)
    return normalized


def _best_window_match(text: str, normalized_quote: str) -> QuoteMatch | None:
    spans = _sentence_spans(text)
    if not spans:
        return None

    best: QuoteMatch | None = None
    max_window = min(3, len(spans))
    quote_tokens = _token_set(normalized_quote)

    for start_idx in range(len(spans)):
        for window_size in range(1, max_window + 1):
            end_idx = start_idx + window_size - 1
            if end_idx >= len(spans):
                break
            raw_start = spans[start_idx][0]
            raw_end = spans[end_idx][1]
            raw_text = text[raw_start:raw_end].strip()
            if not raw_text:
                continue
            candidate = normalized_text(raw_text)
            sequence_score = SequenceMatcher(None, candidate, normalized_quote).ratio()
            quote_recall = _quote_recall(quote_tokens, _token_set(candidate))
            score = max(sequence_score, quote_recall)
            if not _passes_fuzzy_threshold(sequence_score, quote_recall):
                continue
            current = QuoteMatch(
                True,
                raw_start,
                raw_end,
                text[raw_start:raw_end],
                "fuzzy_window",
                round(score, 3),
                True,
            )
            if best is None or current.score > best.score:
                best = current

    return best


def _passes_fuzzy_threshold(sequence_score: float, quote_recall: float) -> bool:
    return sequence_score >= 0.82 or (sequence_score >= 0.67 and quote_recall >= 0.8)


def _quote_recall(left_tokens: set[str], right_tokens: set[str]) -> float:
    if not left_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens)


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9]+", text.lower()))


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in re.finditer(r".+?(?:[.!?](?=\s|$)|\n{2,}|$)", text, flags=re.DOTALL):
        start, end = match.span()
        if text[start:end].strip():
            spans.append((start, end))
    if spans:
        return spans
    stripped = text.strip()
    if not stripped:
        return []
    start = text.find(stripped)
    return [(start, start + len(stripped))]


def _normalize_with_map(text: str, aggressive: bool) -> tuple[str, list[tuple[int, int]]]:
    raw = text.replace("\r\n", "\n").replace("\r", "\n")
    pieces: list[str] = []
    mapping: list[tuple[int, int]] = []
    index = 0

    while index < len(raw):
        char = raw[index]
        if aggressive and char == "\u00ad":
            index += 1
            continue
        if aggressive and _is_wrapped_hyphen(raw, index):
            index += 1
            while index < len(raw) and raw[index].isspace():
                index += 1
            continue

        normalized = unicodedata.normalize("NFKC", char)
        for normalized_char in normalized:
            if aggressive and normalized_char.isspace():
                if pieces and pieces[-1] == " ":
                    continue
                pieces.append(" ")
                mapping.append((index, index + 1))
                continue
            pieces.append(normalized_char)
            mapping.append((index, index + 1))
        index += 1

    if aggressive:
        while pieces and pieces[0] == " ":
            pieces.pop(0)
            mapping.pop(0)
        while pieces and pieces[-1] == " ":
            pieces.pop()
            mapping.pop()

    return "".join(pieces), mapping


def _is_wrapped_hyphen(text: str, index: int) -> bool:
    if text[index] != "-":
        return False
    left = text[index - 1] if index > 0 else ""
    if not left.isalnum():
        return False
    right_index = index + 1
    saw_break = False
    while right_index < len(text) and text[right_index].isspace():
        saw_break = True
        right_index += 1
    if not saw_break or right_index >= len(text):
        return False
    return text[right_index].isalnum()
