"""Prompt builder for tarot spreads."""

from __future__ import annotations

from src.application.dto import GenerationRequest
from src.core.settings.constants import (
    MAX_INTERPRETATION_CHARS,
    MAX_SLOT_TEXT_CHARS,
    MIN_SECTION_BODY_CHARS,
)
from src.domain.entities import Card, SlotDraw

_SLOT_LABELS = {
    "T1": "Карта",
    "PAST": "Прошлое",
    "PRESENT": "Настоящее",
    "FUTURE": "Будущее",
}


def _orientation_label(is_inverted: bool) -> str:
    return "перевёрнутое" if is_inverted else "прямое"


def _meaning(card: Card, *, is_inverted: bool) -> str:
    text = card.inverted_position if is_inverted else card.straight_position
    if len(text) > MAX_SLOT_TEXT_CHARS:
        return text[:MAX_SLOT_TEXT_CHARS].rsplit(" ", 1)[0] + "…"
    return text


def build_prompt(
    *,
    system_template: str,
    user_template: str,
    spread_code: str,
    slots: tuple[SlotDraw, ...],
    cards: dict[int, Card],
) -> GenerationRequest:
    if spread_code in ("single", "daily"):
        slot = slots[0]
        card = cards[slot.card_id]
        user_content = user_template.format(
            card_name=card.name,
            orig_name=card.orig_name,
            orientation=_orientation_label(slot.is_inverted),
            meaning=_meaning(card, is_inverted=slot.is_inverted),
        )
    else:
        blocks: list[str] = []
        for slot in slots:
            card = cards[slot.card_id]
            label = _SLOT_LABELS.get(slot.slot_code, slot.slot_code)
            blocks.append(
                f"{label}: {card.name} ({card.orig_name}), "
                f"{_orientation_label(slot.is_inverted)}.\n"
                f"{_meaning(card, is_inverted=slot.is_inverted)}"
            )
        user_content = user_template.format(slots_block="\n\n".join(blocks))
    messages = [
        {"role": "system", "content": system_template},
        {"role": "user", "content": user_content},
    ]
    return GenerationRequest(
        system_prompt=system_template,
        user_content=user_content,
        messages=messages,
    )


def build_repair_prompt(
    *,
    base: GenerationRequest,
    issues: list[str],
    spread_code: str,
) -> GenerationRequest:
    max_chars = MAX_INTERPRETATION_CHARS.get(spread_code, 650)
    if spread_code == "three":
        format_hint = (
            f"Верни толкование с обязательными абзацами «Прошлое:», «Настоящее:», "
            f"«Будущее:» и кратким «Вывод:». Метка и текст каждой секции — "
            f"в одном абзаце, не менее {MIN_SECTION_BODY_CHARS} символов на секцию. "
            f"Не более {max_chars} символов. Без markdown и списков."
        )
    else:
        format_hint = (
            f"Дай связное толкование: 3–5 коротких абзацев через пустую строку, "
            f"не более {max_chars} символов. Без markdown и списков."
        )
    feedback = (
        "Предыдущий ответ был неприемлем: " + ", ".join(issues) + ". " + format_hint
    )
    system_prompt = base.system_prompt + "\n\n" + feedback
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": base.user_content},
    ]
    return GenerationRequest(
        system_prompt=system_prompt,
        user_content=base.user_content,
        messages=messages,
    )
