"""Bot profiles for multi-divination wiring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.core.settings.config import RUNES_FONT_PATH, TAROT_IMAGES_DIR, Settings
from src.core.settings.constants import (
    PROCESSING_MESSAGES,
    PROFILE_RUNES,
    PROFILE_TAROT,
    RUNE_PROCESSING_MESSAGES,
)


@dataclass(frozen=True)
class BotButtons:
    single: str
    three: str
    daily: str
    settings: str
    back: str
    toggle_daily: str
    toggle_inverted: str | None


@dataclass(frozen=True)
class BotProfile:
    kind: str
    token: str
    buttons: BotButtons
    processing_messages: dict[str, str]
    show_inverted_toggle: bool
    item_label: str
    images_dir: Path | None = None
    font_path: Path | None = None


def tarot_profile() -> BotProfile | None:
    token = Settings.TELEGRAM_BOT_TOKEN_TAROT
    if not token:
        return None
    return BotProfile(
        kind=PROFILE_TAROT,
        token=token,
        buttons=BotButtons(
            single="1 карта",
            three="3 карты",
            daily="Карта дня",
            settings="Параметры",
            back="Назад",
            toggle_daily="Карта дня авто",
            toggle_inverted="Перевернутые",
        ),
        processing_messages=PROCESSING_MESSAGES,
        show_inverted_toggle=True,
        item_label="Карта",
        images_dir=TAROT_IMAGES_DIR,
    )


def runes_profile() -> BotProfile | None:
    token = Settings.TELEGRAM_BOT_TOKEN_RUNES
    if not token:
        return None
    tarot = Settings.TELEGRAM_BOT_TOKEN_TAROT
    if tarot and token == tarot:
        raise ValueError("TELEGRAM_BOT_TOKEN_RUNES must differ from TAROT token")
    if not RUNES_FONT_PATH.exists():
        raise FileNotFoundError(f"Rune font required: {RUNES_FONT_PATH}")
    return BotProfile(
        kind=PROFILE_RUNES,
        token=token,
        buttons=BotButtons(
            single="Одна руна",
            three="Три руны",
            daily="Руна дня",
            settings="Параметры",
            back="Назад",
            toggle_daily="Руна дня авто",
            toggle_inverted=None,
        ),
        processing_messages=RUNE_PROCESSING_MESSAGES,
        show_inverted_toggle=False,
        item_label="Руна",
        font_path=RUNES_FONT_PATH,
    )
