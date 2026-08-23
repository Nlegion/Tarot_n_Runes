"""Telegram reply keyboards (profile-driven)."""

from __future__ import annotations

from src.core.settings.profiles import BotButtons, BotProfile


def main_keyboard(buttons: BotButtons) -> dict:
    return {
        "keyboard": [
            [{"text": buttons.single}, {"text": buttons.three}],
            [{"text": buttons.daily}, {"text": buttons.settings}],
        ],
        "resize_keyboard": True,
    }


def settings_keyboard(
    *,
    profile: BotProfile,
    daily_on: bool,
    inverted_on: bool,
) -> dict:
    buttons = profile.buttons
    daily_label = f"{buttons.toggle_daily}: {'да' if daily_on else 'нет'}"
    rows: list[list[dict[str, str]]] = [[{"text": daily_label}]]
    if profile.show_inverted_toggle and buttons.toggle_inverted:
        inverted_label = f"{buttons.toggle_inverted}: {'да' if inverted_on else 'нет'}"
        rows.append([{"text": inverted_label}])
    rows.append([{"text": buttons.back}])
    return {"keyboard": rows, "resize_keyboard": True}
