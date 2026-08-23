"""Telegram messenger adapter."""

from __future__ import annotations

from io import BytesIO

from src.application.interpretation import split_messages
from src.infrastructure.telegram.client import TelegramClient


class TelegramMessenger:
    def __init__(self, client: TelegramClient) -> None:
        self._client = client

    async def close(self) -> None:
        await self._client.close()

    async def send_message_with_keyboard(
        self, *, chat_id: int, text: str, reply_markup: dict
    ) -> None:
        await self._client.request(
            "sendMessage",
            json={"chat_id": chat_id, "text": text, "reply_markup": reply_markup},
        )

    async def send_message(
        self, *, chat_id: int, text: str, parse_mode: str | None = None
    ) -> int:
        payload: dict = {"chat_id": chat_id, "text": text}
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        response = await self._client.request("sendMessage", json=payload)
        return int(response["result"]["message_id"])

    async def delete_message(self, *, chat_id: int, message_id: int) -> None:
        await self._client.request(
            "deleteMessage",
            json={"chat_id": chat_id, "message_id": message_id},
        )

    async def edit_message(self, *, chat_id: int, message_id: int, text: str) -> None:
        await self._client.request(
            "editMessageText",
            json={"chat_id": chat_id, "message_id": message_id, "text": text},
        )

    async def send_chat_action(self, *, chat_id: int, action: str = "typing") -> None:
        await self._client.request(
            "sendChatAction",
            json={"chat_id": chat_id, "action": action},
        )

    async def send_long_text(
        self, *, chat_id: int, text: str, parse_mode: str | None = None
    ) -> None:
        for chunk in split_messages(text):
            await self.send_message(chat_id=chat_id, text=chunk, parse_mode=parse_mode)

    async def send_photo(
        self, *, chat_id: int, photo_bytes: bytes, caption: str | None = None
    ) -> None:
        files = {"photo": ("reading.jpg", BytesIO(photo_bytes), "image/jpeg")}
        data = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption[:1024]
        await self._client.request(
            "sendPhoto",
            data=data,
            files=files,
        )

    async def answer_callback(self, *, callback_query_id: str, text: str = "") -> None:
        await self._client.request(
            "answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": text},
        )

    async def delete_webhook(self) -> None:
        await self._client.request(
            "deleteWebhook", json={"drop_pending_updates": False}
        )
