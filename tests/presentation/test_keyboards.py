"""Tests for profile-driven keyboards and welcome."""

from src.core.settings.constants import WELCOME_MESSAGE
from src.presentation.keyboards import main_keyboard, settings_keyboard


def test_welcome_has_newlines() -> None:
    lines = WELCOME_MESSAGE.split("\n")
    assert len(lines) == 4
    assert lines[0] == "Добро пожаловать!"
    assert lines[-1] == "Выберите расклад:"


def test_tarot_settings_has_inverted() -> None:
    from src.core.settings.constants import PROCESSING_MESSAGES, PROFILE_TAROT
    from src.core.settings.profiles import BotButtons, BotProfile

    profile = BotProfile(
        kind=PROFILE_TAROT,
        token="x",
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
    )
    markup = settings_keyboard(profile=profile, daily_on=True, inverted_on=False)
    texts = [row[0]["text"] for row in markup["keyboard"]]
    assert any("Перевернутые" in t for t in texts)


def test_runes_settings_no_inverted() -> None:
    from src.core.settings.constants import PROFILE_RUNES, RUNE_PROCESSING_MESSAGES
    from src.core.settings.profiles import BotButtons, BotProfile

    profile = BotProfile(
        kind=PROFILE_RUNES,
        token="y",
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
    )
    markup = settings_keyboard(profile=profile, daily_on=False, inverted_on=True)
    texts = [row[0]["text"] for row in markup["keyboard"]]
    assert not any("Перевернутые" in t for t in texts)
    assert any("Руна дня авто" in t for t in texts)
    main = main_keyboard(profile.buttons)
    assert main["keyboard"][0][0]["text"] == "Одна руна"
