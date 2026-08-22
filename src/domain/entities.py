"""Domain entities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Card:
    id: int
    name: str
    orig_name: str
    straight_position: str
    inverted_position: str


@dataclass(frozen=True)
class SlotDraw:
    slot_code: str
    slot_index: int
    card_id: int
    is_inverted: bool


@dataclass(frozen=True)
class DrawResult:
    spread_code: str
    slots: tuple[SlotDraw, ...]


@dataclass(frozen=True)
class UserSettings:
    daily_card_broadcast: bool
    allow_inverted: bool
