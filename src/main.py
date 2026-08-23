"""Application entry point."""

from __future__ import annotations

import asyncio
import sys

import structlog

from src.core.settings.config import Settings
from src.core.settings.log import setup_logging
from src.core.settings.profiles import tarot_profile
from src.infrastructure.db.migrations_runner import apply_migrations
from src.infrastructure.db.seed import seed_database
from src.infrastructure.db.session import close_engine, health_check, session_scope
from src.infrastructure.imaging.composer import ImageComposer
from src.infrastructure.llm.deepseek_backend import DeepSeekBackend
from src.infrastructure.scheduler.daily_scheduler import DailyScheduler
from src.infrastructure.telegram.client import TelegramClient
from src.infrastructure.telegram.messenger import TelegramMessenger
from src.infrastructure.telegram.poller import TelegramPoller
from src.presentation.handlers import UpdateHandler

logger = structlog.get_logger()


async def async_main() -> None:
    async with session_scope() as session:
        await seed_database(session)
    await health_check()

    profile = tarot_profile()
    logger.info(
        "bot_startup",
        runes_token_configured=bool(Settings.TELEGRAM_BOT_TOKEN_RUNES),
    )
    llm = DeepSeekBackend()
    tg_client = TelegramClient(token=profile.token)
    messenger = TelegramMessenger(tg_client)
    images = ImageComposer(images_dir=profile.images_dir)
    handler = UpdateHandler(llm=llm, messenger=messenger, images=images)
    poller = TelegramPoller(client=tg_client, handler=handler)
    scheduler = DailyScheduler(llm=llm, messenger=messenger, images=images)

    poller_task = asyncio.create_task(poller.run(), name="telegram_poller")
    scheduler_task = asyncio.create_task(scheduler.run(), name="daily_scheduler")
    try:
        await asyncio.gather(poller_task, scheduler_task)
    except asyncio.CancelledError:
        pass
    finally:
        poller.stop()
        scheduler.stop()
        poller_task.cancel()
        scheduler_task.cancel()
        await llm.close()
        await messenger.close()
        await close_engine()


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    setup_logging()
    Settings.validate_startup()
    apply_migrations()
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
