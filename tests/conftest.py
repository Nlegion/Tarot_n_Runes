"""Shared pytest fixtures."""

from __future__ import annotations

import asyncio

import pytest

_BACKGROUND_TASK_NAMES = frozenset({"typing_indicator", "llm_generate"})


@pytest.fixture(autouse=True)
async def cancel_stray_async_tasks() -> None:
    yield
    current = asyncio.current_task()
    for task in asyncio.all_tasks():
        if task is current or task.done():
            continue
        if task.get_name() not in _BACKGROUND_TASK_NAMES:
            continue
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
