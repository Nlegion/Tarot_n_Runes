"""Tests for in-memory image composition."""

from io import BytesIO

from PIL import Image

from src.domain.entities import SlotDraw
from src.infrastructure.imaging.composer import ImageComposer


def test_compose_three_cards(tmp_path) -> None:
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    for card_id in (1, 2, 3):
        path = images_dir / f"{card_id}.jpg"
        Image.new("RGB", (100, 150), color=(card_id * 40, 20, 20)).save(path)
    composer = ImageComposer(images_dir=images_dir)
    slots = (
        SlotDraw("PAST", 0, 1, False),
        SlotDraw("PRESENT", 1, 2, True),
        SlotDraw("FUTURE", 2, 3, False),
    )
    photo_bytes = composer.compose_reading_image(slots=slots)
    assert isinstance(photo_bytes, bytes)
    assert photo_bytes[:2] == b"\xff\xd8"  # JPEG SOI
    with Image.open(BytesIO(photo_bytes)) as img:
        assert img.width > 100
