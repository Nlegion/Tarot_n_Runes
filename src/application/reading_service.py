"""Reading use cases."""

from __future__ import annotations

from datetime import date

import structlog

from src.application.interpretation import (
    finalize_interpretation,
    prepare_interpretation_text,
    validate_interpretation,
)
from src.application.ports import (
    CardRepositoryPort,
    DailyReadingRepositoryPort,
    ImagePort,
    LLMPort,
    MessengerPort,
    ReadingRepositoryPort,
    SpreadRepositoryPort,
    UserRepositoryPort,
)
from src.application.prompt_builder import build_prompt, build_repair_prompt
from src.application.reading_format import format_reading_header, format_reading_message
from src.application.reading_progress import processing_notice
from src.core.settings.constants import (
    DELIVERY_NONE,
    DELIVERY_PENDING,
    READING_STATUS_COMPLETED,
    READING_STATUS_FAILED,
    SPREAD_DAILY,
)
from src.domain.draw_engine import draw_spread
from src.domain.entities import SlotDraw

logger = structlog.get_logger()


class ReadingService:
    def __init__(
        self,
        *,
        users: UserRepositoryPort,
        cards: CardRepositoryPort,
        spreads: SpreadRepositoryPort,
        readings: ReadingRepositoryPort,
        daily: DailyReadingRepositoryPort,
        llm: LLMPort,
        images: ImagePort,
        messenger: MessengerPort,
    ) -> None:
        self._users = users
        self._cards = cards
        self._spreads = spreads
        self._readings = readings
        self._daily = daily
        self._llm = llm
        self._images = images
        self._messenger = messenger

    async def perform_spread(
        self,
        *,
        user_id: int,
        telegram_chat_id: int,
        spread_code: str,
    ) -> None:
        settings = await self._users.get_settings(user_id)
        draw = draw_spread(
            spread_code=spread_code, allow_inverted=settings.allow_inverted
        )
        spread_type_id = await self._spreads.get_spread_type_id(spread_code)
        prompt = await self._spreads.get_active_prompt(spread_type_id)
        slot_id_map = await self._spreads.get_slot_id_map(spread_type_id)
        reading_id = await self._readings.create_reading_with_slots(
            user_id=user_id,
            spread_type_id=spread_type_id,
            prompt_id=prompt["id"],
            slots=draw.slots,
            slot_id_map=slot_id_map,
        )
        await self._interpret_and_send(
            reading_id=reading_id,
            telegram_chat_id=telegram_chat_id,
            spread_code=spread_code,
            slots=draw.slots,
            prompt=prompt,
            with_focus_pause=True,
        )

    async def perform_daily(
        self,
        *,
        user_id: int,
        telegram_chat_id: int,
        card_date: date,
        for_broadcast: bool = False,
    ) -> None:
        settings = await self._users.get_settings(user_id)
        spread_type_id = await self._spreads.get_spread_type_id(SPREAD_DAILY)
        prompt = await self._spreads.get_active_prompt(spread_type_id)
        slot_id_map = await self._spreads.get_slot_id_map(spread_type_id)
        draw = draw_spread(
            spread_code=SPREAD_DAILY, allow_inverted=settings.allow_inverted
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
            existing = await self._readings.get_reading(reading_id)
            if existing and existing.get("interpretation"):
                await self._send_existing(
                    reading_id=reading_id,
                    telegram_chat_id=telegram_chat_id,
                    spread_code=SPREAD_DAILY,
                    slots=await self._load_slots(reading_id),
                )
                return
        await self._interpret_and_send(
            reading_id=reading_id,
            telegram_chat_id=telegram_chat_id,
            spread_code=SPREAD_DAILY,
            slots=draw.slots,
            prompt=prompt,
            with_focus_pause=not for_broadcast,
        )

    async def _load_slots(self, reading_id: int) -> tuple[SlotDraw, ...]:
        reading = await self._readings.get_reading(reading_id)
        if reading is None:
            return ()
        spread_type_id = reading["spread_type_id"]
        slot_id_map = await self._spreads.get_slot_id_map(spread_type_id)
        reverse_map = {value: key for key, value in slot_id_map.items()}
        slots: list[SlotDraw] = []
        for index, slot in enumerate(reading["slots"]):
            code = reverse_map[slot["spread_slot_id"]]
            slots.append(
                SlotDraw(
                    slot_code=code,
                    slot_index=index,
                    card_id=slot["card_id"],
                    is_inverted=slot["is_inverted"],
                )
            )
        return tuple(slots)

    async def _interpret_and_send(
        self,
        *,
        reading_id: int,
        telegram_chat_id: int,
        spread_code: str,
        slots: tuple[SlotDraw, ...],
        prompt: dict,
        with_focus_pause: bool = False,
    ) -> None:
        cards = {
            slot.card_id: await self._cards.get_by_id(slot.card_id) for slot in slots
        }
        cards = {key: value for key, value in cards.items() if value is not None}
        request = build_prompt(
            system_template=prompt["system_template"],
            user_template=prompt["user_template"],
            spread_code=spread_code,
            slots=slots,
            cards=cards,
        )
        async with processing_notice(
            messenger=self._messenger,
            chat_id=telegram_chat_id,
            spread_code=spread_code,
            with_focus_pause=with_focus_pause,
        ) as run_generation:
            response = await run_generation(lambda: self._llm.generate(request=request))
        raw_text = response.text
        if not raw_text.strip():
            logger.warning(
                "llm_empty_content",
                reading_id=reading_id,
                spread_code=spread_code,
            )
        pre_clamp = prepare_interpretation_text(raw_text)
        interpretation = finalize_interpretation(raw_text, spread_code=spread_code)
        issues = validate_interpretation(
            interpretation,
            spread_code=spread_code,
            pre_clamp_text=pre_clamp,
            finish_reason=response.finish_reason,
        )
        repair_raw: str | None = None
        if issues:
            repair_request = build_repair_prompt(
                base=request,
                issues=issues,
                spread_code=spread_code,
            )
            async with processing_notice(
                messenger=self._messenger,
                chat_id=telegram_chat_id,
                spread_code=spread_code,
                with_focus_pause=False,
            ) as run_repair:
                repair_response = await run_repair(
                    lambda: self._llm.generate(request=repair_request)
                )
            repair_raw = repair_response.text
            if not repair_raw.strip():
                logger.warning(
                    "llm_empty_content_repair",
                    reading_id=reading_id,
                    spread_code=spread_code,
                )
            repair_pre_clamp = prepare_interpretation_text(repair_raw)
            interpretation = finalize_interpretation(
                repair_raw, spread_code=spread_code
            )
            issues = validate_interpretation(
                interpretation,
                spread_code=spread_code,
                pre_clamp_text=repair_pre_clamp,
                finish_reason=repair_response.finish_reason,
            )
        logger.info(
            "reading_generated",
            reading_id=reading_id,
            spread_code=spread_code,
            finish_reason=response.finish_reason,
            raw_len=len(raw_text),
            interp_len=len(interpretation),
            issues=issues,
        )
        if issues:
            await self._readings.save_interpretation(
                reading_id=reading_id,
                status=READING_STATUS_FAILED,
                raw_llm_text=raw_text,
                raw_llm_text_repair=repair_raw,
                interpretation="",
            )
            await self._messenger.send_message(
                chat_id=telegram_chat_id,
                text="Не удалось получить толкование. Попробуйте позже.",
            )
            return
        await self._readings.save_interpretation(
            reading_id=reading_id,
            status=READING_STATUS_COMPLETED,
            raw_llm_text=raw_text,
            raw_llm_text_repair=repair_raw,
            interpretation=interpretation,
        )
        await self._send_existing(
            reading_id=reading_id,
            telegram_chat_id=telegram_chat_id,
            spread_code=spread_code,
            slots=slots,
            interpretation=interpretation,
        )

    async def _send_existing(
        self,
        *,
        reading_id: int,
        telegram_chat_id: int,
        spread_code: str,
        slots: tuple[SlotDraw, ...],
        interpretation: str | None = None,
    ) -> None:
        if interpretation is None:
            reading = await self._readings.get_reading(reading_id)
            interpretation = reading["interpretation"] if reading else ""
        cards = {
            slot.card_id: card
            for slot in slots
            if (card := await self._cards.get_by_id(slot.card_id)) is not None
        }
        header = format_reading_header(
            slots=slots, cards=cards, spread_code=spread_code
        )
        message = format_reading_message(
            header=header, interpretation=interpretation or ""
        )
        output = self._images.compose_reading_image(
            slots=slots,
            output_path=f"reading_{reading_id}.jpg",
        )
        await self._messenger.send_chat_action(
            chat_id=telegram_chat_id, action="upload_photo"
        )
        await self._messenger.send_photo(chat_id=telegram_chat_id, photo_path=output)
        await self._messenger.send_long_text(
            chat_id=telegram_chat_id, text=message, parse_mode="HTML"
        )
