"""Daily card broadcast scheduler."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import structlog

from src.application.wiring import build_reading_service
from src.core.settings.config import Settings
from src.core.settings.constants import DAILY_BATCH_SIZE, DELIVERY_FAILED, DELIVERY_SENT
from src.infrastructure.db.models import User
from src.infrastructure.db.repositories.daily_repo import DailyReadingRepository
from src.infrastructure.db.repositories.user_repo import UserRepository
from src.infrastructure.db.session import session_scope
from src.infrastructure.imaging.composer import ImageComposer
from src.infrastructure.llm.deepseek_backend import DeepSeekBackend
from src.infrastructure.telegram.client import TelegramApiError
from src.infrastructure.telegram.messenger import TelegramMessenger

logger = structlog.get_logger()


class DailyScheduler:
    def __init__(
        self,
        *,
        llm: DeepSeekBackend,
        messenger: TelegramMessenger,
        images: ImageComposer | None = None,
        tz_name: str | None = None,
    ) -> None:
        self._llm = llm
        self._messenger = messenger
        self._images = images or ImageComposer()
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
            daily_repo = DailyReadingRepository(session)
            user_ids = await daily_repo.list_broadcast_users()
        for user_id in user_ids:
            async with session_scope() as session:
                user = await session.get(User, user_id)
                if user is None:
                    continue
                readings = build_reading_service(
                    session,
                    llm=self._llm,
                    messenger=self._messenger,
                    images=self._images,
                )
                try:
                    await readings.perform_daily(
                        user_id=user_id,
                        telegram_chat_id=user.telegram_id,
                        card_date=today,
                        for_broadcast=True,
                    )
                except Exception as exc:
                    logger.exception(
                        "daily_broadcast_failed",
                        user_id=user_id,
                        error=str(exc),
                    )

    async def _deliver_pending(self) -> None:
        async with session_scope() as session:
            daily_repo = DailyReadingRepository(session)
            pending = await daily_repo.list_pending_deliveries(limit=DAILY_BATCH_SIZE)
        for item in pending:
            async with session_scope() as session:
                daily_repo = DailyReadingRepository(session)
                user_repo = UserRepository(session)
                user = await session.get(User, item["user_id"])
                if user is None:
                    continue
                readings = build_reading_service(
                    session,
                    llm=self._llm,
                    messenger=self._messenger,
                    images=self._images,
                )
                reading = await readings._readings.get_reading(item["reading_id"])
                if not reading or not reading.get("interpretation"):
                    continue
                try:
                    slots = await readings._load_slots(item["reading_id"])
                    await readings._send_existing(
                        reading_id=item["reading_id"],
                        telegram_chat_id=user.telegram_id,
                        slots=slots,
                        interpretation=reading["interpretation"],
                    )
                    await daily_repo.mark_delivery(
                        daily_id=item["daily_id"],
                        status=DELIVERY_SENT,
                        attempt_count=item["attempt_count"] + 1,
                        next_attempt_at=None,
                        last_error=None,
                    )
                except TelegramApiError as exc:
                    message = str(exc).lower()
                    if "403" in message or "blocked" in message:
                        await user_repo.disable_broadcast(user_id=item["user_id"])
                        status = DELIVERY_FAILED
                        next_attempt = None
                    else:
                        status = "pending"
                        next_attempt = datetime.utcnow() + timedelta(minutes=5)
                    await daily_repo.mark_delivery(
                        daily_id=item["daily_id"],
                        status=status,
                        attempt_count=item["attempt_count"] + 1,
                        next_attempt_at=next_attempt,
                        last_error=str(exc),
                    )
