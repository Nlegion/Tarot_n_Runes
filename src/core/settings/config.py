"""Project settings."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
IMAGES_DIR = PROJECT_ROOT / "images"
CSV_PATH = PROJECT_ROOT / "tarot_cards.csv"
TMP_DIR = PROJECT_ROOT / "tmp"


class Settings:
    TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
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
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.DEEPSEEK_API_KEY:
            missing.append("DEEPSEEK_API_KEY")
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
