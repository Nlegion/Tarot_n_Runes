"""Tests for prompt builder."""

from src.application.prompt_builder import build_prompt, build_repair_prompt
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


def test_build_three_prompt_includes_slot_labels() -> None:
    cards = {
        1: Card(
            id=1,
            name="A",
            orig_name="A",
            straight_position="s",
            inverted_position="i",
        ),
        2: Card(
            id=2,
            name="B",
            orig_name="B",
            straight_position="s",
            inverted_position="i",
        ),
        3: Card(
            id=3,
            name="C",
            orig_name="C",
            straight_position="s",
            inverted_position="i",
        ),
    }
    slots = (
        SlotDraw(slot_code="PAST", slot_index=0, card_id=1, is_inverted=False),
        SlotDraw(slot_code="PRESENT", slot_index=1, card_id=2, is_inverted=False),
        SlotDraw(slot_code="FUTURE", slot_index=2, card_id=3, is_inverted=False),
    )
    request = build_prompt(
        system_template="sys",
        user_template="{slots_block}",
        spread_code="three",
        slots=slots,
        cards=cards,
    )
    assert "Прошлое:" in request.user_content
    assert "Настоящее:" in request.user_content
    assert "Будущее:" in request.user_content


def test_repair_prompt_three_requires_sections() -> None:
    base = build_prompt(
        system_template="sys",
        user_template="user",
        spread_code="three",
        slots=(SlotDraw(slot_code="PAST", slot_index=0, card_id=1, is_inverted=False),),
        cards={
            1: Card(
                id=1,
                name="A",
                orig_name="A",
                straight_position="s",
                inverted_position="i",
            )
        },
    )
    repair = build_repair_prompt(
        base=base,
        issues=["missing_section:Будущее"],
        spread_code="three",
    )
    assert "Прошлое" in repair.system_prompt
    assert "Будущее" in repair.system_prompt
    assert "служебных меток" not in repair.system_prompt
