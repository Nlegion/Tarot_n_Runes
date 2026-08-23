"""Application entry point."""

from __future__ import annotations

import asyncio
import sys

import structlog

from src.core.settings.config import Settings
from src.core.settings.constants import PROFILE_RUNES
from src.core.settings.log import setup_logging
from src.core.settings.profiles import BotProfile, runes_profile, tarot_profile
from src.infrastructure.db.migrations_runner import apply_migrations
from src.infrastructure.db.repositories.rune_repo import RuneRepository
from src.infrastructure.db.seed import seed_database
from src.infrastructure.db.session import close_engine, health_check, session_scope
from src.infrastructure.imaging.composer import ImageComposer
from src.infrastructure.imaging.rune_composer import RuneImageComposer
from src.infrastructure.llm.deepseek_backend import DeepSeekBackend
from src.infrastructure.scheduler.daily_scheduler import DailyScheduler
from src.infrastructure.telegram.client import TelegramClient
from src.infrastructure.telegram.messenger import TelegramMessenger
from src.infrastructure.telegram.poller import TelegramPoller
from src.presentation.handlers import UpdateHandler

logger = structlog.get_logger()


async def _build_images(profile: BotProfile):
    if profile.kind == PROFILE_RUNES:
        async with session_scope() as session:
            glyphs = await RuneRepository(session).list_glyph_map()
        return RuneImageComposer(glyphs=glyphs, font_path=profile.font_path)
    return ImageComposer(images_dir=profile.images_dir)


async def _start_stack(
    *,
    profile: BotProfile,
    llm: DeepSeekBackend,
) -> tuple[TelegramPoller, DailyScheduler, TelegramMessenger]:
    images = await _build_images(profile)
    non_invertible: frozenset[int] | None = None
    if profile.kind == PROFILE_RUNES:
        async with session_scope() as session:
            non_invertible = await RuneRepository(session).list_non_invertible_ids()
    tg_client = TelegramClient(token=profile.token)
    messenger = TelegramMessenger(tg_client)
    handler = UpdateHandler(
        profile=profile,
        llm=llm,
        messenger=messenger,
        images=images,
        non_invertible_ids=non_invertible,
    )
    poller = TelegramPoller(client=tg_client, handler=handler)
    scheduler = DailyScheduler(
        profile=profile,
        llm=llm,
        messenger=messenger,
        images=images,
        non_invertible_ids=non_invertible,
    )
    return poller, scheduler, messenger


def _profiles_for_mode() -> list[BotProfile]:
    mode = Settings.BOT_MODE
    profiles: list[BotProfile] = []
    if mode in {"all", "tarot"}:
        tarot = tarot_profile()
        if tarot is not None:
            profiles.append(tarot)
        elif mode == "tarot":
            raise ValueError("TELEGRAM_BOT_TOKEN_TAROT is required for BOT_MODE=tarot")
    if mode in {"all", "runes"}:
        runes = runes_profile()
        if runes is not None:
            profiles.append(runes)
        elif mode == "runes":
            raise ValueError("TELEGRAM_BOT_TOKEN_RUNES is required for BOT_MODE=runes")
    if not profiles:
        raise ValueError("No bot profiles configured for the selected BOT_MODE")
    return profiles


async def async_main() -> None:
    async with session_scope() as session:
        await seed_database(session)
    await health_check()

    profiles = _profiles_for_mode()
    profile_kinds = [profile.kind for profile in profiles]
    logger.info(
        "bot_startup",
        bot_mode=Settings.BOT_MODE,
        profiles=profile_kinds,
    )
    llm = DeepSeekBackend()
    stacks: list[tuple[TelegramPoller, DailyScheduler, TelegramMessenger]] = []
    tasks: list[asyncio.Task] = []

    for profile in profiles:
        logger.info("bot_stack_starting", profile=profile.kind)
        poller, scheduler, messenger = await _start_stack(profile=profile, llm=llm)
        stacks.append((poller, scheduler, messenger))
        tasks.append(asyncio.create_task(poller.run(), name=f"{profile.kind}_poller"))
        tasks.append(
            asyncio.create_task(scheduler.run(), name=f"{profile.kind}_scheduler")
        )
        logger.info("bot_stack_started", profile=profile.kind)

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        for poller, scheduler, _messenger in stacks:
            poller.stop()
            scheduler.stop()
        for task in tasks:
            task.cancel()
        await llm.close()
        for _, __, messenger in stacks:
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
