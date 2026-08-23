"""Section detection and clamping for multi-card spreads."""

from __future__ import annotations

import re

from src.core.settings.constants import (
    LABEL_ONLY_BODY_CHARS,
    MAX_TELEGRAM_MESSAGE,
    MIN_SECTION_BODY_CHARS,
    SPREAD_REQUIRED_SECTIONS,
    SPREAD_THREE,
)

_EMPHASIS = re.compile(r"^(?:\*\*|__)(.+?)(?:\*\*|__)", re.DOTALL)
_PREFIX_TRIM = re.compile(r"^[:\u2014\s-]+")
_SECTION_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "Прошлое",
        re.compile(r"^(?:прошлое(?:\s*[:\u2014-])?|в прошлом\b)", re.IGNORECASE),
    ),
    (
        "Настоящее",
        re.compile(
            r"^(?:настоящее(?:\s*[:\u2014-])?|в настоящем\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "Будущее",
        re.compile(r"^(?:будущее(?:\s*[:\u2014-])?|в будущем\b)", re.IGNORECASE),
    ),
)
_CONCLUSION = re.compile(r"^(?:вывод|общий вывод|итог)\b", re.IGNORECASE)


def normalize_section_prefix(paragraph: str) -> str:
    line = paragraph.strip()
    match = _EMPHASIS.match(line)
    if match:
        return match.group(1).strip() + line[match.end() :]
    return line


def section_body(paragraph: str) -> tuple[str | None, str]:
    normalized = normalize_section_prefix(paragraph.strip())
    for name, pattern in _SECTION_RULES:
        if pattern.match(normalized):
            rest = pattern.sub("", normalized, count=1)
            rest = _PREFIX_TRIM.sub("", rest.strip())
            return name, rest
    if _CONCLUSION.match(normalized):
        rest = _CONCLUSION.sub("", normalized, count=1)
        rest = _PREFIX_TRIM.sub("", rest.strip())
        return "Вывод", rest
    return None, normalized


def is_label_only(
    paragraph: str, *, max_body_chars: int = LABEL_ONLY_BODY_CHARS
) -> bool:
    section, body = section_body(paragraph)
    if section is None:
        return False
    return len(body) < max_body_chars


def merge_orphan_labels(text: str) -> str:
    paragraphs = [paragraph for paragraph in text.split("\n\n") if paragraph.strip()]
    if not paragraphs:
        return text

    merged: list[str] = []
    index = 0
    while index < len(paragraphs):
        current = paragraphs[index]
        if is_label_only(current) and index + 1 < len(paragraphs):
            nxt = paragraphs[index + 1]
            nxt_section, _nxt_body = section_body(nxt)
            if nxt_section is None:
                merged.append(f"{current.strip()}\n{nxt.strip()}")
                index += 2
                continue
        merged.append(current)
        index += 1
    return "\n\n".join(merged)


def detect_section(paragraph: str) -> str | None:
    name, _body = section_body(paragraph)
    return name


def missing_sections(text: str, *, spread_code: str = SPREAD_THREE) -> list[str]:
    required = SPREAD_REQUIRED_SECTIONS.get(spread_code, ())
    if not required:
        return []
    found = {detect_section(paragraph) for paragraph in text.split("\n\n") if paragraph}
    return [name for name in required if name not in found]


def thin_sections(
    text: str,
    *,
    spread_code: str = SPREAD_THREE,
    min_body_chars: int = MIN_SECTION_BODY_CHARS,
) -> list[str]:
    required = SPREAD_REQUIRED_SECTIONS.get(spread_code, ())
    if not required:
        return []
    bodies: dict[str, int] = {}
    for paragraph in text.split("\n\n"):
        if not paragraph.strip():
            continue
        name, body = section_body(paragraph)
        if name in required:
            bodies[name] = max(bodies.get(name, 0), len(body))
    return [name for name in required if bodies.get(name, 0) < min_body_chars]


def clamp_with_sections(
    text: str,
    *,
    max_chars: int,
    spread_code: str = SPREAD_THREE,
) -> str:
    if len(text) <= max_chars:
        return text
    required = SPREAD_REQUIRED_SECTIONS.get(spread_code, ())
    if not required:
        return _clamp_paragraphs(text.split("\n\n"), max_chars=max_chars)

    paragraphs = [paragraph for paragraph in text.split("\n\n") if paragraph.strip()]
    tagged: list[tuple[str, str | None]] = [
        (paragraph, detect_section(paragraph)) for paragraph in paragraphs
    ]
    required_set = set(required)
    kept: list[str] = []
    total = 0
    for paragraph, section in tagged:
        if section in required_set and not is_label_only(paragraph):
            extra = 2 if kept else 0
            kept.append(paragraph)
            total += extra + len(paragraph)
    for paragraph, section in tagged:
        if section in required_set or paragraph in kept:
            continue
        extra = 2 if kept else 0
        if total + extra + len(paragraph) > max_chars:
            continue
        kept.append(paragraph)
        total += extra + len(paragraph)
    if not kept:
        return _clamp_paragraphs(paragraphs, max_chars=max_chars)
    result = "\n\n".join(kept)
    if len(result) > MAX_TELEGRAM_MESSAGE:
        return result[:MAX_TELEGRAM_MESSAGE].rstrip()
    return result


def _clamp_paragraphs(paragraphs: list[str], *, max_chars: int) -> str:
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
    candidate = paragraphs[0] if paragraphs else ""
    if len(candidate) <= max_chars:
        return candidate
    return candidate[:max_chars].rstrip()
