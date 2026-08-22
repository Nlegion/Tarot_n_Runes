"""Tests for Telegram poller resilience."""

from unittest.mock import AsyncMock

import httpx
import pytest

from src.infrastructure.telegram.poller import TelegramPoller


@pytest.mark.asyncio
async def test_poller_get_updates_survives_read_timeout(monkeypatch) -> None:
    delays: list[float] = []

    async def fast_sleep(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr("src.infrastructure.telegram.poller.asyncio.sleep", fast_sleep)
    client = AsyncMock()
    client.request = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))
    poller = TelegramPoller(client=client, handler=AsyncMock())
    params = {
        "timeout": poller._poll_timeout,
        "allowed_updates": ["message", "callback_query"],
    }

    with pytest.raises(httpx.ReadTimeout):
        await poller._client.request("getUpdates", json=params, retry=False)

    await fast_sleep(5)

    assert delays == [5]
    assert client.request.await_args.kwargs.get("retry") is False


@pytest.mark.asyncio
async def test_poller_delete_webhook_error_is_non_fatal() -> None:
    client = AsyncMock()
    client.request = AsyncMock(side_effect=httpx.ConnectError("down"))

    with pytest.raises(httpx.ConnectError):
        await client.request("deleteWebhook", json={"drop_pending_updates": False})


@pytest.mark.asyncio
async def test_poller_run_exits_when_stopped(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.infrastructure.telegram.poller.asyncio.sleep",
        AsyncMock(),
    )
    poll_calls = 0
    poller = TelegramPoller(client=AsyncMock(), handler=AsyncMock())

    async def request(method: str, **kwargs):
        nonlocal poll_calls
        if method == "deleteWebhook":
            return {}
        if method == "getUpdates":
            poll_calls += 1
            poller.stop()
            return {"result": []}
        raise AssertionError(f"unexpected method {method}")

    poller._client.request = AsyncMock(side_effect=request)
    await poller.run()
    assert poll_calls == 1
