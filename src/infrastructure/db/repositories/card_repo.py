"""Card repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Card as CardEntity
from src.infrastructure.db.models import Card


class CardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, card_id: int) -> CardEntity | None:
        row = await self._session.get(Card, card_id)
        if row is None:
            return None
        return self._to_entity(row)

    async def list_all(self) -> list[CardEntity]:
        result = await self._session.execute(select(Card).order_by(Card.id))
        return [self._to_entity(row) for row in result.scalars()]

    @staticmethod
    def _to_entity(row: Card) -> CardEntity:
        return CardEntity(
            id=row.id,
            name=row.name,
            orig_name=row.orig_name,
            straight_position=row.straight_position,
            inverted_position=row.inverted_position,
        )
