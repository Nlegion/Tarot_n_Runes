"""Rune daily reading repository."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings.constants import DELIVERY_PENDING
from src.domain.entities import SlotDraw
from src.infrastructure.db.models import User
from src.infrastructure.db.repositories.rune_reading_repo import RuneReadingRepository
from src.infrastructure.db.rune_models import RuneDailyReading, RuneUserSettings


class RuneDailyReadingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim_daily(
        self,
        *,
        user_id: int,
        card_date: date,
        spread_type_id: int,
        prompt_id: int,
        slots: tuple[SlotDraw, ...],
        slot_id_map: dict[str, int],
        delivery_status: str = "none",
    ) -> tuple[int, bool]:
        existing = await self.get_daily_reading_id(user_id=user_id, card_date=card_date)
        if existing is not None:
            return existing, False
        reading_repo = RuneReadingRepository(self._session)
        try:
            async with self._session.begin_nested():
                reading_id = await reading_repo.create_reading_with_slots(
                    user_id=user_id,
                    spread_type_id=spread_type_id,
                    prompt_id=prompt_id,
                    slots=slots,
                    slot_id_map=slot_id_map,
                )
                self._session.add(
                    RuneDailyReading(
                        user_id=user_id,
                        rune_date=card_date,
                        reading_id=reading_id,
                        delivery_status=delivery_status,
                    )
                )
                await self._session.flush()
        except IntegrityError:
            existing = await self.get_daily_reading_id(
                user_id=user_id, card_date=card_date
            )
            if existing is None:
                raise
            return existing, False
        return reading_id, True

    async def get_daily_reading_id(
        self, *, user_id: int, card_date: date
    ) -> int | None:
        result = await self._session.execute(
            select(RuneDailyReading.reading_id).where(
                RuneDailyReading.user_id == user_id,
                RuneDailyReading.rune_date == card_date,
            )
        )
        return result.scalar_one_or_none()

    async def list_pending_deliveries(self, *, limit: int) -> list[dict]:
        result = await self._session.execute(
            select(RuneDailyReading, User.telegram_id)
            .join(User, User.id == RuneDailyReading.user_id)
            .where(RuneDailyReading.delivery_status == DELIVERY_PENDING)
            .limit(limit)
        )
        return [
            {
                "daily_id": daily.id,
                "user_id": daily.user_id,
                "telegram_id": telegram_id,
                "reading_id": daily.reading_id,
                "attempt_count": daily.attempt_count,
            }
            for daily, telegram_id in result.all()
        ]

    async def mark_delivery(
        self,
        *,
        daily_id: int,
        status: str,
        attempt_count: int,
        next_attempt_at: datetime | None,
        last_error: str | None,
    ) -> None:
        daily = await self._session.get(RuneDailyReading, daily_id)
        if daily is None:
            raise ValueError(f"RuneDailyReading {daily_id} not found")
        daily.delivery_status = status
        daily.attempt_count = attempt_count
        daily.next_attempt_at = next_attempt_at
        daily.last_error = last_error
        await self._session.flush()

    async def list_broadcast_users(self) -> list[int]:
        result = await self._session.execute(
            select(RuneUserSettings.user_id).where(
                RuneUserSettings.daily_rune_broadcast.is_(True)
            )
        )
        return list(result.scalars())
