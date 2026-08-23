"""Rune text preprocessing (pure functions, no I/O)."""

from __future__ import annotations

import re

from src.domain.card_text import (
    fix_sentence_gaps,
    normalize_orig_name,
    normalize_unicode,
    normalize_whitespace,
    preprocess_card_name,
    strip_position_header,
)

_UNICODE_CODEPOINT = re.compile(r"^U\+([0-9A-Fa-f]+)$")


def parse_rune_unicode(raw: str | None) -> str | None:
    if raw is None:
        return None
    cleaned = normalize_unicode(raw).strip()
    if not cleaned:
        return None
    match = _UNICODE_CODEPOINT.match(cleaned)
    if match is None:
        raise ValueError(f"Invalid rune Unicode value: {raw!r}")
    return chr(int(match.group(1), 16))


def preprocess_rune_field(text: str) -> str:
    text = normalize_unicode(text)
    text = strip_position_header(text)
    text = fix_sentence_gaps(text)
    text = normalize_whitespace(text)
    return text


def preprocess_rune_row(
    *,
    name: str,
    orig_name: str,
    unicode_raw: str | None,
    straight_position: str,
    inverted_position: str,
) -> dict:
    straight = preprocess_rune_field(straight_position)
    if not straight:
        raise ValueError("Rune straight_position must not be empty after preprocessing")
    inverted_raw = preprocess_rune_field(inverted_position)
    can_invert = bool(inverted_raw)
    inverted = inverted_raw if can_invert else straight
    return {
        "name": preprocess_card_name(name),
        "orig_name": normalize_orig_name(orig_name),
        "unicode": parse_rune_unicode(unicode_raw),
        "straight_position": straight,
        "inverted_position": inverted,
        "can_invert": can_invert,
    }
