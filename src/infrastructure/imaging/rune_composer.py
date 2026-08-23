"""In-memory rune oval composition (Unicode glyphs)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.core.settings.config import RUNES_FONT_PATH
from src.domain.entities import SlotDraw

_TILE_WIDTH = 400
_TILE_HEIGHT = 560
_BG_COLOR = (18, 22, 32)
_OVAL_OUTLINE = (212, 175, 55)
_OVAL_FILL = (28, 34, 48)
_GLYPH_COLOR = (240, 230, 200)
_OVAL_MARGIN_X = 70
_OVAL_MARGIN_Y = 90
_GLYPH_FONT_SIZE = 180


class RuneImageComposer:
    def __init__(
        self,
        *,
        glyphs: dict[int, str | None],
        font_path: Path | None = None,
    ) -> None:
        self._glyphs = glyphs
        path = font_path or RUNES_FONT_PATH
        if not path.exists():
            raise FileNotFoundError(f"Rune font not found: {path}")
        self._font = ImageFont.truetype(str(path), size=_GLYPH_FONT_SIZE)
        self._validate_glyphs()

    def _validate_glyphs(self) -> None:
        for rune_id, glyph in self._glyphs.items():
            if glyph is None:
                continue
            if not glyph:
                raise ValueError(f"Empty glyph for rune {rune_id}")

    def compose_reading_image(self, *, slots: tuple[SlotDraw, ...]) -> bytes:
        images: list[Image.Image] = []
        for slot in slots:
            tile = self._render_tile(rune_id=slot.card_id)
            if slot.is_inverted:
                tile = tile.rotate(180)
            images.append(tile)
        if len(images) == 1:
            result = images[0]
        else:
            total_width = sum(img.width for img in images)
            result = Image.new("RGB", (total_width, _TILE_HEIGHT), color=_BG_COLOR)
            offset = 0
            for img in images:
                result.paste(img, (offset, 0))
                offset += img.width
        buffer = BytesIO()
        result.save(buffer, format="JPEG", quality=90)
        for img in images:
            img.close()
        if result is not images[0]:
            result.close()
        return buffer.getvalue()

    def _render_tile(self, *, rune_id: int) -> Image.Image:
        img = Image.new("RGB", (_TILE_WIDTH, _TILE_HEIGHT), color=_BG_COLOR)
        draw = ImageDraw.Draw(img)
        box = (
            _OVAL_MARGIN_X,
            _OVAL_MARGIN_Y,
            _TILE_WIDTH - _OVAL_MARGIN_X,
            _TILE_HEIGHT - _OVAL_MARGIN_Y,
        )
        draw.ellipse(box, fill=_OVAL_FILL, outline=_OVAL_OUTLINE, width=4)
        glyph = self._glyphs.get(rune_id)
        if glyph:
            bbox = draw.textbbox((0, 0), glyph, font=self._font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            x = (_TILE_WIDTH - text_w) // 2 - bbox[0]
            y = (_TILE_HEIGHT - text_h) // 2 - bbox[1]
            draw.text((x, y), glyph, font=self._font, fill=_GLYPH_COLOR)
        return img
