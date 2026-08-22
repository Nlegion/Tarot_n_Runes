"""Pillow image composition."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.core.settings.config import IMAGES_DIR, TMP_DIR
from src.domain.entities import SlotDraw


class ImageComposer:
    def __init__(
        self, *, images_dir: Path | None = None, tmp_dir: Path | None = None
    ) -> None:
        self._images_dir = images_dir or IMAGES_DIR
        self._tmp_dir = tmp_dir or TMP_DIR
        self._tmp_dir.mkdir(parents=True, exist_ok=True)

    def card_image_path(self, card_id: int) -> str:
        return str(self._images_dir / f"{card_id}.jpg")

    def compose_reading_image(
        self, *, slots: tuple[SlotDraw, ...], output_path: str
    ) -> str:
        images: list[Image.Image] = []
        for slot in slots:
            path = self.card_image_path(slot.card_id)
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
        out = self._tmp_dir / output_path
        result.save(out, format="JPEG", quality=90)
        for img in images:
            img.close()
        result.close()
        return str(out)
