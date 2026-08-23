"""Bot profiles for multi-divination wiring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.core.settings.config import TAROT_IMAGES_DIR, Settings


@dataclass(frozen=True)
class BotProfile:
    token: str
    images_dir: Path


def tarot_profile() -> BotProfile:
    token = Settings.TELEGRAM_BOT_TOKEN_TAROT
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN_TAROT is required")
    return BotProfile(token=token, images_dir=TAROT_IMAGES_DIR)
