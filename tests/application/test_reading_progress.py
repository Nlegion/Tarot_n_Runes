"""Tests for reading progress notices."""

from unittest.mock import AsyncMock

import pytest

from src.application import reading_progress
from src.application.reading_progress import processing_notice
from src.core.settings.constants import (
    FOCUS_PROMPT_MESSAGE,
    SPREAD_SINGLE,
)


@pytest.fixture(autouse=True)
def fast_progress_timing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reading_progress, "FOCUS_PAUSE_SECONDS", 0.0)
    monkeypatch.setattr(reading_progress, "INTERPRETING_MIN_VISIBLE_SECONDS", 0.0)

    async def instant_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(reading_progress.asyncio, "sleep", instant_sleep)
    monkeypatch.setattr(reading_progress, "_refresh_typing", AsyncMock())


@pytest.mark.asyncio
async def test_focus_pause_starts_generation_in_parallel() -> None:
    messenger = AsyncMock()
    messenger.send_message = AsyncMock(return_value=101)
    messenger.edit_message = AsyncMock()
    messenger.delete_message = AsyncMock()
    messenger.send_chat_action = AsyncMock()
    started = False
    finished = False

    async with processing_notice(
        messenger=messenger,
        chat_id=1,
        spread_code=SPREAD_SINGLE,
        with_focus_pause=True,
    ) as run_generation:

        async def generate() -> str:
            nonlocal started, finished
            started = True
            finished = True
            return "ok"

        result = await run_generation(generate)

    assert result == "ok"
    assert started
    assert finished
    first_call = messenger.send_message.await_args_list[0]
    assert first_call.kwargs["text"] == FOCUS_PROMPT_MESSAGE
    messenger.edit_message.assert_awaited_once()
    assert "Толкую" in messenger.edit_message.await_args.kwargs["text"]


@pytest.mark.asyncio
async def test_repair_notice_skips_focus_pause() -> None:
    messenger = AsyncMock()
    messenger.send_message = AsyncMock(return_value=55)
    messenger.delete_message = AsyncMock()
    messenger.send_chat_action = AsyncMock()

    async with processing_notice(
        messenger=messenger,
        chat_id=1,
        spread_code=SPREAD_SINGLE,
        with_focus_pause=False,
    ) as run_generation:
        result = await run_generation(lambda: _return_value("done"))

    assert result == "done"
    assert messenger.send_message.await_count == 1
    assert "Толкую" in messenger.send_message.await_args.kwargs["text"]
    messenger.edit_message.assert_not_called()


async def _return_value(value: str) -> str:
    return value
