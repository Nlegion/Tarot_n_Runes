"""Spread and prompt repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models import Prompt, SpreadSlot, SpreadType


class SpreadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_spread_type_id(self, code: str) -> int:
        result = await self._session.execute(
            select(SpreadType.id).where(SpreadType.code == code)
        )
        spread_id = result.scalar_one_or_none()
        if spread_id is None:
            raise ValueError(f"Spread type not found: {code}")
        return spread_id

    async def get_active_prompt(self, spread_type_id: int) -> dict:
        result = await self._session.execute(
            select(Prompt).where(
                Prompt.spread_type_id == spread_type_id,
                Prompt.is_active.is_(True),
            )
        )
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise ValueError(f"No active prompt for spread {spread_type_id}")
        return {
            "id": prompt.id,
            "system_template": prompt.system_template,
            "user_template": prompt.user_template,
        }

    async def get_slot_id_map(self, spread_type_id: int) -> dict[str, int]:
        result = await self._session.execute(
            select(SpreadSlot).where(SpreadSlot.spread_type_id == spread_type_id)
        )
        return {row.code: row.id for row in result.scalars()}
