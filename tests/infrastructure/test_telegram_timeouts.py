"""Tests for Telegram client timeouts."""

from src.core.settings.constants import (
    TELEGRAM_HTTP_READ_TIMEOUT,
    TELEGRAM_POLL_TIMEOUT,
)


def test_http_read_timeout_exceeds_poll_timeout() -> None:
    assert TELEGRAM_HTTP_READ_TIMEOUT > TELEGRAM_POLL_TIMEOUT
