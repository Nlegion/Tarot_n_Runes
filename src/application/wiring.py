"""Application wiring helpers."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.reading_service import ReadingService
from src.application.user_service import UserService
from src.core.settings.constants import (
    PROFILE_RUNES,
    RUNE_ID_MAX,
    RUNE_ID_MIN,
)
from src.core.settings.profiles import BotProfile
from src.domain.draw_engine import TAROT_DRAW_CONFIG, DrawConfig
from src.infrastructure.db.repositories.card_repo import CardRepository
from src.infrastructure.db.repositories.daily_repo import DailyReadingRepository
from src.infrastructure.db.repositories.reading_repo import ReadingRepository
from src.infrastructure.db.repositories.rune_daily_repo import (
    RuneDailyReadingRepository,
)
from src.infrastructure.db.repositories.rune_reading_repo import RuneReadingRepository
from src.infrastructure.db.repositories.rune_repo import RuneRepository
from src.infrastructure.db.repositories.rune_spread_repo import RuneSpreadRepository
from src.infrastructure.db.repositories.rune_user_repo import RuneUserRepository
from src.infrastructure.db.repositories.spread_repo import SpreadRepository
from src.infrastructure.db.repositories.user_repo import UserRepository
from src.infrastructure.imaging.composer import ImageComposer
from src.infrastructure.llm.deepseek_backend import DeepSeekBackend
from src.infrastructure.telegram.messenger import TelegramMessenger


def build_user_service(session: AsyncSession, *, profile: BotProfile) -> UserService:
    if profile.kind == PROFILE_RUNES:
        return UserService(users=RuneUserRepository(session))
    return UserService(users=UserRepository(session))


def build_daily_repo(session: AsyncSession, *, profile: BotProfile):
    if profile.kind == PROFILE_RUNES:
        return RuneDailyReadingRepository(session)
    return DailyReadingRepository(session)


def build_user_repo(session: AsyncSession, *, profile: BotProfile):
    if profile.kind == PROFILE_RUNES:
        return RuneUserRepository(session)
    return UserRepository(session)


async def build_reading_service(
    session: AsyncSession,
    *,
    profile: BotProfile,
    llm: DeepSeekBackend,
    messenger: TelegramMessenger,
    images,
    non_invertible_ids: frozenset[int] | None = None,
) -> ReadingService:
    if profile.kind == PROFILE_RUNES:
        rune_repo = RuneRepository(session)
        if non_invertible_ids is None:
            non_invertible_ids = await rune_repo.list_non_invertible_ids()
        draw_config = DrawConfig(
            id_min=RUNE_ID_MIN,
            id_max=RUNE_ID_MAX,
            non_invertible_ids=non_invertible_ids,
        )
        return ReadingService(
            users=RuneUserRepository(session),
            cards=rune_repo,
            spreads=RuneSpreadRepository(session),
            readings=RuneReadingRepository(session),
            daily=RuneDailyReadingRepository(session),
            llm=llm,
            images=images,
            messenger=messenger,
            draw_config=draw_config,
            processing_messages=profile.processing_messages,
            item_label=profile.item_label,
        )
    return ReadingService(
        users=UserRepository(session),
        cards=CardRepository(session),
        spreads=SpreadRepository(session),
        readings=ReadingRepository(session),
        daily=DailyReadingRepository(session),
        llm=llm,
        images=images if images is not None else ImageComposer(),
        messenger=messenger,
        draw_config=TAROT_DRAW_CONFIG,
        processing_messages=profile.processing_messages,
        item_label=profile.item_label,
    )
