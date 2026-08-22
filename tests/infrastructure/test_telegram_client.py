"""Tests for Telegram client."""

import pytest

from src.infrastructure.telegram.client import TelegramClient


def test_token_fail_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        TelegramClient(token="")


def test_base_url_not_bot_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:test")
    client = TelegramClient(token="123:test")
    assert "botNone" not in client.base_url
