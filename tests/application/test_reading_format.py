"""Tests for reading message formatting."""

from src.application.reading_format import (
    escape_html,
    format_reading_header,
    format_reading_message,
)
from src.core.settings.constants import SPREAD_SINGLE, SPREAD_THREE
from src.domain.entities import Card, SlotDraw


def _card(card_id: int, name: str = "Маг") -> Card:
    return Card(
        id=card_id,
        name=name,
        orig_name="The Magician",
        straight_position="сила",
        inverted_position="слабость",
    )


def test_escape_html() -> None:
    assert escape_html("a < b & c") == "a &lt; b &amp; c"


def test_single_header_is_bold() -> None:
    slots = (SlotDraw(slot_code="T1", slot_index=0, card_id=1, is_inverted=False),)
    header = format_reading_header(
        slots=slots,
        cards={1: _card(1)},
        spread_code=SPREAD_SINGLE,
    )
    assert header.startswith("<b>")
    assert "Маг (The Magician)" in header
    assert "прямое положение" in header


def test_three_header_includes_labels() -> None:
    slots = (
        SlotDraw(slot_code="PAST", slot_index=0, card_id=1, is_inverted=False),
        SlotDraw(slot_code="PRESENT", slot_index=1, card_id=2, is_inverted=True),
        SlotDraw(slot_code="FUTURE", slot_index=2, card_id=3, is_inverted=False),
    )
    cards = {
        1: _card(1, "Маг"),
        2: _card(2, "Императрица"),
        3: _card(3, "Звезда"),
    }
    header = format_reading_header(
        slots=slots, cards=cards, spread_code=SPREAD_THREE
    )
    assert "Прошлое:" in header
    assert "Настоящее:" in header
    assert "Будущее:" in header
    assert "перевёрнутое положение" in header


def test_format_reading_message_adds_blank_line() -> None:
    message = format_reading_message(
        header="<b>Маг</b>",
        interpretation="Толкование.",
    )
    assert message == "<b>Маг</b>\n\nТолкование."
