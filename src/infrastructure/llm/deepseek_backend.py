"""DeepSeek LLM backend."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter

import aiohttp
import structlog

from src.application.dto import GenerationRequest, GenerationResponse
from src.core.settings.config import Settings
from src.core.settings.constants import (
    LLM_CONNECT_TIMEOUT,
    LLM_MAX_RETRIES,
    LLM_TOTAL_TIMEOUT,
)

logger = structlog.get_logger()
_semaphore = asyncio.Semaphore(5)


@dataclass(frozen=True)
class BackendConfig:
    model_name: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 1500
    thinking_mode: str = "disabled"


class DeepSeekBackend:
    def __init__(
        self,
        *,
        server_url: str | None = None,
        api_key: str | None = None,
        backend_config: BackendConfig | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.server_url = (server_url or Settings.GENERATION_SERVER_URL).rstrip("/")
        key = api_key or Settings.DEEPSEEK_API_KEY
        if not key:
            raise ValueError("DEEPSEEK_API_KEY is required")
        self.api_key = key
        self.backend_config = backend_config or BackendConfig(
            model_name=Settings.LLM_MODEL_NAME
        )
        self.session = session
        self._owns_session = session is None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self.session is None:
            timeout = aiohttp.ClientTimeout(
                total=LLM_TOTAL_TIMEOUT, sock_connect=LLM_CONNECT_TIMEOUT
            )
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self) -> None:
        if self._owns_session and self.session is not None:
            await self.session.close()
            self.session = None

    def _build_payload(
        self, request: GenerationRequest, *, include_thinking: bool
    ) -> dict:
        payload: dict = {
            "model": self.backend_config.model_name,
            "messages": request.messages,
            "temperature": self.backend_config.temperature,
            "top_p": self.backend_config.top_p,
            "max_tokens": self.backend_config.max_tokens,
            "stream": False,
        }
        if include_thinking and self.backend_config.thinking_mode == "enabled":
            payload["thinking"] = {"type": "enabled"}
        return payload

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        async with _semaphore:
            return await self._generate_with_retry(
                request=request, include_thinking=True
            )

    async def _generate_with_retry(
        self, *, request: GenerationRequest, include_thinking: bool
    ) -> GenerationResponse:
        last_error: Exception | None = None
        for attempt in range(LLM_MAX_RETRIES):
            try:
                return await self._call_api(
                    request=request, include_thinking=include_thinking
                )
            except RuntimeError as exc:
                last_error = exc
                message = str(exc)
                if "HTTP 400" in message and include_thinking:
                    return await self._call_api(request=request, include_thinking=False)
                if any(
                    code in message
                    for code in ("HTTP 400", "HTTP 401", "HTTP 402", "HTTP 422")
                ):
                    raise
                if attempt + 1 >= LLM_MAX_RETRIES:
                    raise
                await asyncio.sleep(2**attempt)
        raise last_error or RuntimeError("LLM request failed")

    async def _call_api(
        self, *, request: GenerationRequest, include_thinking: bool
    ) -> GenerationResponse:
        session = await self._ensure_session()
        payload = self._build_payload(request, include_thinking=include_thinking)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        started = perf_counter()
        async with session.post(
            f"{self.server_url}/chat/completions",
            json=payload,
            headers=headers,
        ) as response:
            body = await response.text()
            if response.status != 200:
                raise RuntimeError(
                    f"chat completions failed: HTTP {response.status}: {body[:300]}"
                )
            result = await response.json()
        latency_ms = int((perf_counter() - started) * 1000)
        choices = result.get("choices") or []
        if not choices:
            raise RuntimeError("chat completions response has empty choices")
        choice = choices[0]
        text = str(choice.get("message", {}).get("content", "")).strip()
        finish_reason = choice.get("finish_reason")
        return GenerationResponse(
            text=text,
            model_name=self.backend_config.model_name,
            latency_ms=latency_ms,
            finish_reason=str(finish_reason) if finish_reason is not None else None,
        )
