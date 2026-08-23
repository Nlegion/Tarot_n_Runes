"""Tests for Telegram messenger photo upload."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.infrastructure.telegram.messenger import TelegramMessenger


@pytest.mark.asyncio
async def test_send_photo_uploads_bytes() -> None:
    client = AsyncMock()
    client.request = AsyncMock(return_value={"ok": True, "result": {}})
    messenger = TelegramMessenger(client)
    photo_bytes = b"\xff\xd8\xfffake-jpeg"

    await messenger.send_photo(chat_id=42, photo_bytes=photo_bytes, caption="hi")

    client.request.assert_awaited_once()
    kwargs = client.request.await_args.kwargs
    assert kwargs["data"]["chat_id"] == "42"
    assert kwargs["data"]["caption"] == "hi"
    name, handle, content_type = kwargs["files"]["photo"]
    assert name == "reading.jpg"
    assert content_type == "image/jpeg"
    assert handle.read() == photo_bytes
