"""Project settings."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TAROT_IMAGES_DIR = PROJECT_ROOT / "images" / "tarot"
CSV_PATH = PROJECT_ROOT / "tarot_cards.csv"
RUNES_CSV_PATH = PROJECT_ROOT / "runes.csv"
RUNES_FONT_PATH = PROJECT_ROOT / "fonts" / "NotoSansRunic-Regular.ttf"


class Settings:
    TELEGRAM_BOT_TOKEN_TAROT: str | None = os.getenv("TELEGRAM_BOT_TOKEN_TAROT") or None
    TELEGRAM_BOT_TOKEN_RUNES: str | None = os.getenv("TELEGRAM_BOT_TOKEN_RUNES") or None
    DEEPSEEK_API_KEY: str | None = os.getenv("DEEPSEEK_API_KEY")
    TELEGRAM_PROXY_URL: str | None = os.getenv("TELEGRAM_PROXY_URL") or None
    GENERATION_SERVER_URL: str = os.getenv(
        "GENERATION_SERVER_URL", "https://api.deepseek.com"
    ).rstrip("/")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "deepseek-v4-flash")
    DB_PATH: str = os.getenv("DB_PATH", "tarot.db")
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")
    # all | tarot | runes — which bot stacks to start
    BOT_MODE: str = (os.getenv("BOT_MODE") or "all").strip().lower()

    @classmethod
    def db_url(cls) -> str:
        db_file = Path(cls.DB_PATH)
        if not db_file.is_absolute():
            db_file = PROJECT_ROOT / db_file
        return f"sqlite+aiosqlite:///{db_file.as_posix()}"

    @classmethod
    def validate_startup(cls) -> None:
        if cls.BOT_MODE not in {"all", "tarot", "runes"}:
            raise ValueError("BOT_MODE must be one of: all, tarot, runes")
        missing: list[str] = []
        if not cls.DEEPSEEK_API_KEY:
            missing.append("DEEPSEEK_API_KEY")
        need_tarot = cls.BOT_MODE in {"all", "tarot"}
        need_runes = cls.BOT_MODE in {"all", "runes"}
        if need_tarot and not cls.TELEGRAM_BOT_TOKEN_TAROT and cls.BOT_MODE == "tarot":
            missing.append("TELEGRAM_BOT_TOKEN_TAROT")
        if need_runes and not cls.TELEGRAM_BOT_TOKEN_RUNES and cls.BOT_MODE == "runes":
            missing.append("TELEGRAM_BOT_TOKEN_RUNES")
        if cls.BOT_MODE == "all":
            if not cls.TELEGRAM_BOT_TOKEN_TAROT and not cls.TELEGRAM_BOT_TOKEN_RUNES:
                missing.append("TELEGRAM_BOT_TOKEN_TAROT or TELEGRAM_BOT_TOKEN_RUNES")
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
        if (
            cls.TELEGRAM_BOT_TOKEN_RUNES
            and cls.TELEGRAM_BOT_TOKEN_TAROT
            and cls.TELEGRAM_BOT_TOKEN_RUNES == cls.TELEGRAM_BOT_TOKEN_TAROT
        ):
            raise ValueError(
                "TELEGRAM_BOT_TOKEN_RUNES must differ from TELEGRAM_BOT_TOKEN_TAROT"
            )
