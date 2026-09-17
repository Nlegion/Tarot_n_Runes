"""Tests for daily interpretation retry and redraw fallback."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.application import reading_progress
from src.application.dto import GenerationResponse
from src.application.reading_service import ReadingService
from src.core.settings.constants import (
    DAILY_INTERPRETATION_MAX_ATTEMPTS,
    DAILY_INTERPRETATION_RETRY_SECONDS,
    INTERPRETATION_FAILED_MESSAGE,
    READING_STATUS_COMPLETED,
    READING_STATUS_FAILED,
    READING_STATUS_PENDING,
)
from src.domain.draw_engine import DrawConfig
from src.domain.entities import Card, SlotDraw, UserSettings


@pytest.fixture(autouse=True)
def fast_progress_timing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reading_progress, "FOCUS_PAUSE_SECONDS", 0.0)
    monkeypatch.setattr(reading_progress, "INTERPRETING_MIN_VISIBLE_SECONDS", 0.0)

    async def instant_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(reading_progress.asyncio, "sleep", instant_sleep)
    monkeypatch.setattr(reading_progress, "_refresh_typing", AsyncMock())


class FakeUsers:
    async def get_settings(self, user_id: int) -> UserSettings:
        return UserSettings(
            daily_card_broadcast=False,
            allow_inverted=False,
        )


class FakeCards:
    async def get_by_id(self, card_id: int) -> Card:
        return Card(
            id=card_id,
            name=f"Card {card_id}",
            orig_name=f"Orig {card_id}",
            straight_position="straight",
            inverted_position="inverted",
        )


class FakeSpreads:
    async def get_spread_type_id(self, code: str) -> int:
        return 1

    async def get_active_prompt(self, spread_type_id: int) -> dict:
        return {
            "id": 10,
            "system_template": "system",
            "user_template": "Карта дня: {card_name}",
        }

    async def get_slot_id_map(self, spread_type_id: int) -> dict[str, int]:
        return {"T1": 1}


class FakeReadings:
    def __init__(self) -> None:
        self.readings: dict[int, dict] = {}
        self._next_id = 1
        self.reset_calls: list[int] = []

    async def create_reading_with_slots(
        self,
        *,
        user_id: int,
        spread_type_id: int,
        prompt_id: int,
        slots: tuple[SlotDraw, ...],
        slot_id_map: dict[str, int],
    ) -> int:
        reading_id = self._next_id
        self._next_id += 1
        self.readings[reading_id] = {
            "id": reading_id,
            "user_id": user_id,
            "spread_type_id": spread_type_id,
            "status": READING_STATUS_PENDING,
            "interpretation": None,
            "slots": [
                {
                    "card_id": slot.card_id,
                    "is_inverted": slot.is_inverted,
                    "spread_slot_id": slot_id_map[slot.slot_code],
                }
                for slot in slots
            ],
        }
        return reading_id

    async def save_interpretation(
        self,
        *,
        reading_id: int,
        status: str,
        raw_llm_text: str,
        raw_llm_text_repair: str | None,
        interpretation: str,
    ) -> None:
        reading = self.readings[reading_id]
        reading["status"] = status
        reading["interpretation"] = interpretation or None

    async def get_reading(self, reading_id: int) -> dict | None:
        reading = self.readings.get(reading_id)
        return None if reading is None else dict(reading)

    async def reset_for_reinterpretation(self, *, reading_id: int) -> None:
        self.reset_calls.append(reading_id)
        reading = self.readings[reading_id]
        reading["status"] = READING_STATUS_PENDING
        reading["interpretation"] = None


class FakeDaily:
    def __init__(self, readings: FakeReadings) -> None:
        self._readings = readings
        self.state: dict[tuple[int, date], dict] = {}
        self.replace_calls = 0

    async def claim_daily(
        self,
        *,
        user_id: int,
        card_date: date,
        spread_type_id: int,
        prompt_id: int,
        slots: tuple[SlotDraw, ...],
        slot_id_map: dict[str, int],
        delivery_status: str = "none",
    ) -> tuple[int, bool]:
        key = (user_id, card_date)
        if key in self.state:
            return self.state[key]["reading_id"], False
        reading_id = await self._readings.create_reading_with_slots(
            user_id=user_id,
            spread_type_id=spread_type_id,
            prompt_id=prompt_id,
            slots=slots,
            slot_id_map=slot_id_map,
        )
        self.state[key] = {
            "daily_id": 1,
            "reading_id": reading_id,
            "attempt_count": 0,
            "next_attempt_at": None,
            "last_error": None,
            "delivery_status": delivery_status,
        }
        return reading_id, True

    async def get_daily_reading_id(
        self, *, user_id: int, card_date: date
    ) -> int | None:
        state = self.state.get((user_id, card_date))
        return None if state is None else state["reading_id"]

    async def get_daily_state(self, *, user_id: int, card_date: date) -> dict | None:
        state = self.state.get((user_id, card_date))
        return None if state is None else dict(state)

    async def mark_interpretation_attempt(
        self,
        *,
        user_id: int,
        card_date: date,
        attempt_count: int,
        next_attempt_at: datetime | None,
        last_error: str | None,
    ) -> None:
        state = self.state[(user_id, card_date)]
        state["attempt_count"] = attempt_count
        state["next_attempt_at"] = next_attempt_at
        state["last_error"] = last_error

    async def replace_daily_reading(
        self,
        *,
        user_id: int,
        card_date: date,
        spread_type_id: int,
        prompt_id: int,
        slots: tuple[SlotDraw, ...],
        slot_id_map: dict[str, int],
    ) -> int:
        self.replace_calls += 1
        reading_id = await self._readings.create_reading_with_slots(
            user_id=user_id,
            spread_type_id=spread_type_id,
            prompt_id=prompt_id,
            slots=slots,
            slot_id_map=slot_id_map,
        )
        state = self.state[(user_id, card_date)]
        state["reading_id"] = reading_id
        state["attempt_count"] = 0
        state["next_attempt_at"] = None
        state["last_error"] = None
        return reading_id

    async def list_pending_deliveries(self, *, limit: int) -> list[dict]:
        return []

    async def mark_delivery(
        self,
        *,
        daily_id: int,
        status: str,
        attempt_count: int,
        next_attempt_at: datetime | None,
        last_error: str | None,
    ) -> None:
        return None

    async def list_broadcast_users(self) -> list[int]:
        return []


def _response(text: str, *, finish_reason: str) -> GenerationResponse:
    return GenerationResponse(
        text=text,
        model_name="test",
        latency_ms=1,
        finish_reason=finish_reason,
    )


def _valid_text() -> str:
    return (
        "Сегодня карта советует сохранять спокойствие и действовать уверенно. "
        "Важно замечать детали и не торопить события вокруг себя."
    )


def _build_service(
    *,
    llm: AsyncMock,
    readings: FakeReadings | None = None,
    daily: FakeDaily | None = None,
) -> tuple[ReadingService, FakeReadings, FakeDaily, AsyncMock]:
    readings = readings or FakeReadings()
    daily = daily or FakeDaily(readings)
    messenger = AsyncMock()
    messenger.send_message = AsyncMock(return_value=1)
    messenger.send_photo = AsyncMock()
    messenger.send_long_text = AsyncMock()
    messenger.send_chat_action = AsyncMock()
    messenger.delete_message = AsyncMock()
    messenger.edit_message = AsyncMock()
    images = AsyncMock()
    images.compose_reading_image = AsyncMock(return_value=b"img")
    service = ReadingService(
        users=FakeUsers(),
        cards=FakeCards(),
        spreads=FakeSpreads(),
        readings=readings,
        daily=daily,
        llm=llm,
        images=images,
        messenger=messenger,
        draw_config=DrawConfig(
            id_min=0,
            id_max=2,
            non_invertible_ids=frozenset(),
        ),
    )
    return service, readings, daily, messenger


@pytest.mark.asyncio
async def test_daily_failure_schedules_retry() -> None:
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=_response("", finish_reason="length"))
    service, readings, daily, messenger = _build_service(llm=llm)
    today = date(2026, 9, 16)

    ok = await service.perform_daily(
        user_id=1,
        telegram_chat_id=100,
        card_date=today,
        for_broadcast=False,
    )

    assert ok is False
    state = await daily.get_daily_state(user_id=1, card_date=today)
    assert state is not None
    assert state["attempt_count"] == 1
    assert state["next_attempt_at"] is not None
    assert state["last_error"] == "interpretation_failed"
    reading = await readings.get_reading(state["reading_id"])
    assert reading is not None
    assert reading["status"] == READING_STATUS_FAILED
    messenger.send_message.assert_any_await(
        chat_id=100,
        text=INTERPRETATION_FAILED_MESSAGE,
    )
    assert daily.replace_calls == 0


@pytest.mark.asyncio
async def test_daily_retry_before_cooldown_skips_llm() -> None:
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=_response("", finish_reason="length"))
    service, _readings, daily, messenger = _build_service(llm=llm)
    today = date(2026, 9, 16)
    await service.perform_daily(
        user_id=1,
        telegram_chat_id=100,
        card_date=today,
        for_broadcast=False,
    )
    llm.generate.reset_mock()
    messenger.send_message.reset_mock()

    ok = await service.perform_daily(
        user_id=1,
        telegram_chat_id=100,
        card_date=today,
        for_broadcast=False,
    )

    assert ok is False
    llm.generate.assert_not_called()
    messenger.send_message.assert_awaited()


@pytest.mark.asyncio
async def test_daily_retry_after_cooldown_reinterprets_same_reading() -> None:
    llm = AsyncMock()
    llm.generate = AsyncMock(
        side_effect=[
            _response("", finish_reason="length"),
            _response("", finish_reason="length"),
            _response(_valid_text(), finish_reason="stop"),
        ]
    )
    service, readings, daily, _messenger = _build_service(llm=llm)
    today = date(2026, 9, 16)
    await service.perform_daily(
        user_id=1,
        telegram_chat_id=100,
        card_date=today,
        for_broadcast=False,
    )
    state = await daily.get_daily_state(user_id=1, card_date=today)
    assert state is not None
    first_reading_id = state["reading_id"]
    daily.state[(1, today)]["next_attempt_at"] = datetime.utcnow() - timedelta(
        seconds=1
    )

    ok = await service.perform_daily(
        user_id=1,
        telegram_chat_id=100,
        card_date=today,
        for_broadcast=False,
    )

    assert ok is True
    assert first_reading_id in readings.reset_calls
    state = await daily.get_daily_state(user_id=1, card_date=today)
    assert state is not None
    assert state["reading_id"] == first_reading_id
    assert state["attempt_count"] == 0
    reading = await readings.get_reading(first_reading_id)
    assert reading is not None
    assert reading["status"] == READING_STATUS_COMPLETED
    assert daily.replace_calls == 0


@pytest.mark.asyncio
async def test_daily_redraws_after_max_attempts() -> None:
    llm = AsyncMock()
    llm.generate = AsyncMock(
        return_value=_response(_valid_text(), finish_reason="stop")
    )
    readings = FakeReadings()
    daily = FakeDaily(readings)
    today = date(2026, 9, 16)
    reading_id = await readings.create_reading_with_slots(
        user_id=1,
        spread_type_id=1,
        prompt_id=10,
        slots=(
            SlotDraw(
                slot_code="T1",
                slot_index=0,
                card_id=1,
                is_inverted=False,
            ),
        ),
        slot_id_map={"T1": 1},
    )
    await readings.save_interpretation(
        reading_id=reading_id,
        status=READING_STATUS_FAILED,
        raw_llm_text="",
        raw_llm_text_repair=None,
        interpretation="",
    )
    daily.state[(1, today)] = {
        "daily_id": 1,
        "reading_id": reading_id,
        "attempt_count": DAILY_INTERPRETATION_MAX_ATTEMPTS,
        "next_attempt_at": datetime.utcnow() - timedelta(seconds=1),
        "last_error": "interpretation_failed",
        "delivery_status": "none",
    }
    service, _readings, daily, _messenger = _build_service(
        llm=llm,
        readings=readings,
        daily=daily,
    )

    ok = await service.perform_daily(
        user_id=1,
        telegram_chat_id=100,
        card_date=today,
        for_broadcast=False,
    )

    assert ok is True
    assert daily.replace_calls == 1
    state = await daily.get_daily_state(user_id=1, card_date=today)
    assert state is not None
    assert state["reading_id"] != reading_id
    new_reading = await readings.get_reading(state["reading_id"])
    assert new_reading is not None
    assert new_reading["status"] == READING_STATUS_COMPLETED


@pytest.mark.asyncio
async def test_daily_fifth_failure_redraws_immediately() -> None:
    llm = AsyncMock()
    llm.generate = AsyncMock(
        side_effect=[
            _response("", finish_reason="length"),
            _response("", finish_reason="length"),
            _response(_valid_text(), finish_reason="stop"),
        ]
    )
    readings = FakeReadings()
    daily = FakeDaily(readings)
    today = date(2026, 9, 16)
    reading_id = await readings.create_reading_with_slots(
        user_id=1,
        spread_type_id=1,
        prompt_id=10,
        slots=(
            SlotDraw(
                slot_code="T1",
                slot_index=0,
                card_id=1,
                is_inverted=False,
            ),
        ),
        slot_id_map={"T1": 1},
    )
    await readings.save_interpretation(
        reading_id=reading_id,
        status=READING_STATUS_FAILED,
        raw_llm_text="",
        raw_llm_text_repair=None,
        interpretation="",
    )
    daily.state[(1, today)] = {
        "daily_id": 1,
        "reading_id": reading_id,
        "attempt_count": DAILY_INTERPRETATION_MAX_ATTEMPTS - 1,
        "next_attempt_at": datetime.utcnow()
        - timedelta(seconds=DAILY_INTERPRETATION_RETRY_SECONDS),
        "last_error": "interpretation_failed",
        "delivery_status": "none",
    }
    service, _readings, daily, _messenger = _build_service(
        llm=llm,
        readings=readings,
        daily=daily,
    )

    ok = await service.perform_daily(
        user_id=1,
        telegram_chat_id=100,
        card_date=today,
        for_broadcast=False,
    )

    assert ok is True
    assert daily.replace_calls == 1
    state = await daily.get_daily_state(user_id=1, card_date=today)
    assert state is not None
    assert state["reading_id"] != reading_id
