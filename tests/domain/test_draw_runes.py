"""Tests for rune draw constraints."""

from src.core.settings.constants import RUNE_ID_MAX, RUNE_ID_MIN
from src.domain.draw_engine import DrawConfig, draw_spread


def test_rune_draw_unique_ids() -> None:
    config = DrawConfig(id_min=RUNE_ID_MIN, id_max=RUNE_ID_MAX)
    result = draw_spread(spread_code="three", allow_inverted=True, config=config)
    ids = [slot.card_id for slot in result.slots]
    assert len(ids) == len(set(ids))
    assert all(RUNE_ID_MIN <= i <= RUNE_ID_MAX for i in ids)


def test_non_invertible_never_inverted() -> None:
    non_invertible = frozenset(range(1, 26))
    config = DrawConfig(
        id_min=1,
        id_max=25,
        non_invertible_ids=non_invertible,
    )
    for _ in range(20):
        result = draw_spread(spread_code="single", allow_inverted=True, config=config)
        assert result.slots[0].is_inverted is False
