"""Telegram long-poll loop."""

from __future__ import annotations

import asyncio

import httpx
import structlog

from src.core.settings.constants import TELEGRAM_POLL_TIMEOUT
from src.infrastructure.telegram.client import TelegramClient

logger = structlog.get_logger()


def format_network_error(exc: BaseException) -> str:
    """Build a non-empty error string for httpx/network failures."""
    parts: list[str] = [type(exc).__name__]
    message = str(exc).strip()
    if message:
        parts.append(message)
    else:
        rendered = repr(exc).strip()
        if rendered and rendered != type(exc).__name__:
            parts.append(rendered)
    request = None
    try:
        request = getattr(exc, "request", None)
    except RuntimeError:
        request = None
    if request is not None:
        method = getattr(request, "method", None)
        url = getattr(request, "url", None)
        if method or url:
            parts.append(f"{method or '?'} {url or '?'}")
    return ": ".join(parts)


class TelegramPoller:
    def __init__(
        self,
        *,
        client: TelegramClient,
        handler,
        poll_timeout: int = TELEGRAM_POLL_TIMEOUT,
    ) -> None:
        self._client = client
        self._handler = handler
        self._poll_timeout = poll_timeout
        self._offset: int | None = None
        self._running = False

    async def run(self) -> None:
        self._running = True
        try:
            await self._client.request(
                "deleteWebhook",
                json={"drop_pending_updates": False},
            )
        except httpx.RequestError as exc:
            logger.warning(
                "telegram_delete_webhook_error",
                error=format_network_error(exc),
            )
        while self._running:
            params: dict = {
                "timeout": self._poll_timeout,
                "allowed_updates": ["message", "callback_query"],
            }
            if self._offset is not None:
                params["offset"] = self._offset
            try:
                payload = await self._client.request(
                    "getUpdates",
                    json=params,
                    retry=False,
                )
            except httpx.RequestError as exc:
                logger.warning(
                    "telegram_poll_request_error",
                    error=format_network_error(exc),
                )
                await asyncio.sleep(5)
                continue
            for update in payload.get("result", []):
                update_id = update["update_id"]
                try:
                    await self._handler(update)
                except Exception as exc:
                    logger.exception(
                        "update_handler_failed",
                        update_id=update_id,
                        error=format_network_error(exc),
                    )
                self._offset = update_id + 1

    def stop(self) -> None:
        self._running = False
