"""Logging setup."""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging() -> None:
    """Configure stdlib + structlog so app events reach stderr (docker logs)."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Allow re-configure after Alembic fileConfig without stale cached loggers.
    structlog.reset_defaults()
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root.disabled = False

    # fileConfig(disable_existing_loggers=True) leaves loggers disabled.
    for name in list(logging.root.manager.loggerDict):
        logging.getLogger(name).disabled = False

    for name in ("sqlalchemy", "alembic", "asyncio", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
