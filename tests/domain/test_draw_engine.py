"""Tests for draw engine."""

from src.domain.draw_engine import draw_spread


def test_draw_three_unique_cards() -> None:
    result = draw_spread(spread_code="three", allow_inverted=True)
    card_ids = [slot.card_id for slot in result.slots]
    assert len(card_ids) == len(set(card_ids))
    assert len(result.slots) == 3


def test_draw_respects_inverted_setting() -> None:
    result = draw_spread(spread_code="single", allow_inverted=False)
    assert result.slots[0].is_inverted is False
