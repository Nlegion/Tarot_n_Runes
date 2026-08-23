"""Rune catalog repository (implements CardRepositoryPort)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Card as CardEntity
from src.infrastructure.db.rune_models import Rune


class RuneRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, card_id: int) -> CardEntity | None:
        row = await self._session.get(Rune, card_id)
        if row is None:
            return None
        return self._to_entity(row)

    async def list_all(self) -> list[CardEntity]:
        result = await self._session.execute(select(Rune).order_by(Rune.id))
        return [self._to_entity(row) for row in result.scalars()]

    async def list_glyph_map(self) -> dict[int, str | None]:
        result = await self._session.execute(select(Rune.id, Rune.unicode))
        return {row.id: row.unicode for row in result.all()}

    async def list_non_invertible_ids(self) -> frozenset[int]:
        result = await self._session.execute(
            select(Rune.id).where(Rune.can_invert.is_(False))
        )
        return frozenset(result.scalars())

    @staticmethod
    def _to_entity(row: Rune) -> CardEntity:
        return CardEntity(
            id=row.id,
            name=row.name,
            orig_name=row.orig_name,
            straight_position=row.straight_position,
            inverted_position=row.inverted_position,
        )
