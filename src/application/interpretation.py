"""Interpretation postprocessing."""

from __future__ import annotations

import re

from src.application.interpretation_sections import (
    clamp_with_sections,
    merge_orphan_labels,
    missing_sections,
    thin_sections,
)
from src.core.settings.constants import (
    MAX_INTERPRETATION_CHARS,
    MAX_TELEGRAM_MESSAGE,
    MIN_INTERPRETATION_CHARS,
    SPREAD_SINGLE,
    SPREAD_THREE,
)

_TRUNCATION = re.compile(r"\n?\.\.\.\[truncated\]", re.IGNORECASE)
_SERVICE = re.compile(r"<\|.*?\|>", re.DOTALL)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n+")
_MULTI_SPACE = re.compile(r"[^\S\n]+")
_MARKDOWN_HEADER = re.compile(r"^#+\s*", re.MULTILINE)
_BULLET = re.compile(r"^[\-*•]\s+", re.MULTILINE)
_EMPHASIS = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")


_THINKING = re.compile(
    "\x3c"
    + "redacted_thinking"
    + "\x3e"
    + ".*?"
    + "\x3c/"
    + "redacted_thinking"
    + "\x3e",
    re.DOTALL | re.IGNORECASE,
)


def strip_markers(text: str) -> str:
    cleaned = _TRUNCATION.sub("", text)
    cleaned = _THINKING.sub("", cleaned)
    cleaned = _SERVICE.sub("", cleaned)
    return cleaned.strip()


def normalize_paragraphs(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _MARKDOWN_HEADER.sub("", normalized)
    normalized = _BULLET.sub("", normalized)
    normalized = _EMPHASIS.sub(
        lambda match: match.group(1) or match.group(2) or "",
        normalized,
    )
    blocks = _PARAGRAPH_BREAK.split(normalized.strip())
    paragraphs: list[str] = []
    for block in blocks:
        line = _MULTI_SPACE.sub(" ", block.strip())
        if line:
            paragraphs.append(line)
    if paragraphs:
        return "\n\n".join(paragraphs)
    return _MULTI_SPACE.sub(" ", normalized.strip())


def _dedupe_paragraph(text: str) -> str:
    parts = _SENTENCE_SPLIT.split(text.strip())
    if len(parts) < 2:
        return text.strip()
    kept: list[str] = []
    previous: str | None = None
    for part in parts:
        normalized = re.sub(r"\s+", " ", part.strip().casefold())
        if previous is not None and normalized == previous:
            continue
        kept.append(part.strip())
        previous = normalized if normalized else previous
    return " ".join(kept)


def dedupe_sentences(text: str) -> str:
    paragraphs = text.split("\n\n")
    cleaned = (_dedupe_paragraph(paragraph) for paragraph in paragraphs if paragraph)
    return "\n\n".join(cleaned)


def clamp_to_sentence(text: str, *, max_chars: int = MAX_TELEGRAM_MESSAGE) -> str:
    if len(text) <= max_chars:
        return text
    candidate = text[:max_chars].rstrip()
    for punct in (".", "!", "?", "…"):
        idx = candidate.rfind(punct)
        if idx >= int(max_chars * 0.6):
            return candidate[: idx + 1]
    return candidate


def clamp_interpretation(
    text: str, *, max_chars: int, spread_code: str = SPREAD_SINGLE
) -> str:
    if spread_code in (SPREAD_THREE,):
        return clamp_with_sections(text, max_chars=max_chars, spread_code=spread_code)
    if len(text) <= max_chars:
        return text
    paragraphs = text.split("\n\n")
    kept: list[str] = []
    total = 0
    for paragraph in paragraphs:
        extra = 2 if kept else 0
        if total + extra + len(paragraph) > max_chars:
            break
        kept.append(paragraph)
        total += extra + len(paragraph)
    if kept:
        return "\n\n".join(kept)
    return clamp_to_sentence(text, max_chars=max_chars)


def split_messages(text: str, *, max_chars: int = MAX_TELEGRAM_MESSAGE) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(paragraph) <= max_chars:
            current = paragraph
            continue
        remaining = paragraph
        while remaining:
            if len(remaining) <= max_chars:
                chunks.append(remaining)
                break
            piece = clamp_to_sentence(remaining, max_chars=max_chars)
            if not piece:
                piece = remaining[:max_chars]
            chunks.append(piece)
            remaining = remaining[len(piece) :].lstrip()
    if current:
        chunks.append(current)
    return chunks


def prepare_interpretation_text(text: str) -> str:
    cleaned = strip_markers(text)
    cleaned = normalize_paragraphs(cleaned)
    cleaned = merge_orphan_labels(cleaned)
    return dedupe_sentences(cleaned)


def validate_interpretation(
    text: str,
    *,
    spread_code: str = SPREAD_SINGLE,
    pre_clamp_text: str | None = None,
    finish_reason: str | None = None,
) -> list[str]:
    issues: list[str] = []
    if not text.strip():
        issues.append("empty")
    if len(text.strip()) < MIN_INTERPRETATION_CHARS:
        issues.append("too_short")
    if finish_reason == "length":
        issues.append("finish_reason_length")
    if "redacted_thinking" in text.lower():
        issues.append("thinking_marker")
    source = pre_clamp_text if pre_clamp_text is not None else text
    for section in missing_sections(source, spread_code=spread_code):
        issues.append(f"missing_section:{section}")
    for section in thin_sections(source, spread_code=spread_code):
        issues.append(f"thin_section:{section}")
    return issues


def finalize_interpretation(text: str, *, spread_code: str = SPREAD_SINGLE) -> str:
    cleaned = prepare_interpretation_text(text)
    max_chars = MAX_INTERPRETATION_CHARS.get(spread_code, 650)
    return clamp_interpretation(cleaned, max_chars=max_chars, spread_code=spread_code)
