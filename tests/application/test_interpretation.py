"""Tests for interpretation postprocessing."""

from src.application.interpretation import (
    finalize_interpretation,
    normalize_paragraphs,
    split_messages,
    strip_markers,
    validate_interpretation,
)
from src.core.settings.constants import SPREAD_SINGLE, SPREAD_THREE


def test_strip_thinking_marker() -> None:
    tag_open = "\x3c" + "redacted_thinking" + "\x3e"
    tag_close = "\x3c/" + "redacted_thinking" + "\x3e"
    raw = f"Hello {tag_open}secret{tag_close} world"
    cleaned = strip_markers(raw)
    assert "secret" not in cleaned
    assert "Hello" in cleaned


def test_normalize_paragraphs() -> None:
    raw = "## Заголовок\n\n- Первый пункт.\n- Второй пункт.\n\nИтог."
    cleaned = normalize_paragraphs(raw)
    assert "\n\n" in cleaned
    assert "##" not in cleaned
    assert "- " not in cleaned


def test_split_long_message() -> None:
    text = "А" * 5000
    chunks = split_messages(text, max_chars=4096)
    assert len(chunks) >= 2
    assert all(len(chunk) <= 4096 for chunk in chunks)


def test_split_prefers_paragraphs() -> None:
    text = "Абзац один.\n\n" + ("Б" * 3000) + "\n\nАбзац три."
    chunks = split_messages(text, max_chars=2000)
    assert chunks[0].startswith("Абзац один.")


def test_validate_too_short() -> None:
    issues = validate_interpretation("коротко")
    assert "too_short" in issues


def test_finalize_dedupes() -> None:
    text = "Один и тот же смысл. Один и тот же смысл."
    cleaned = finalize_interpretation(text, spread_code=SPREAD_SINGLE)
    assert cleaned.count("Один и тот же смысл") == 1


def test_finalize_clamps_length() -> None:
    text = "Абзац.\n\n" + ("Слово " * 400)
    cleaned = finalize_interpretation(text, spread_code=SPREAD_THREE)
    assert len(cleaned) <= 950
