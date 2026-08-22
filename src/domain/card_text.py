"""Card text preprocessing (pure functions, no I/O)."""

from __future__ import annotations

import re
import unicodedata

_POSITION_HEADERS = frozenset(
    {
        "прямое положение",
        "перевернутое положение",
        "перевёрнутое положение",
    }
)

_GLUE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("видекарта", "виде карта"),
    ("перевернутомвиде", "перевернутом виде"),
    ("жрецв", "жрец в"),
    ("Деломожет", "Дело может"),
    ("виде карта", "виде карта"),
)

_HOMOGLYPHS = str.maketrans(
    {"с": "c", "С": "C", "е": "e", "Е": "E", "а": "a", "А": "A"}
)

_SENTENCE_GAP = re.compile(r"\.([А-ЯA-ZЁ])")
_MULTI_SPACE = re.compile(r"[^\S\n]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")


def normalize_unicode(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    return unicodedata.normalize("NFC", text)


def strip_position_header(text: str) -> str:
    lines = text.split("\n")
    if not lines:
        return text
    first = lines[0].strip().casefold()
    if first in _POSITION_HEADERS:
        return "\n".join(lines[1:]).strip()
    return text.strip()


def fix_sentence_gaps(text: str) -> str:
    return _SENTENCE_GAP.sub(r". \1", text)


def apply_glue_dictionary(text: str) -> str:
    result = text
    for old, new in _GLUE_REPLACEMENTS:
        result = result.replace(old, new)
    return result


def normalize_whitespace(text: str) -> str:
    lines = [line.strip() for line in text.split("\n")]
    compact: list[str] = []
    blank_run = False
    for line in lines:
        if not line:
            if not blank_run:
                compact.append("")
                blank_run = True
            continue
        blank_run = False
        compact.append(_MULTI_SPACE.sub(" ", line))
    result = "\n".join(compact).strip()
    return _MULTI_NEWLINE.sub("\n\n", result)


def normalize_orig_name(orig_name: str) -> str:
    cleaned = normalize_unicode(orig_name).strip()
    return cleaned.translate(_HOMOGLYPHS)


def preprocess_card_field(text: str) -> str:
    text = normalize_unicode(text)
    text = strip_position_header(text)
    text = fix_sentence_gaps(text)
    text = apply_glue_dictionary(text)
    text = normalize_whitespace(text)
    return text


def preprocess_card_name(name: str) -> str:
    return normalize_unicode(name).strip()


def preprocess_card_row(
    *,
    name: str,
    orig_name: str,
    straight_position: str,
    inverted_position: str,
) -> dict[str, str]:
    straight = preprocess_card_field(straight_position)
    inverted = preprocess_card_field(inverted_position)
    if not straight or not inverted:
        raise ValueError("Card position text must not be empty after preprocessing")
    return {
        "name": preprocess_card_name(name),
        "orig_name": normalize_orig_name(orig_name),
        "straight_position": straight,
        "inverted_position": inverted,
    }
