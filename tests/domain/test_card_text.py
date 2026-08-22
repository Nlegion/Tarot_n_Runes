"""Tests for card text preprocessing."""

from src.domain.card_text import (
    fix_sentence_gaps,
    normalize_orig_name,
    preprocess_card_field,
    strip_position_header,
)


def test_strip_fool_header() -> None:
    raw = "Прямое положение\nТекст карты."
    assert strip_position_header(raw) == "Текст карты."


def test_fix_sentence_gap() -> None:
    assert fix_sentence_gaps("конец.Также начало") == "конец. Также начало"


def test_glue_dictionary() -> None:
    result = preprocess_card_field("видекарта Маг означает")
    assert "виде карта" in result


def test_orig_name_homoglyph() -> None:
    assert normalize_orig_name("Aсe of Wands") == "Ace of Wands"


def test_preprocess_idempotent() -> None:
    raw = "Текст.Также продолжение"
    once = preprocess_card_field(raw)
    twice = preprocess_card_field(once)
    assert once == twice
