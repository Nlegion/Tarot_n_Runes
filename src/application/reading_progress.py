"""User-facing progress indicators while readings are generated."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog

from src.application.ports import MessengerPort
from src.core.settings.constants import PROCESSING_MESSAGES

logger = structlog.get_logger()
_TYPING_REFRESH_SECONDS = 4


@asynccontextmanager
async def processing_notice(
    *,
    messenger: MessengerPort,
    chat_id: int,
    spread_code: str,
):
    status_text = PROCESSING_MESSAGES.get(spread_code, "🔮 Толкую карты…")
    await messenger.send_chat_action(chat_id=chat_id, action="typing")
    status_id = await messenger.send_message(chat_id=chat_id, text=status_text)
    typing_task = asyncio.create_task(
        _refresh_typing(messenger=messenger, chat_id=chat_id),
        name="typing_indicator",
    )
    try:
        yield
    finally:
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass
        try:
            await messenger.delete_message(chat_id=chat_id, message_id=status_id)
        except Exception as exc:
            logger.warning(
                "processing_status_delete_failed",
                chat_id=chat_id,
                message_id=status_id,
                error=str(exc),
            )


async def _refresh_typing(*, messenger: MessengerPort, chat_id: int) -> None:
    while True:
        await asyncio.sleep(_TYPING_REFRESH_SECONDS)
        await messenger.send_chat_action(chat_id=chat_id, action="typing")
