"""Tests for prompt builder."""

from src.application.prompt_builder import build_prompt
from src.domain.entities import Card, SlotDraw


def test_build_single_prompt_uses_selected_orientation() -> None:
    card = Card(
        id=1,
        name="Маг",
        orig_name="The Magician",
        straight_position="прямое",
        inverted_position="перевернутое",
    )
    slots = (SlotDraw(slot_code="T1", slot_index=0, card_id=1, is_inverted=False),)
    request = build_prompt(
        system_template="sys",
        user_template="Карта: {card_name}, {orientation}, {meaning}",
        spread_code="single",
        slots=slots,
        cards={1: card},
    )
    assert "прямое" in request.user_content
    assert "перевернутое" not in request.user_content
