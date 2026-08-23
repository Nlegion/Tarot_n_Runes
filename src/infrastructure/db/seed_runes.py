"""Seed runes and rune spreads from CSV."""

from __future__ import annotations

import csv
import hashlib

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings.config import RUNES_CSV_PATH
from src.core.settings.constants import RUNE_DECK_SIZE, RUNE_ID_MAX, RUNE_ID_MIN
from src.domain.rune_text import preprocess_rune_row
from src.infrastructure.db.rune_models import (
    Rune,
    RunePrompt,
    RuneSpreadSlot,
    RuneSpreadType,
)

logger = structlog.get_logger()

_PROMPTS = {
    "single": {
        "name": "1 руна",
        "description": "Разовый расклад на одну руну",
        "slots": [("T1", 0)],
        "system": (
            "Ты опытный рунический практик. Дай толкование одной руны.\n"
            "Формат: 3–4 коротких абзаца через пустую строку, до 800 символов. "
            "Без markdown и списков. Пиши по-русски, живо и по делу."
        ),
        "user": (
            "Расклад: 1 руна.\n"
            "Руна: {card_name} ({orig_name}), положение: {orientation}.\n"
            "Значение руны:\n{meaning}\n\n"
            "Дай персональное толкование для вопрошающего."
        ),
    },
    "three": {
        "name": "3 руны",
        "description": "Прошлое — настоящее — будущее",
        "slots": [("PAST", 0), ("PRESENT", 1), ("FUTURE", 2)],
        "system": (
            "Ты опытный рунический практик. Интерпретируй расклад "
            "«Прошлое — настоящее — будущее».\n"
            "Формат: 4 абзаца через пустую строку, до 1600 символов. "
            "Каждый абзац начинай с метки «Прошлое:», «Настоящее:», «Будущее:» "
            "и текстом секции в том же абзаце (не выноси метки отдельными строками); "
            "опционально «Вывод:». "
            "Без markdown и списков. Пиши по-русски."
        ),
        "user": (
            "Расклад: Прошлое — настоящее — будущее.\n"
            "{slots_block}\n\n"
            "Дай толкование с обязательными секциями Прошлое, Настоящее и Будущее."
        ),
    },
    "daily": {
        "name": "Руна дня",
        "description": "Одна руна на день",
        "slots": [("T1", 0)],
        "system": (
            "Ты опытный рунический практик. Дай толкование руны дня.\n"
            "Формат: 2–3 коротких абзаца через пустую строку, до 550 символов. "
            "Напутствие на день. Без markdown и списков. Пиши по-русски."
        ),
        "user": (
            "Руна дня: {card_name} ({orig_name}), положение: {orientation}.\n"
            "Значение:\n{meaning}\n\n"
            "Дай толкование как руну дня."
        ),
    },
}


def _row_checksum(row: dict[str, str]) -> str:
    payload = "|".join(
        row.get(key, "")
        for key in (
            "id",
            "name",
            "orig_name",
            "Unicode",
            "straight_position",
            "inverted_position",
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def seed_runes(session: AsyncSession) -> None:
    await _seed_rune_rows(session)
    await _seed_rune_spreads(session)
    logger.info("rune_seed_complete")


async def _seed_rune_rows(session: AsyncSession) -> None:
    if not RUNES_CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {RUNES_CSV_PATH}")
    with RUNES_CSV_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != RUNE_DECK_SIZE:
        raise ValueError(f"Expected {RUNE_DECK_SIZE} runes, got {len(rows)}")
    for raw in rows:
        rune_id = int(raw["id"])
        if rune_id < RUNE_ID_MIN or rune_id > RUNE_ID_MAX:
            raise ValueError(f"Invalid rune id: {rune_id}")
        checksum = _row_checksum(raw)
        existing = await session.get(Rune, rune_id)
        if existing is not None and existing.source_checksum == checksum:
            continue
        cleaned = preprocess_rune_row(
            name=raw["name"],
            orig_name=raw["orig_name"],
            unicode_raw=raw.get("Unicode"),
            straight_position=raw["straight_position"],
            inverted_position=raw.get("inverted_position") or "",
        )
        if existing is None:
            session.add(Rune(id=rune_id, source_checksum=checksum, **cleaned))
        else:
            existing.name = cleaned["name"]
            existing.orig_name = cleaned["orig_name"]
            existing.unicode = cleaned["unicode"]
            existing.straight_position = cleaned["straight_position"]
            existing.inverted_position = cleaned["inverted_position"]
            existing.can_invert = cleaned["can_invert"]
            existing.source_checksum = checksum
    await session.flush()


async def _seed_rune_spreads(session: AsyncSession) -> None:
    for code, meta in _PROMPTS.items():
        result = await session.execute(
            select(RuneSpreadType).where(RuneSpreadType.code == code)
        )
        spread = result.scalar_one_or_none()
        if spread is None:
            spread = RuneSpreadType(
                code=code,
                slot_count=len(meta["slots"]),
                name=meta["name"],
                description=meta["description"],
            )
            session.add(spread)
            await session.flush()
            for slot_code, slot_index in meta["slots"]:
                session.add(
                    RuneSpreadSlot(
                        spread_type_id=spread.id,
                        slot_index=slot_index,
                        code=slot_code,
                    )
                )
            session.add(
                RunePrompt(
                    spread_type_id=spread.id,
                    version=1,
                    system_template=meta["system"],
                    user_template=meta["user"],
                    is_active=True,
                )
            )
            continue
        prompt_result = await session.execute(
            select(RunePrompt).where(
                RunePrompt.spread_type_id == spread.id,
                RunePrompt.is_active.is_(True),
            )
        )
        prompt = prompt_result.scalar_one_or_none()
        if prompt is None:
            continue
        if (
            prompt.system_template != meta["system"]
            or prompt.user_template != meta["user"]
        ):
            prompt.system_template = meta["system"]
            prompt.user_template = meta["user"]
    await session.flush()
