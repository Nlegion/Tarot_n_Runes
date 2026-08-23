"""Project settings."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TAROT_IMAGES_DIR = PROJECT_ROOT / "images" / "tarot"
CSV_PATH = PROJECT_ROOT / "tarot_cards.csv"


class Settings:
    TELEGRAM_BOT_TOKEN_TAROT: str | None = os.getenv("TELEGRAM_BOT_TOKEN_TAROT")
    TELEGRAM_BOT_TOKEN_RUNES: str | None = os.getenv("TELEGRAM_BOT_TOKEN_RUNES") or None
    DEEPSEEK_API_KEY: str | None = os.getenv("DEEPSEEK_API_KEY")
    TELEGRAM_PROXY_URL: str | None = os.getenv("TELEGRAM_PROXY_URL") or None
    GENERATION_SERVER_URL: str = os.getenv(
        "GENERATION_SERVER_URL", "https://api.deepseek.com"
    ).rstrip("/")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "deepseek-v4-flash")
    DB_PATH: str = os.getenv("DB_PATH", "tarot.db")
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")

    @classmethod
    def db_url(cls) -> str:
        db_file = Path(cls.DB_PATH)
        if not db_file.is_absolute():
            db_file = PROJECT_ROOT / db_file
        return f"sqlite+aiosqlite:///{db_file.as_posix()}"

    @classmethod
    def validate_startup(cls) -> None:
        missing: list[str] = []
        if not cls.TELEGRAM_BOT_TOKEN_TAROT:
            missing.append("TELEGRAM_BOT_TOKEN_TAROT")
        if not cls.DEEPSEEK_API_KEY:
            missing.append("DEEPSEEK_API_KEY")
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
