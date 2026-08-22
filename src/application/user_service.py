"""User registration and settings."""

from __future__ import annotations

from src.application.ports import UserRepositoryPort
from src.domain.entities import UserSettings


class UserService:
    def __init__(self, users: UserRepositoryPort) -> None:
        self._users = users

    async def register_or_touch(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
    ) -> int:
        return await self._users.upsert_from_telegram(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )

    async def get_settings(self, user_id: int) -> UserSettings:
        return await self._users.get_settings(user_id)

    async def toggle_daily_broadcast(self, user_id: int) -> UserSettings:
        current = await self._users.get_settings(user_id)
        return await self._users.update_settings(
            user_id=user_id,
            daily_card_broadcast=not current.daily_card_broadcast,
        )

    async def toggle_allow_inverted(self, user_id: int) -> UserSettings:
        current = await self._users.get_settings(user_id)
        return await self._users.update_settings(
            user_id=user_id,
            allow_inverted=not current.allow_inverted,
        )
