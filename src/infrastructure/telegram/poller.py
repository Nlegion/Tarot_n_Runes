"""Telegram long-poll loop."""

from __future__ import annotations

import asyncio

import httpx
import structlog

from src.infrastructure.telegram.client import TelegramClient

logger = structlog.get_logger()


class TelegramPoller:
    def __init__(
        self,
        *,
        client: TelegramClient,
        handler,
        poll_timeout: int = 30,
    ) -> None:
        self._client = client
        self._handler = handler
        self._poll_timeout = poll_timeout
        self._offset: int | None = None
        self._running = False

    async def run(self) -> None:
        self._running = True
        await self._client.request(
            "deleteWebhook", json={"drop_pending_updates": False}
        )
        while self._running:
            params: dict = {
                "timeout": self._poll_timeout,
                "allowed_updates": ["message", "callback_query"],
            }
            if self._offset is not None:
                params["offset"] = self._offset
            try:
                payload = await self._client.request("getUpdates", json=params)
            except httpx.ConnectError as exc:
                logger.warning("telegram_poll_connect_error", error=str(exc))
                await asyncio.sleep(5)
                continue
            for update in payload.get("result", []):
                update_id = update["update_id"]
                try:
                    await self._handler(update)
                except Exception as exc:
                    logger.exception(
                        "update_handler_failed", update_id=update_id, error=str(exc)
                    )
                self._offset = update_id + 1

    def stop(self) -> None:
        self._running = False
