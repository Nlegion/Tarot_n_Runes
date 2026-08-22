"""User-facing progress indicators while readings are generated."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TypeVar

import structlog

from src.application.ports import MessengerPort
from src.core.settings.constants import (
    FOCUS_PAUSE_SECONDS,
    FOCUS_PROMPT_MESSAGE,
    INTERPRETING_MIN_VISIBLE_SECONDS,
    PROCESSING_MESSAGES,
)

logger = structlog.get_logger()
_TYPING_REFRESH_SECONDS = 4

T = TypeVar("T")


@asynccontextmanager
async def processing_notice(
    *,
    messenger: MessengerPort,
    chat_id: int,
    spread_code: str,
    with_focus_pause: bool = False,
):
    await messenger.send_chat_action(chat_id=chat_id, action="typing")
    status_id: int | None = None
    typing_task = asyncio.create_task(
        _refresh_typing(messenger=messenger, chat_id=chat_id),
        name="typing_indicator",
    )

    async def run_generation(
        coro_factory: Callable[[], Awaitable[T]],
    ) -> T:
        nonlocal status_id
        if with_focus_pause:
            status_id = await messenger.send_message(
                chat_id=chat_id,
                text=FOCUS_PROMPT_MESSAGE,
            )
            gen_task = asyncio.create_task(coro_factory(), name="llm_generate")
            await asyncio.sleep(FOCUS_PAUSE_SECONDS)
            interpreting_text = PROCESSING_MESSAGES.get(spread_code, "🔮 Толкую карты…")
            await messenger.edit_message(
                chat_id=chat_id,
                message_id=status_id,
                text=interpreting_text,
            )
            shown_at = time.monotonic()
            result = await gen_task
            visible = time.monotonic() - shown_at
            if visible < INTERPRETING_MIN_VISIBLE_SECONDS:
                await asyncio.sleep(INTERPRETING_MIN_VISIBLE_SECONDS - visible)
            return result

        status_id = await messenger.send_message(
            chat_id=chat_id,
            text=PROCESSING_MESSAGES.get(spread_code, "🔮 Толкую карты…"),
        )
        return await coro_factory()

    try:
        yield run_generation
    finally:
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass
        if status_id is not None:
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
