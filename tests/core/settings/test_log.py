"""Logging setup behavior."""

from __future__ import annotations

import json
import logging
from logging.config import fileConfig

import structlog

from src.core.settings.config import PROJECT_ROOT
from src.core.settings.log import setup_logging


def test_setup_logging_emits_json_event_to_stderr(capsys) -> None:
    setup_logging()
    structlog.get_logger().info("bot_startup", bot_mode="all", profiles=["tarot"])
    err = capsys.readouterr().err
    payload = json.loads(err.strip().splitlines()[-1])
    assert payload["event"] == "bot_startup"
    assert payload["bot_mode"] == "all"
    assert payload["profiles"] == ["tarot"]
    assert payload["level"] == "info"


def test_setup_logging_restores_info_after_alembic_file_config(capsys) -> None:
    setup_logging()
    ini = PROJECT_ROOT / "alembic.ini"
    assert ini.is_file()
    fileConfig(str(ini))
    assert logging.getLogger().level >= logging.WARNING

    setup_logging()
    structlog.get_logger().info("seed_complete")
    err = capsys.readouterr().err
    payload = json.loads(err.strip().splitlines()[-1])
    assert payload["event"] == "seed_complete"


def test_migration_env_skips_file_config_when_handlers_exist() -> None:
    setup_logging()
    assert logging.getLogger().handlers
    # Mirrors guard in migrations/env.py
    should_configure = (
        PROJECT_ROOT.joinpath("alembic.ini").is_file()
        and not logging.getLogger().handlers
    )
    assert should_configure is False
