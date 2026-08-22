"""Telegram reply keyboards."""

from __future__ import annotations

BTN_SINGLE = "1 карта"
BTN_THREE = "3 карты"
BTN_DAILY = "Карта дня"
BTN_SETTINGS = "Параметры"
BTN_BACK = "Назад"
BTN_TOGGLE_DAILY = "Карта дня авто"
BTN_TOGGLE_INVERTED = "Перевернутые"


def main_keyboard() -> dict:
    return {
        "keyboard": [
            [{"text": BTN_SINGLE}, {"text": BTN_THREE}],
            [{"text": BTN_DAILY}, {"text": BTN_SETTINGS}],
        ],
        "resize_keyboard": True,
    }


def settings_keyboard(*, daily_on: bool, inverted_on: bool) -> dict:
    daily_label = f"{BTN_TOGGLE_DAILY}: {'да' if daily_on else 'нет'}"
    inverted_label = f"{BTN_TOGGLE_INVERTED}: {'да' if inverted_on else 'нет'}"
    return {
        "keyboard": [
            [{"text": daily_label}],
            [{"text": inverted_label}],
            [{"text": BTN_BACK}],
        ],
        "resize_keyboard": True,
    }
