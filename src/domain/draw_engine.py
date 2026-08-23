"""Draw engine for tarot and runes."""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from dataclasses import dataclass

from src.core.settings.constants import CARD_ID_MAX, CARD_ID_MIN, DECK_SIZE
from src.domain.entities import DrawResult, SlotDraw

_SPREAD_SLOTS: dict[str, tuple[str, ...]] = {
    "single": ("T1",),
    "daily": ("T1",),
    "three": ("PAST", "PRESENT", "FUTURE"),
}


@dataclass(frozen=True)
class DrawConfig:
    id_min: int = CARD_ID_MIN
    id_max: int = CARD_ID_MAX
    non_invertible_ids: frozenset[int] = frozenset()


TAROT_DRAW_CONFIG = DrawConfig()


def spread_slot_codes(spread_code: str) -> tuple[str, ...]:
    if spread_code not in _SPREAD_SLOTS:
        raise ValueError(f"Unknown spread code: {spread_code}")
    return _SPREAD_SLOTS[spread_code]


def draw_spread(
    *,
    spread_code: str,
    allow_inverted: bool,
    config: DrawConfig | None = None,
) -> DrawResult:
    draw_config = config or TAROT_DRAW_CONFIG
    slot_codes = spread_slot_codes(spread_code=spread_code)
    rng = secrets.SystemRandom()
    card_ids = rng.sample(
        range(draw_config.id_min, draw_config.id_max + 1),
        k=len(slot_codes),
    )
    slots: list[SlotDraw] = []
    for index, (code, card_id) in enumerate(zip(slot_codes, card_ids, strict=True)):
        can_invert = card_id not in draw_config.non_invertible_ids
        inverted = allow_inverted and can_invert and rng.choice((True, False))
        slots.append(
            SlotDraw(
                slot_code=code,
                slot_index=index,
                card_id=card_id,
                is_inverted=inverted,
            )
        )
    return DrawResult(spread_code=spread_code, slots=tuple(slots))


def validate_deck_size(ids: Sequence[int]) -> None:
    if len(ids) != DECK_SIZE:
        raise ValueError(f"Expected {DECK_SIZE} cards, got {len(ids)}")
