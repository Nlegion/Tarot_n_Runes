"""Database seed from CSV and static prompts."""

from __future__ import annotations

import csv
import hashlib

import structlog
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings.config import CSV_PATH, IMAGES_DIR
from src.core.settings.constants import CARD_ID_MAX, CARD_ID_MIN, DECK_SIZE
from src.domain.card_text import preprocess_card_row
from src.infrastructure.db.models import Card, Prompt, SpreadSlot, SpreadType

logger = structlog.get_logger()

_PROMPTS = {
    "single": {
        "name": "1 карта",
        "description": "Разовый расклад на одну карту",
        "slots": [("T1", 0)],
        "system": (
            "Ты опытный таролог. Дай толкование одной карты.\n"
            "Формат: 3–4 коротких абзаца через пустую строку, до 600 символов. "
            "Без markdown, списков и служебных меток. Пиши по-русски, живо и по делу."
        ),
        "user": (
            "Расклад: 1 карта.\n"
            "Карта: {card_name} ({orig_name}), положение: {orientation}.\n"
            "Значение карты:\n{meaning}\n\n"
            "Дай персональное толкование для вопрошающего."
        ),
    },
    "three": {
        "name": "3 карты",
        "description": "Было — стало — будет",
        "slots": [("PAST", 0), ("PRESENT", 1), ("FUTURE", 2)],
        "system": (
            "Ты опытный таролог. Интерпретируй расклад «Было — стало — будет».\n"
            "Формат: 4–5 абзацев через пустую строку, до 900 символов. "
            "Отдельно про прошлое, настоящее и будущее, затем общий вывод. "
            "Без markdown и служебных меток. Пиши по-русски."
        ),
        "user": (
            "Расклад: Было — стало — будет.\n"
            "{slots_block}\n\n"
            "Дай цельное толкование прошлого, настоящего и будущего."
        ),
    },
    "daily": {
        "name": "Карта дня",
        "description": "Одна карта на день",
        "slots": [("T1", 0)],
        "system": (
            "Ты опытный таролог. Дай толкование карты дня.\n"
            "Формат: 2–3 коротких абзаца через пустую строку, до 400 символов. "
            "Напутствие на день. Без markdown и служебных меток. Пиши по-русски."
        ),
        "user": (
            "Карта дня: {card_name} ({orig_name}), положение: {orientation}.\n"
            "Значение:\n{meaning}\n\n"
            "Дай толкование как карту дня."
        ),
    },
}


def _row_checksum(row: dict[str, str]) -> str:
    payload = "|".join(
        row.get(key, "")
        for key in ("id", "name", "orig_name", "straight_position", "inverted_position")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_jpeg(card_id: int) -> None:
    path = IMAGES_DIR / f"{card_id}.jpg"
    if not path.exists():
        raise ValueError(f"Missing image: {path}")
    with Image.open(path) as img:
        img.verify()


async def seed_database(session: AsyncSession) -> None:
    await _seed_cards(session)
    await _seed_spreads(session)
    logger.info("seed_complete")


async def _seed_cards(session: AsyncSession) -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if len(rows) != DECK_SIZE:
        raise ValueError(f"Expected {DECK_SIZE} cards, got {len(rows)}")
    for raw in rows:
        card_id = int(raw["id"])
        if card_id < CARD_ID_MIN or card_id > CARD_ID_MAX:
            raise ValueError(f"Invalid card id: {card_id}")
        _validate_jpeg(card_id)
        checksum = _row_checksum(raw)
        existing = await session.get(Card, card_id)
        if existing is not None and existing.source_checksum == checksum:
            continue
        cleaned = preprocess_card_row(
            name=raw["name"],
            orig_name=raw["orig_name"],
            straight_position=raw["straight_position"],
            inverted_position=raw["inverted_position"],
        )
        if existing is None:
            session.add(
                Card(
                    id=card_id,
                    source_checksum=checksum,
                    **cleaned,
                )
            )
        else:
            existing.name = cleaned["name"]
            existing.orig_name = cleaned["orig_name"]
            existing.straight_position = cleaned["straight_position"]
            existing.inverted_position = cleaned["inverted_position"]
            existing.source_checksum = checksum
    await session.flush()


async def _seed_spreads(session: AsyncSession) -> None:
    for code, meta in _PROMPTS.items():
        result = await session.execute(
            select(SpreadType).where(SpreadType.code == code)
        )
        spread = result.scalar_one_or_none()
        if spread is None:
            spread = SpreadType(
                code=code,
                slot_count=len(meta["slots"]),
                name=meta["name"],
                description=meta["description"],
            )
            session.add(spread)
            await session.flush()
            for slot_code, slot_index in meta["slots"]:
                session.add(
                    SpreadSlot(
                        spread_type_id=spread.id,
                        slot_index=slot_index,
                        code=slot_code,
                    )
                )
            session.add(
                Prompt(
                    spread_type_id=spread.id,
                    version=1,
                    system_template=meta["system"],
                    user_template=meta["user"],
                    is_active=True,
                )
            )
            continue
        prompt_result = await session.execute(
            select(Prompt).where(
                Prompt.spread_type_id == spread.id,
                Prompt.is_active.is_(True),
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
