"""Tests for Telegram client."""

import pytest

from src.infrastructure.telegram.client import TelegramClient


def test_token_required() -> None:
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN_TAROT"):
        TelegramClient(token="")


def test_base_url_uses_explicit_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN_TAROT", "env-token")
    client = TelegramClient(token="123:test")
    assert client.base_url.endswith("/bot123:test")
    assert "botNone" not in client.base_url
    assert "env-token" not in client.base_url
