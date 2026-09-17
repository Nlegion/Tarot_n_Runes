"""Daily card/rune interpretation retry and redraw flow."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta

import structlog

from src.core.settings.constants import (
    DAILY_INTERPRETATION_MAX_ATTEMPTS,
    DAILY_INTERPRETATION_RETRY_SECONDS,
    DELIVERY_NONE,
    DELIVERY_PENDING,
    INTERPRETATION_FAILED_MESSAGE,
    READING_STATUS_PENDING,
    SPREAD_DAILY,
)
from src.domain.draw_engine import draw_spread
from src.domain.entities import SlotDraw

logger = structlog.get_logger()


class DailyReadingMixin:
    async def perform_daily(
        self,
        *,
        user_id: int,
        telegram_chat_id: int,
        card_date: date,
        for_broadcast: bool = False,
    ) -> bool:
        settings = await self._users.get_settings(user_id)
        spread_type_id = await self._spreads.get_spread_type_id(SPREAD_DAILY)
        prompt = await self._spreads.get_active_prompt(spread_type_id)
        slot_id_map = await self._spreads.get_slot_id_map(spread_type_id)
        draw = draw_spread(
            spread_code=SPREAD_DAILY,
            allow_inverted=settings.allow_inverted,
            config=self._draw_config,
        )
        delivery = DELIVERY_PENDING if for_broadcast else DELIVERY_NONE
        reading_id, created = await self._daily.claim_daily(
            user_id=user_id,
            card_date=card_date,
            spread_type_id=spread_type_id,
            prompt_id=prompt["id"],
            slots=draw.slots,
            slot_id_map=slot_id_map,
            delivery_status=delivery,
        )
        if not created:
            return await self._resume_daily(
                user_id=user_id,
                telegram_chat_id=telegram_chat_id,
                card_date=card_date,
                reading_id=reading_id,
                spread_type_id=spread_type_id,
                prompt=prompt,
                slot_id_map=slot_id_map,
                allow_inverted=settings.allow_inverted,
                for_broadcast=for_broadcast,
            )
        return await self._interpret_daily(
            user_id=user_id,
            telegram_chat_id=telegram_chat_id,
            card_date=card_date,
            reading_id=reading_id,
            slots=draw.slots,
            prompt=prompt,
            spread_type_id=spread_type_id,
            slot_id_map=slot_id_map,
            allow_inverted=settings.allow_inverted,
            for_broadcast=for_broadcast,
            allow_redraw=True,
        )

    async def deliver_existing_daily(
        self,
        *,
        reading_id: int,
        telegram_chat_id: int,
    ) -> bool:
        reading = await self._readings.get_reading(reading_id)
        if reading is None or not reading.get("interpretation"):
            return False
        slots = await self._load_slots(reading_id)
        await self._send_existing(
            reading_id=reading_id,
            telegram_chat_id=telegram_chat_id,
            spread_code=SPREAD_DAILY,
            slots=slots,
            interpretation=reading["interpretation"],
        )
        return True

    async def _resume_daily(
        self,
        *,
        user_id: int,
        telegram_chat_id: int,
        card_date: date,
        reading_id: int,
        spread_type_id: int,
        prompt: dict,
        slot_id_map: dict[str, int],
        allow_inverted: bool,
        for_broadcast: bool,
    ) -> bool:
        existing = await self._readings.get_reading(reading_id)
        if existing and existing.get("interpretation"):
            await self.deliver_existing_daily(
                reading_id=reading_id,
                telegram_chat_id=telegram_chat_id,
            )
            return True
        if existing and existing.get("status") == READING_STATUS_PENDING:
            for _ in range(3):
                await asyncio.sleep(1.0)
                existing = await self._readings.get_reading(reading_id)
                if existing and existing.get("interpretation"):
                    await self.deliver_existing_daily(
                        reading_id=reading_id,
                        telegram_chat_id=telegram_chat_id,
                    )
                    return True
                if existing and existing.get("status") != READING_STATUS_PENDING:
                    break
            else:
                return False
        state = await self._daily.get_daily_state(user_id=user_id, card_date=card_date)
        attempt_count = int(state["attempt_count"]) if state else 0
        next_attempt_at = state.get("next_attempt_at") if state else None
        now = datetime.utcnow()
        if (
            next_attempt_at is not None
            and now < next_attempt_at
            and attempt_count < DAILY_INTERPRETATION_MAX_ATTEMPTS
        ):
            if not for_broadcast:
                await self._messenger.send_message(
                    chat_id=telegram_chat_id,
                    text=INTERPRETATION_FAILED_MESSAGE,
                )
            return False
        if attempt_count >= DAILY_INTERPRETATION_MAX_ATTEMPTS:
            return await self._redraw_and_interpret_daily(
                user_id=user_id,
                telegram_chat_id=telegram_chat_id,
                card_date=card_date,
                spread_type_id=spread_type_id,
                prompt=prompt,
                slot_id_map=slot_id_map,
                allow_inverted=allow_inverted,
                for_broadcast=for_broadcast,
            )
        slots = await self._load_slots(reading_id)
        if not slots:
            return await self._redraw_and_interpret_daily(
                user_id=user_id,
                telegram_chat_id=telegram_chat_id,
                card_date=card_date,
                spread_type_id=spread_type_id,
                prompt=prompt,
                slot_id_map=slot_id_map,
                allow_inverted=allow_inverted,
                for_broadcast=for_broadcast,
            )
        await self._readings.reset_for_reinterpretation(reading_id=reading_id)
        return await self._interpret_daily(
            user_id=user_id,
            telegram_chat_id=telegram_chat_id,
            card_date=card_date,
            reading_id=reading_id,
            slots=slots,
            prompt=prompt,
            spread_type_id=spread_type_id,
            slot_id_map=slot_id_map,
            allow_inverted=allow_inverted,
            for_broadcast=for_broadcast,
            allow_redraw=True,
        )

    async def _interpret_daily(
        self,
        *,
        user_id: int,
        telegram_chat_id: int,
        card_date: date,
        reading_id: int,
        slots: tuple[SlotDraw, ...],
        prompt: dict,
        spread_type_id: int,
        slot_id_map: dict[str, int],
        allow_inverted: bool,
        for_broadcast: bool,
        allow_redraw: bool,
    ) -> bool:
        ok = await self._interpret_and_send(
            reading_id=reading_id,
            telegram_chat_id=telegram_chat_id,
            spread_code=SPREAD_DAILY,
            slots=slots,
            prompt=prompt,
            with_focus_pause=False,
            notify_on_failure=False,
        )
        if ok:
            await self._daily.mark_interpretation_attempt(
                user_id=user_id,
                card_date=card_date,
                attempt_count=0,
                next_attempt_at=None,
                last_error=None,
            )
            return True
        return await self._recover_failed_daily(
            user_id=user_id,
            telegram_chat_id=telegram_chat_id,
            card_date=card_date,
            spread_type_id=spread_type_id,
            prompt=prompt,
            slot_id_map=slot_id_map,
            allow_inverted=allow_inverted,
            for_broadcast=for_broadcast,
            allow_redraw=allow_redraw,
        )

    async def _recover_failed_daily(
        self,
        *,
        user_id: int,
        telegram_chat_id: int,
        card_date: date,
        spread_type_id: int,
        prompt: dict,
        slot_id_map: dict[str, int],
        allow_inverted: bool,
        for_broadcast: bool,
        allow_redraw: bool,
    ) -> bool:
        state = await self._daily.get_daily_state(user_id=user_id, card_date=card_date)
        attempt_count = int(state["attempt_count"]) + 1 if state else 1
        if attempt_count >= DAILY_INTERPRETATION_MAX_ATTEMPTS and allow_redraw:
            logger.warning(
                "daily_interpretation_exhausted",
                user_id=user_id,
                card_date=str(card_date),
                attempts=attempt_count,
            )
            return await self._redraw_and_interpret_daily(
                user_id=user_id,
                telegram_chat_id=telegram_chat_id,
                card_date=card_date,
                spread_type_id=spread_type_id,
                prompt=prompt,
                slot_id_map=slot_id_map,
                allow_inverted=allow_inverted,
                for_broadcast=for_broadcast,
            )
        next_attempt_at = datetime.utcnow() + timedelta(
            seconds=DAILY_INTERPRETATION_RETRY_SECONDS
        )
        await self._daily.mark_interpretation_attempt(
            user_id=user_id,
            card_date=card_date,
            attempt_count=attempt_count,
            next_attempt_at=next_attempt_at,
            last_error="interpretation_failed",
        )
        logger.info(
            "daily_interpretation_retry_scheduled",
            user_id=user_id,
            card_date=str(card_date),
            attempt_count=attempt_count,
            next_attempt_at=next_attempt_at.isoformat(),
        )
        if not for_broadcast:
            await self._messenger.send_message(
                chat_id=telegram_chat_id,
                text=INTERPRETATION_FAILED_MESSAGE,
            )
        return False

    async def _redraw_and_interpret_daily(
        self,
        *,
        user_id: int,
        telegram_chat_id: int,
        card_date: date,
        spread_type_id: int,
        prompt: dict,
        slot_id_map: dict[str, int],
        allow_inverted: bool,
        for_broadcast: bool,
    ) -> bool:
        draw = draw_spread(
            spread_code=SPREAD_DAILY,
            allow_inverted=allow_inverted,
            config=self._draw_config,
        )
        reading_id = await self._daily.replace_daily_reading(
            user_id=user_id,
            card_date=card_date,
            spread_type_id=spread_type_id,
            prompt_id=prompt["id"],
            slots=draw.slots,
            slot_id_map=slot_id_map,
        )
        logger.info(
            "daily_reading_redrawn",
            user_id=user_id,
            card_date=str(card_date),
            reading_id=reading_id,
        )
        return await self._interpret_daily(
            user_id=user_id,
            telegram_chat_id=telegram_chat_id,
            card_date=card_date,
            reading_id=reading_id,
            slots=draw.slots,
            prompt=prompt,
            spread_type_id=spread_type_id,
            slot_id_map=slot_id_map,
            allow_inverted=allow_inverted,
            for_broadcast=for_broadcast,
            allow_redraw=False,
        )
