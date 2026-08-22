"""Application wiring helpers."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.reading_service import ReadingService
from src.application.user_service import UserService
from src.infrastructure.db.repositories.card_repo import CardRepository
from src.infrastructure.db.repositories.daily_repo import DailyReadingRepository
from src.infrastructure.db.repositories.reading_repo import ReadingRepository
from src.infrastructure.db.repositories.spread_repo import SpreadRepository
from src.infrastructure.db.repositories.user_repo import UserRepository
from src.infrastructure.imaging.composer import ImageComposer
from src.infrastructure.llm.deepseek_backend import DeepSeekBackend
from src.infrastructure.telegram.messenger import TelegramMessenger


def build_user_service(session: AsyncSession) -> UserService:
    return UserService(users=UserRepository(session))


def build_reading_service(
    session: AsyncSession,
    *,
    llm: DeepSeekBackend,
    messenger: TelegramMessenger,
    images: ImageComposer,
) -> ReadingService:
    return ReadingService(
        users=UserRepository(session),
        cards=CardRepository(session),
        spreads=SpreadRepository(session),
        readings=ReadingRepository(session),
        daily=DailyReadingRepository(session),
        llm=llm,
        images=images,
        messenger=messenger,
    )
