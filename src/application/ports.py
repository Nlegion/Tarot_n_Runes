"""Application port protocols."""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from src.application.dto import GenerationRequest, GenerationResponse
from src.domain.entities import Card, SlotDraw, UserSettings


class CardRepositoryPort(Protocol):
    async def get_by_id(self, card_id: int) -> Card | None: ...
    async def list_all(self) -> list[Card]: ...


class UserRepositoryPort(Protocol):
    async def upsert_from_telegram(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
    ) -> int: ...

    async def get_settings(self, user_id: int) -> UserSettings: ...

    async def update_settings(
        self,
        *,
        user_id: int,
        daily_card_broadcast: bool | None = None,
        allow_inverted: bool | None = None,
    ) -> UserSettings: ...

    async def disable_broadcast(self, user_id: int) -> None: ...

    async def get_telegram_id(self, user_id: int) -> int | None: ...


class ReadingRepositoryPort(Protocol):
    async def create_reading_with_slots(
        self,
        *,
        user_id: int,
        spread_type_id: int,
        prompt_id: int,
        slots: tuple[SlotDraw, ...],
        slot_id_map: dict[str, int],
    ) -> int: ...

    async def save_interpretation(
        self,
        *,
        reading_id: int,
        status: str,
        raw_llm_text: str,
        raw_llm_text_repair: str | None,
        interpretation: str,
    ) -> None: ...

    async def get_reading(self, reading_id: int) -> dict | None: ...

    async def reset_for_reinterpretation(self, *, reading_id: int) -> None: ...


class DailyReadingRepositoryPort(Protocol):
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
    ) -> tuple[int, bool]: ...

    async def get_daily_reading_id(
        self, *, user_id: int, card_date: date
    ) -> int | None: ...

    async def get_daily_state(
        self, *, user_id: int, card_date: date
    ) -> dict | None: ...

    async def mark_interpretation_attempt(
        self,
        *,
        user_id: int,
        card_date: date,
        attempt_count: int,
        next_attempt_at: datetime | None,
        last_error: str | None,
    ) -> None: ...

    async def replace_daily_reading(
        self,
        *,
        user_id: int,
        card_date: date,
        spread_type_id: int,
        prompt_id: int,
        slots: tuple[SlotDraw, ...],
        slot_id_map: dict[str, int],
    ) -> int: ...

    async def list_pending_deliveries(self, *, limit: int) -> list[dict]: ...

    async def mark_delivery(
        self,
        *,
        daily_id: int,
        status: str,
        attempt_count: int,
        next_attempt_at: datetime | None,
        last_error: str | None,
    ) -> None: ...

    async def list_broadcast_users(self) -> list[int]: ...


class SpreadRepositoryPort(Protocol):
    async def get_spread_type_id(self, code: str) -> int: ...

    async def get_active_prompt(self, spread_type_id: int) -> dict: ...

    async def get_slot_id_map(self, spread_type_id: int) -> dict[str, int]: ...


class LLMPort(Protocol):
    async def generate(self, request: GenerationRequest) -> GenerationResponse: ...

    async def close(self) -> None: ...


class ImagePort(Protocol):
    def compose_reading_image(self, *, slots: tuple[SlotDraw, ...]) -> bytes: ...


class MessengerPort(Protocol):
    async def send_message(self, *, chat_id: int, text: str) -> int: ...

    async def delete_message(self, *, chat_id: int, message_id: int) -> None: ...

    async def edit_message(
        self, *, chat_id: int, message_id: int, text: str
    ) -> None: ...

    async def send_chat_action(
        self, *, chat_id: int, action: str = "typing"
    ) -> None: ...

    async def send_photo(
        self, *, chat_id: int, photo_bytes: bytes, caption: str | None = None
    ) -> None: ...

    async def answer_callback(
        self, *, callback_query_id: str, text: str = ""
    ) -> None: ...

    async def close(self) -> None: ...
