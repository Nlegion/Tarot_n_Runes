"""Tests for rune text preprocessing."""

from src.domain.rune_text import parse_rune_unicode, preprocess_rune_row


def test_parse_unicode_codepoint() -> None:
    assert parse_rune_unicode("U+16A0") == "\u16a0"


def test_parse_empty_unicode() -> None:
    assert parse_rune_unicode("") is None
    assert parse_rune_unicode(None) is None


def test_preprocess_irreversible_copies_straight() -> None:
    result = preprocess_rune_row(
        name="Гебо",
        orig_name="Gebō",
        unicode_raw="U+16B7",
        straight_position="Прямое значение.",
        inverted_position="",
    )
    assert result["can_invert"] is False
    assert result["inverted_position"] == result["straight_position"]
    assert result["unicode"] == "\u16b7"


def test_odin_has_no_glyph() -> None:
    result = preprocess_rune_row(
        name="Один",
        orig_name="Odin",
        unicode_raw="",
        straight_position="Знак судьбы.",
        inverted_position="",
    )
    assert result["unicode"] is None
    assert result["can_invert"] is False
