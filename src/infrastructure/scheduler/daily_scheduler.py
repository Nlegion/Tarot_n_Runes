"""Daily broadcast scheduler (profile-aware)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import structlog

from src.application.wiring import (
    build_daily_repo,
    build_reading_service,
    build_user_repo,
)
from src.core.settings.config import Settings
from src.core.settings.constants import DAILY_BATCH_SIZE, DELIVERY_FAILED, DELIVERY_SENT
from src.core.settings.profiles import BotProfile
from src.infrastructure.db.session import session_scope
from src.infrastructure.llm.deepseek_backend import DeepSeekBackend
from src.infrastructure.telegram.client import TelegramApiError
from src.infrastructure.telegram.messenger import TelegramMessenger

logger = structlog.get_logger()


class DailyScheduler:
    def __init__(
        self,
        *,
        profile: BotProfile,
        llm: DeepSeekBackend,
        messenger: TelegramMessenger,
        images,
        non_invertible_ids: frozenset[int] | None = None,
        tz_name: str | None = None,
    ) -> None:
        self._profile = profile
        self._llm = llm
        self._messenger = messenger
        self._images = images
        self._non_invertible_ids = non_invertible_ids
        self._tz = ZoneInfo(tz_name or Settings.TIMEZONE)
        self._running = False
        self._last_midnight: datetime | None = None

    def stop(self) -> None:
        self._running = False

    async def run(self) -> None:
        self._running = True
        while self._running:
            await self._maybe_run_midnight()
            await self._deliver_pending()
            await asyncio.sleep(60)

    async def _maybe_run_midnight(self) -> None:
        now = datetime.now(self._tz)
        if now.hour != 0 or now.minute > 1:
            return
        if self._last_midnight and self._last_midnight.date() == now.date():
            return
        self._last_midnight = now
        today = now.date()
        async with session_scope() as session:
            daily = build_daily_repo(session, profile=self._profile)
            user_ids = await daily.list_broadcast_users()
        for user_id in user_ids:
            async with session_scope() as session:
                users = build_user_repo(session, profile=self._profile)
                telegram_id = await users.get_telegram_id(user_id)
                if telegram_id is None:
                    continue
                readings = await build_reading_service(
                    session,
                    profile=self._profile,
                    llm=self._llm,
                    messenger=self._messenger,
                    images=self._images,
                    non_invertible_ids=self._non_invertible_ids,
                )
                try:
                    await readings.perform_daily(
                        user_id=user_id,
                        telegram_chat_id=telegram_id,
                        card_date=today,
                        for_broadcast=True,
                    )
                except Exception as exc:
                    logger.exception(
                        "daily_broadcast_failed",
                        profile=self._profile.kind,
                        user_id=user_id,
                        error=str(exc),
                    )

    async def _deliver_pending(self) -> None:
        async with session_scope() as session:
            daily = build_daily_repo(session, profile=self._profile)
            pending = await daily.list_pending_deliveries(limit=DAILY_BATCH_SIZE)
        for item in pending:
            async with session_scope() as session:
                daily = build_daily_repo(session, profile=self._profile)
                users = build_user_repo(session, profile=self._profile)
                readings = await build_reading_service(
                    session,
                    profile=self._profile,
                    llm=self._llm,
                    messenger=self._messenger,
                    images=self._images,
                    non_invertible_ids=self._non_invertible_ids,
                )
                try:
                    await readings.deliver_existing_daily(
                        reading_id=item["reading_id"],
                        telegram_chat_id=item["telegram_id"],
                    )
                    await daily.mark_delivery(
                        daily_id=item["daily_id"],
                        status=DELIVERY_SENT,
                        attempt_count=item["attempt_count"] + 1,
                        next_attempt_at=None,
                        last_error=None,
                    )
                except TelegramApiError as exc:
                    message = str(exc).lower()
                    if "403" in message or "blocked" in message:
                        await users.disable_broadcast(user_id=item["user_id"])
                        status = DELIVERY_FAILED
                        next_attempt = None
                    else:
                        status = "pending"
                        next_attempt = datetime.utcnow() + timedelta(minutes=5)
                    await daily.mark_delivery(
                        daily_id=item["daily_id"],
                        status=status,
                        attempt_count=item["attempt_count"] + 1,
                        next_attempt_at=next_attempt,
                        last_error=str(exc),
                    )
                except httpx.RequestError as exc:
                    logger.warning(
                        "daily_delivery_request_error",
                        profile=self._profile.kind,
                        daily_id=item["daily_id"],
                        error=str(exc),
                    )
                    await daily.mark_delivery(
                        daily_id=item["daily_id"],
                        status="pending",
                        attempt_count=item["attempt_count"] + 1,
                        next_attempt_at=datetime.utcnow() + timedelta(minutes=5),
                        last_error=str(exc),
                    )
