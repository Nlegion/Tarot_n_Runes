"""Quick startup smoke test."""

from __future__ import annotations

import asyncio
import sys

from src.core.settings.config import Settings
from src.core.settings.log import setup_logging
from src.infrastructure.db.migrations_runner import apply_migrations
from src.infrastructure.db.seed import seed_database
from src.infrastructure.db.session import health_check, session_scope
from src.infrastructure.telegram.client import TelegramClient


def _prepare() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    setup_logging()
    Settings.validate_startup()
    apply_migrations()


async def main() -> None:
    async with session_scope() as session:
        await seed_database(session)
    await health_check()
    client = TelegramClient(token=Settings.TELEGRAM_BOT_TOKEN_TAROT or "")
    me = await client.request("getMe")
    username = me["result"].get("username")
    print(f"startup_ok bot=@{username}")
    await client.close()


if __name__ == "__main__":
    _prepare()
    asyncio.run(main())
