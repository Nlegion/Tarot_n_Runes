"""Pillow image composition."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image

from src.core.settings.config import TAROT_IMAGES_DIR
from src.domain.entities import SlotDraw


class ImageComposer:
    def __init__(self, *, images_dir: Path | None = None) -> None:
        self._images_dir = images_dir or TAROT_IMAGES_DIR

    def _card_image_path(self, card_id: int) -> Path:
        return self._images_dir / f"{card_id}.jpg"

    def compose_reading_image(self, *, slots: tuple[SlotDraw, ...]) -> bytes:
        images: list[Image.Image] = []
        for slot in slots:
            path = self._card_image_path(slot.card_id)
            img = Image.open(path).convert("RGB")
            if slot.is_inverted:
                img = img.rotate(180)
            images.append(img)
        if len(images) == 1:
            result = images[0]
        else:
            height = max(img.height for img in images)
            resized = []
            for img in images:
                ratio = height / img.height
                resized.append(img.resize((int(img.width * ratio), height)))
            total_width = sum(img.width for img in resized)
            result = Image.new("RGB", (total_width, height))
            offset = 0
            for img in resized:
                result.paste(img, (offset, 0))
                offset += img.width
        buffer = BytesIO()
        result.save(buffer, format="JPEG", quality=90)
        for img in images:
            img.close()
        if result is not images[0]:
            result.close()
        return buffer.getvalue()
