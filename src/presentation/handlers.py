"""Telegram update handlers."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import structlog

from src.application.wiring import build_reading_service, build_user_service
from src.core.settings.config import Settings
from src.core.settings.constants import SPREAD_SINGLE, SPREAD_THREE, WELCOME_MESSAGE
from src.core.settings.profiles import BotProfile
from src.infrastructure.db.session import session_scope
from src.infrastructure.llm.deepseek_backend import DeepSeekBackend
from src.infrastructure.telegram.messenger import TelegramMessenger
from src.presentation.keyboards import main_keyboard, settings_keyboard

logger = structlog.get_logger()


class UpdateHandler:
    def __init__(
        self,
        *,
        profile: BotProfile,
        llm: DeepSeekBackend,
        messenger: TelegramMessenger,
        images,
        non_invertible_ids: frozenset[int] | None = None,
    ) -> None:
        self._profile = profile
        self._llm = llm
        self._messenger = messenger
        self._images = images
        self._non_invertible_ids = non_invertible_ids
        self._buttons = profile.buttons

    async def __call__(self, update: dict) -> None:
        if "callback_query" in update:
            await self._handle_callback(update["callback_query"])
            return
        message = update.get("message")
        if not message:
            return
        chat = message["chat"]
        chat_id = chat["id"]
        from_user = message.get("from") or {}
        text = (message.get("text") or "").strip()
        buttons = self._buttons
        async with session_scope() as session:
            users = build_user_service(session, profile=self._profile)
            user_id = await users.register_or_touch(
                telegram_id=from_user.get("id", chat_id),
                username=from_user.get("username"),
                first_name=from_user.get("first_name"),
                last_name=from_user.get("last_name"),
                language_code=from_user.get("language_code"),
            )
            readings = await build_reading_service(
                session,
                profile=self._profile,
                llm=self._llm,
                messenger=self._messenger,
                images=self._images,
                non_invertible_ids=self._non_invertible_ids,
            )
            if text.startswith("/start"):
                await self._send_main_menu(
                    chat_id=chat_id, user_id=user_id, users=users
                )
                return
            if text == buttons.single:
                await readings.perform_spread(
                    user_id=user_id,
                    telegram_chat_id=chat_id,
                    spread_code=SPREAD_SINGLE,
                )
                return
            if text == buttons.three:
                await readings.perform_spread(
                    user_id=user_id,
                    telegram_chat_id=chat_id,
                    spread_code=SPREAD_THREE,
                )
                return
            if text == buttons.daily:
                today = datetime.now(ZoneInfo(Settings.TIMEZONE)).date()
                await readings.perform_daily(
                    user_id=user_id,
                    telegram_chat_id=chat_id,
                    card_date=today,
                    for_broadcast=False,
                )
                return
            if text == buttons.settings or text.startswith(buttons.toggle_daily):
                await self._handle_settings(
                    chat_id=chat_id,
                    user_id=user_id,
                    text=text,
                    users=users,
                )
                return
            if (
                self._profile.show_inverted_toggle
                and buttons.toggle_inverted
                and text.startswith(buttons.toggle_inverted)
            ):
                await self._handle_settings(
                    chat_id=chat_id,
                    user_id=user_id,
                    text=text,
                    users=users,
                )
                return
            if text == buttons.back:
                await self._send_main_menu(
                    chat_id=chat_id, user_id=user_id, users=users
                )
                return

    async def _handle_settings(
        self, *, chat_id: int, user_id: int, text: str, users
    ) -> None:
        buttons = self._buttons
        if text.startswith(buttons.toggle_daily):
            await users.toggle_daily_broadcast(user_id)
        elif (
            self._profile.show_inverted_toggle
            and buttons.toggle_inverted
            and text.startswith(buttons.toggle_inverted)
        ):
            await users.toggle_allow_inverted(user_id)
        settings = await users.get_settings(user_id)
        message = (
            "Параметры обновлены."
            if text.startswith(buttons.toggle_daily)
            or (
                buttons.toggle_inverted is not None
                and text.startswith(buttons.toggle_inverted)
            )
            else "Настройки:"
        )
        await self._messenger.send_message_with_keyboard(
            chat_id=chat_id,
            text=message,
            reply_markup=settings_keyboard(
                profile=self._profile,
                daily_on=settings.daily_card_broadcast,
                inverted_on=settings.allow_inverted,
            ),
        )

    async def _send_main_menu(self, *, chat_id: int, user_id: int, users) -> None:
        await users.get_settings(user_id)
        await self._messenger.send_message_with_keyboard(
            chat_id=chat_id,
            text=WELCOME_MESSAGE,
            reply_markup=main_keyboard(self._buttons),
        )

    async def _handle_callback(self, callback: dict) -> None:
        await self._messenger.answer_callback(
            callback_query_id=callback["id"],
        )
