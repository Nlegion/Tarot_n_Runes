import pytest

from src.domain.entities import SlotDraw
from src.infrastructure.imaging.composer import ImageComposer


def test_compose_three_cards(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from PIL import Image

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    for card_id in (1, 2, 3):
        path = images_dir / f"{card_id}.jpg"
        Image.new("RGB", (100, 150), color=(card_id * 40, 20, 20)).save(path)
    composer = ImageComposer(
        images_dir=images_dir,
        tmp_dir=tmp_path / "out",
    )
    slots = (
        SlotDraw("PAST", 0, 1, False),
        SlotDraw("PRESENT", 1, 2, True),
        SlotDraw("FUTURE", 2, 3, False),
    )
    output = composer.compose_reading_image(slots=slots, output_path="spread.jpg")
    assert (tmp_path / "out" / "spread.jpg").exists()
    with Image.open(output) as img:
        assert img.width > 100
