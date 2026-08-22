"""Telegram API client."""

from __future__ import annotations

import asyncio

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.settings.config import Settings
from src.core.settings.constants import TELEGRAM_MAX_RETRIES

logger = structlog.get_logger()


class TelegramApiError(Exception):
    def __init__(self, message: str, *, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class TelegramClient:
    def __init__(self, *, token: str | None = None) -> None:
        resolved = token if token is not None else Settings.TELEGRAM_BOT_TOKEN
        if not resolved:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        self.token = resolved
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        kwargs: dict = {"timeout": 30.0, "trust_env": False}
        if Settings.TELEGRAM_PROXY_URL:
            kwargs["proxy"] = Settings.TELEGRAM_PROXY_URL
        self._client = httpx.AsyncClient(**kwargs)

    async def close(self) -> None:
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(TELEGRAM_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, TelegramApiError)),
        reraise=True,
    )
    async def request(
        self,
        method: str,
        *,
        json: dict | None = None,
        data: dict | None = None,
        files: dict | None = None,
    ) -> dict:
        response = await self._client.post(
            f"{self.base_url}/{method}",
            json=json,
            data=data,
            files=files,
        )
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "5"))
            await asyncio.sleep(retry_after)
            raise TelegramApiError("Rate limited", retry_after=retry_after)
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            description = payload.get("description", "Unknown Telegram error")
            params = payload.get("parameters") or {}
            retry_after = params.get("retry_after")
            if retry_after:
                await asyncio.sleep(int(retry_after))
                raise TelegramApiError(description, retry_after=int(retry_after))
            raise TelegramApiError(description)
        return payload
