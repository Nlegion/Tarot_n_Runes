"""User repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import UserSettings as UserSettingsEntity
from src.infrastructure.db.models import User, UserSettings


class UserRepository:
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
            settings = UserSettings(user_id=user.id)
            self._session.add(settings)
            await self._session.flush()
            return user.id
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.language_code = language_code
        await self._session.flush()
        return user.id

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_settings(self, user_id: int) -> UserSettingsEntity:
        result = await self._session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        row = result.scalar_one()
        return UserSettingsEntity(
            daily_card_broadcast=row.daily_card_broadcast,
            allow_inverted=row.allow_inverted,
        )

    async def update_settings(
        self,
        *,
        user_id: int,
        daily_card_broadcast: bool | None = None,
        allow_inverted: bool | None = None,
    ) -> UserSettingsEntity:
        result = await self._session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        row = result.scalar_one()
        if daily_card_broadcast is not None:
            row.daily_card_broadcast = daily_card_broadcast
        if allow_inverted is not None:
            row.allow_inverted = allow_inverted
        await self._session.flush()
        return UserSettingsEntity(
            daily_card_broadcast=row.daily_card_broadcast,
            allow_inverted=row.allow_inverted,
        )

    async def disable_broadcast(self, user_id: int) -> None:
        result = await self._session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        row = result.scalar_one()
        row.daily_card_broadcast = False
        await self._session.flush()
