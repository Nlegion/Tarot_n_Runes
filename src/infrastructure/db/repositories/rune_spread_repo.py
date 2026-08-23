"""Rune spread and prompt repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.rune_models import RunePrompt, RuneSpreadSlot, RuneSpreadType


class RuneSpreadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_spread_type_id(self, code: str) -> int:
        result = await self._session.execute(
            select(RuneSpreadType.id).where(RuneSpreadType.code == code)
        )
        spread_id = result.scalar_one_or_none()
        if spread_id is None:
            raise ValueError(f"Rune spread type not found: {code}")
        return spread_id

    async def get_active_prompt(self, spread_type_id: int) -> dict:
        result = await self._session.execute(
            select(RunePrompt).where(
                RunePrompt.spread_type_id == spread_type_id,
                RunePrompt.is_active.is_(True),
            )
        )
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise ValueError(f"No active rune prompt for spread {spread_type_id}")
        return {
            "id": prompt.id,
            "system_template": prompt.system_template,
            "user_template": prompt.user_template,
        }

    async def get_slot_id_map(self, spread_type_id: int) -> dict[str, int]:
        result = await self._session.execute(
            select(RuneSpreadSlot).where(
                RuneSpreadSlot.spread_type_id == spread_type_id
            )
        )
        return {row.code: row.id for row in result.scalars()}
