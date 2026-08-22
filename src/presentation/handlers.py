"""Telegram update handlers."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import structlog

from src.application.wiring import build_reading_service, build_user_service
from src.core.settings.config import Settings
from src.core.settings.constants import SPREAD_SINGLE, SPREAD_THREE
from src.infrastructure.db.session import session_scope
from src.infrastructure.imaging.composer import ImageComposer
from src.infrastructure.llm.deepseek_backend import DeepSeekBackend
from src.infrastructure.telegram.messenger import TelegramMessenger
from src.presentation.keyboards import (
    BTN_BACK,
    BTN_DAILY,
    BTN_SETTINGS,
    BTN_SINGLE,
    BTN_THREE,
    BTN_TOGGLE_DAILY,
    BTN_TOGGLE_INVERTED,
    main_keyboard,
    settings_keyboard,
)

logger = structlog.get_logger()


class UpdateHandler:
    def __init__(
        self,
        *,
        llm: DeepSeekBackend,
        messenger: TelegramMessenger,
        images: ImageComposer | None = None,
    ) -> None:
        self._llm = llm
        self._messenger = messenger
        self._images = images or ImageComposer()

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
        async with session_scope() as session:
            users = build_user_service(session)
            user_id = await users.register_or_touch(
                telegram_id=from_user.get("id", chat_id),
                username=from_user.get("username"),
                first_name=from_user.get("first_name"),
                last_name=from_user.get("last_name"),
                language_code=from_user.get("language_code"),
            )
            readings = build_reading_service(
                session,
                llm=self._llm,
                messenger=self._messenger,
                images=self._images,
            )
            if text.startswith("/start"):
                await self._send_main_menu(
                    chat_id=chat_id, user_id=user_id, users=users
                )
                return
            if text == BTN_SINGLE:
                await readings.perform_spread(
                    user_id=user_id,
                    telegram_chat_id=chat_id,
                    spread_code=SPREAD_SINGLE,
                )
                return
            if text == BTN_THREE:
                await readings.perform_spread(
                    user_id=user_id,
                    telegram_chat_id=chat_id,
                    spread_code=SPREAD_THREE,
                )
                return
            if text == BTN_DAILY:
                today = datetime.now(ZoneInfo(Settings.TIMEZONE)).date()
                await readings.perform_daily(
                    user_id=user_id,
                    telegram_chat_id=chat_id,
                    card_date=today,
                    for_broadcast=False,
                )
                return
            if (
                text == BTN_SETTINGS
                or text.startswith(BTN_TOGGLE_DAILY)
                or text.startswith(BTN_TOGGLE_INVERTED)
            ):
                await self._handle_settings(
                    chat_id=chat_id,
                    user_id=user_id,
                    text=text,
                    users=users,
                )
                return
            if text == BTN_BACK:
                await self._send_main_menu(
                    chat_id=chat_id, user_id=user_id, users=users
                )
                return

    async def _handle_settings(
        self, *, chat_id: int, user_id: int, text: str, users
    ) -> None:
        if text.startswith(BTN_TOGGLE_DAILY):
            await users.toggle_daily_broadcast(user_id)
        elif text.startswith(BTN_TOGGLE_INVERTED):
            await users.toggle_allow_inverted(user_id)
        settings = await users.get_settings(user_id)
        message = (
            "Параметры обновлены."
            if text.startswith(BTN_TOGGLE_DAILY) or text.startswith(BTN_TOGGLE_INVERTED)
            else "Настройки:"
        )
        await self._messenger.send_message_with_keyboard(
            chat_id=chat_id,
            text=message,
            reply_markup=settings_keyboard(
                daily_on=settings.daily_card_broadcast,
                inverted_on=settings.allow_inverted,
            ),
        )

    async def _send_main_menu(self, *, chat_id: int, user_id: int, users) -> None:
        await users.get_settings(user_id)
        await self._messenger.send_message_with_keyboard(
            chat_id=chat_id,
            text="Добро пожаловать! Выберите расклад:",
            reply_markup=main_keyboard(),
        )

    async def _handle_callback(self, callback: dict) -> None:
        await self._messenger.answer_callback(
            callback_query_id=callback["id"],
        )
