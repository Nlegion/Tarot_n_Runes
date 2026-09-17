"""Daily reading repository."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings.constants import DELIVERY_PENDING
from src.domain.entities import SlotDraw
from src.infrastructure.db.models import DailyReading, User, UserSettings, utc_now
from src.infrastructure.db.repositories.reading_repo import ReadingRepository


class DailyReadingRepository:
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
        reading_repo = ReadingRepository(self._session)
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
                    DailyReading(
                        user_id=user_id,
                        card_date=card_date,
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
            select(DailyReading.reading_id).where(
                DailyReading.user_id == user_id,
                DailyReading.card_date == card_date,
            )
        )
        return result.scalar_one_or_none()

    async def get_daily_row(
        self, *, user_id: int, card_date: date
    ) -> DailyReading | None:
        result = await self._session.execute(
            select(DailyReading).where(
                DailyReading.user_id == user_id,
                DailyReading.card_date == card_date,
            )
        )
        return result.scalar_one_or_none()

    async def get_daily_state(self, *, user_id: int, card_date: date) -> dict | None:
        daily = await self.get_daily_row(user_id=user_id, card_date=card_date)
        if daily is None:
            return None
        return {
            "daily_id": daily.id,
            "reading_id": daily.reading_id,
            "attempt_count": daily.attempt_count,
            "next_attempt_at": daily.next_attempt_at,
            "last_error": daily.last_error,
            "delivery_status": daily.delivery_status,
        }

    async def mark_interpretation_attempt(
        self,
        *,
        user_id: int,
        card_date: date,
        attempt_count: int,
        next_attempt_at: datetime | None,
        last_error: str | None,
    ) -> None:
        daily = await self.get_daily_row(user_id=user_id, card_date=card_date)
        if daily is None:
            raise ValueError(
                f"DailyReading not found for user={user_id} date={card_date}"
            )
        daily.attempt_count = attempt_count
        daily.next_attempt_at = next_attempt_at
        daily.last_error = last_error
        await self._session.flush()

    async def replace_daily_reading(
        self,
        *,
        user_id: int,
        card_date: date,
        spread_type_id: int,
        prompt_id: int,
        slots: tuple[SlotDraw, ...],
        slot_id_map: dict[str, int],
    ) -> int:
        daily = await self.get_daily_row(user_id=user_id, card_date=card_date)
        if daily is None:
            raise ValueError(
                f"DailyReading not found for user={user_id} date={card_date}"
            )
        reading_repo = ReadingRepository(self._session)
        reading_id = await reading_repo.create_reading_with_slots(
            user_id=user_id,
            spread_type_id=spread_type_id,
            prompt_id=prompt_id,
            slots=slots,
            slot_id_map=slot_id_map,
        )
        daily.reading_id = reading_id
        daily.attempt_count = 0
        daily.next_attempt_at = None
        daily.last_error = None
        await self._session.flush()
        return reading_id

    async def list_pending_deliveries(self, *, limit: int) -> list[dict]:
        now = utc_now()
        result = await self._session.execute(
            select(DailyReading, User.telegram_id)
            .join(User, User.id == DailyReading.user_id)
            .where(
                DailyReading.delivery_status == DELIVERY_PENDING,
                or_(
                    DailyReading.next_attempt_at.is_(None),
                    DailyReading.next_attempt_at <= now,
                ),
            )
            .limit(limit)
        )
        return [
            {
                "daily_id": daily.id,
                "user_id": daily.user_id,
                "telegram_id": telegram_id,
                "reading_id": daily.reading_id,
                "card_date": daily.card_date,
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
        daily = await self._session.get(DailyReading, daily_id)
        if daily is None:
            raise ValueError(f"DailyReading {daily_id} not found")
        daily.delivery_status = status
        daily.attempt_count = attempt_count
        daily.next_attempt_at = next_attempt_at
        daily.last_error = last_error
        await self._session.flush()

    async def set_delivery_pending(self, *, daily_id: int) -> None:
        daily = await self._session.get(DailyReading, daily_id)
        if daily is None:
            raise ValueError(f"DailyReading {daily_id} not found")
        daily.delivery_status = DELIVERY_PENDING
        await self._session.flush()

    async def list_broadcast_users(self) -> list[int]:
        result = await self._session.execute(
            select(UserSettings.user_id).where(
                UserSettings.daily_card_broadcast.is_(True)
            )
        )
        return list(result.scalars())
