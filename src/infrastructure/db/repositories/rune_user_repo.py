"""Rune-bot user settings (shared users table)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import UserSettings as UserSettingsEntity
from src.infrastructure.db.models import User, utc_now
from src.infrastructure.db.rune_models import RuneUserSettings


class RuneUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_from_telegram(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
    ) -> int:
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
            )
            self._session.add(user)
            await self._session.flush()
        else:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.language_code = language_code
            user.last_seen_at = utc_now()
            await self._session.flush()
        await self._ensure_settings(user.id)
        return user.id

    async def get_settings(self, user_id: int) -> UserSettingsEntity:
        row = await self._ensure_settings(user_id)
        return UserSettingsEntity(
            daily_card_broadcast=row.daily_rune_broadcast,
            allow_inverted=True,
        )

    async def update_settings(
        self,
        *,
        user_id: int,
        daily_card_broadcast: bool | None = None,
        allow_inverted: bool | None = None,
    ) -> UserSettingsEntity:
        del allow_inverted
        row = await self._ensure_settings(user_id)
        if daily_card_broadcast is not None:
            row.daily_rune_broadcast = daily_card_broadcast
        await self._session.flush()
        return UserSettingsEntity(
            daily_card_broadcast=row.daily_rune_broadcast,
            allow_inverted=True,
        )

    async def disable_broadcast(self, user_id: int) -> None:
        row = await self._ensure_settings(user_id)
        row.daily_rune_broadcast = False
        await self._session.flush()

    async def get_telegram_id(self, user_id: int) -> int | None:
        user = await self._session.get(User, user_id)
        return user.telegram_id if user is not None else None

    async def _ensure_settings(self, user_id: int) -> RuneUserSettings:
        result = await self._session.execute(
            select(RuneUserSettings).where(RuneUserSettings.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            return row
        row = RuneUserSettings(user_id=user_id)
        self._session.add(row)
        await self._session.flush()
        return row
