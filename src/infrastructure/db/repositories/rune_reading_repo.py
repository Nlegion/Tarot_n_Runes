"""Rune reading repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.settings.constants import READING_STATUS_PENDING
from src.domain.entities import SlotDraw
from src.infrastructure.db.rune_models import RuneReading, RuneReadingSlot


class RuneReadingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_reading_with_slots(
        self,
        *,
        user_id: int,
        spread_type_id: int,
        prompt_id: int,
        slots: tuple[SlotDraw, ...],
        slot_id_map: dict[str, int],
    ) -> int:
        reading = RuneReading(
            user_id=user_id,
            spread_type_id=spread_type_id,
            prompt_id=prompt_id,
            status=READING_STATUS_PENDING,
        )
        self._session.add(reading)
        await self._session.flush()
        for slot in slots:
            spread_slot_id = slot_id_map[slot.slot_code]
            self._session.add(
                RuneReadingSlot(
                    reading_id=reading.id,
                    spread_slot_id=spread_slot_id,
                    rune_id=slot.card_id,
                    is_inverted=slot.is_inverted,
                )
            )
        await self._session.flush()
        return reading.id

    async def save_interpretation(
        self,
        *,
        reading_id: int,
        status: str,
        raw_llm_text: str,
        raw_llm_text_repair: str | None,
        interpretation: str,
    ) -> None:
        reading = await self._session.get(RuneReading, reading_id)
        if reading is None:
            raise ValueError(f"RuneReading {reading_id} not found")
        reading.status = status
        reading.raw_llm_text = raw_llm_text
        reading.raw_llm_text_repair = raw_llm_text_repair
        reading.interpretation = interpretation
        await self._session.flush()

    async def reset_for_reinterpretation(self, *, reading_id: int) -> None:
        reading = await self._session.get(RuneReading, reading_id)
        if reading is None:
            raise ValueError(f"RuneReading {reading_id} not found")
        reading.status = READING_STATUS_PENDING
        reading.interpretation = None
        await self._session.flush()

    async def get_reading(self, reading_id: int) -> dict | None:
        result = await self._session.execute(
            select(RuneReading)
            .options(selectinload(RuneReading.slots))
            .where(RuneReading.id == reading_id)
        )
        reading = result.scalar_one_or_none()
        if reading is None:
            return None
        return {
            "id": reading.id,
            "user_id": reading.user_id,
            "spread_type_id": reading.spread_type_id,
            "status": reading.status,
            "interpretation": reading.interpretation,
            "slots": [
                {
                    "card_id": slot.rune_id,
                    "is_inverted": slot.is_inverted,
                    "spread_slot_id": slot.spread_slot_id,
                }
                for slot in reading.slots
            ],
        }
