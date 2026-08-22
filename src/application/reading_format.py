"""Telegram formatting for reading messages."""

from __future__ import annotations

import html

from src.core.settings.constants import SPREAD_THREE
from src.domain.entities import Card, SlotDraw

_SLOT_LABELS = {
    "PAST": "Прошлое",
    "PRESENT": "Настоящее",
    "FUTURE": "Будущее",
}


def orientation_label(*, is_inverted: bool) -> str:
    return "перевёрнутое положение" if is_inverted else "прямое положение"


def escape_html(text: str) -> str:
    return html.escape(text, quote=False)


def _card_line(*, card: Card, is_inverted: bool, label: str | None = None) -> str:
    orientation = orientation_label(is_inverted=is_inverted)
    title = f"{card.name} ({card.orig_name}) · {orientation}"
    if label:
        title = f"{label}: {title}"
    return f"<b>{escape_html(title)}</b>"


def format_reading_header(
    *,
    slots: tuple[SlotDraw, ...],
    cards: dict[int, Card],
    spread_code: str,
) -> str:
    if spread_code == SPREAD_THREE:
        lines = []
        for slot in slots:
            card = cards.get(slot.card_id)
            if card is None:
                continue
            label = _SLOT_LABELS.get(slot.slot_code, slot.slot_code)
            lines.append(
                _card_line(card=card, is_inverted=slot.is_inverted, label=label)
            )
        return "\n".join(lines)
    slot = slots[0]
    card = cards.get(slot.card_id)
    if card is None:
        return ""
    return _card_line(card=card, is_inverted=slot.is_inverted)


def format_reading_message(*, header: str, interpretation: str) -> str:
    body = escape_html(interpretation.strip())
    if not header:
        return body
    if not body:
        return header
    return f"{header}\n\n{body}"
