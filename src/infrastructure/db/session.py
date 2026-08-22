"""Async database engine and session."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.settings.config import Settings

logger = structlog.get_logger()
_write_lock = asyncio.Semaphore(1)


def _set_sqlite_pragma(dbapi_conn, _connection_record) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


_engine = None
_session_factory = None


def get_engine():
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(
            Settings.db_url(),
            connect_args={"check_same_thread": False},
            echo=False,
        )
        event.listen(_engine.sync_engine, "connect", _set_sqlite_pragma)
        _session_factory = async_sessionmaker(
            _engine, expire_on_commit=False, class_=AsyncSession
        )
    return _engine


def get_session_factory():
    get_engine()
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception as exc:
        await session.rollback()
        logger.error("db_session_error", error=str(exc), exc_info=True)
        raise
    finally:
        await session.close()


async def close_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def run_with_write_lock(coro_factory):
    async with _write_lock:
        return await coro_factory()


async def health_check() -> None:
    async with session_scope() as session:
        await session.execute(text("SELECT 1"))
