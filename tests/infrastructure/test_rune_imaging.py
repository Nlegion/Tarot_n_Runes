"""Tests for in-memory rune oval composition."""

from io import BytesIO

from PIL import Image

from src.core.settings.config import RUNES_FONT_PATH
from src.domain.entities import SlotDraw
from src.infrastructure.imaging.rune_composer import RuneImageComposer


def test_compose_odin_empty_and_fehu() -> None:
    glyphs = {1: "\u16a0", 25: None}
    composer = RuneImageComposer(glyphs=glyphs, font_path=RUNES_FONT_PATH)
    fehu = composer.compose_reading_image(slots=(SlotDraw("T1", 0, 1, False),))
    odin = composer.compose_reading_image(slots=(SlotDraw("T1", 0, 25, False),))
    assert fehu[:2] == b"\xff\xd8"
    assert odin[:2] == b"\xff\xd8"
    assert fehu != odin


def test_compose_three_runes_wider() -> None:
    glyphs = {1: "\u16a0", 2: "\u16a2", 3: "\u16a6"}
    composer = RuneImageComposer(glyphs=glyphs, font_path=RUNES_FONT_PATH)
    single = composer.compose_reading_image(slots=(SlotDraw("T1", 0, 1, False),))
    three = composer.compose_reading_image(
        slots=(
            SlotDraw("PAST", 0, 1, False),
            SlotDraw("PRESENT", 1, 2, True),
            SlotDraw("FUTURE", 2, 3, False),
        )
    )
    with Image.open(BytesIO(single)) as one, Image.open(BytesIO(three)) as many:
        assert many.width > one.width


def test_inverted_differs_from_upright() -> None:
    glyphs = {1: "\u16a0"}
    composer = RuneImageComposer(glyphs=glyphs, font_path=RUNES_FONT_PATH)
    upright = composer.compose_reading_image(slots=(SlotDraw("T1", 0, 1, False),))
    inverted = composer.compose_reading_image(slots=(SlotDraw("T1", 0, 1, True),))
    assert upright != inverted
