"""Tests for interpretation section handling."""

from src.application.interpretation import (
    finalize_interpretation,
    validate_interpretation,
)
from src.application.interpretation_sections import (
    clamp_with_sections,
    detect_section,
    merge_orphan_labels,
    missing_sections,
    normalize_section_prefix,
    thin_sections,
)
from src.core.settings.constants import SPREAD_THREE


def test_detect_section_from_paragraph_start() -> None:
    assert detect_section("В будущем вас ждёт перемена.") == "Будущее"
    assert detect_section("Прошлое: было трудно.") == "Прошлое"
    assert detect_section("**Будущее:** светлые перспективы.") == "Будущее"


def test_detect_section_ignores_inline_future_word() -> None:
    past = "В прошлом вы готовили почву для будущего."
    assert detect_section(past) == "Прошлое"


def test_normalize_section_prefix_strips_emphasis() -> None:
    assert normalize_section_prefix("**Будущее:** текст").startswith("Будущее:")


def test_missing_sections_reports_absent_labels() -> None:
    text = "Прошлое: было.\n\nНастоящее: сейчас."
    missing = missing_sections(text, spread_code=SPREAD_THREE)
    assert missing == ["Будущее"]


def test_clamp_preserves_future_section() -> None:
    past = "Прошлое: " + ("А" * 400)
    present = "Настоящее: " + ("Б" * 400)
    future = "Будущее: " + ("В" * 400)
    conclusion = "Вывод: " + ("Г" * 400)
    text = "\n\n".join([past, present, future, conclusion])
    clamped = clamp_with_sections(text, max_chars=1600, spread_code=SPREAD_THREE)
    assert "Будущее:" in clamped
    assert "Прошлое:" in clamped
    assert "Настоящее:" in clamped


def test_finalize_three_keeps_future() -> None:
    past = "Прошлое: " + ("А" * 400)
    present = "Настоящее: " + ("Б" * 400)
    future = "Будущее: " + ("В" * 400)
    conclusion = "Вывод: " + ("Г" * 400)
    text = "\n\n".join([past, present, future, conclusion])
    cleaned = finalize_interpretation(text, spread_code=SPREAD_THREE)
    assert "Будущее:" in cleaned


def test_validate_missing_section_from_pre_clamp() -> None:
    pre = "Прошлое: было.\n\nНастоящее: сейчас."
    final = finalize_interpretation(pre, spread_code=SPREAD_THREE)
    issues = validate_interpretation(
        final,
        spread_code=SPREAD_THREE,
        pre_clamp_text=pre,
    )
    assert "missing_section:Будущее" in issues


def test_merge_orphan_label_attaches_following_content() -> None:
    raw = "Прошлое:\n\n" + ("А" * 120) + "\n\nНастоящее:\n\n" + ("Б" * 120)
    merged = merge_orphan_labels(raw)
    assert merged.startswith("Прошлое:\n")
    assert "Настоящее:\n" in merged
    assert thin_sections(merged, spread_code=SPREAD_THREE) == ["Будущее"]


def test_merge_orphan_labels_does_not_merge_stacked_headers() -> None:
    body = "В" * 120
    raw = f"Прошлое:\n\nНастоящее:\n\nБудущее:\n\n{body}"
    merged = merge_orphan_labels(raw)
    assert merged.startswith("Прошлое:\n\nНастоящее:\n\nБудущее:\n")
    assert merged.endswith(body)
    assert thin_sections(merged, spread_code=SPREAD_THREE) == ["Прошлое", "Настоящее"]


def test_validate_rejects_label_only_sections() -> None:
    pre = "Прошлое:\n\nНастоящее:\n\nБудущее:\n\n" + ("В" * 120)
    final = finalize_interpretation(pre, spread_code=SPREAD_THREE)
    issues = validate_interpretation(
        final,
        spread_code=SPREAD_THREE,
        pre_clamp_text=pre,
    )
    assert "thin_section:Прошлое" in issues
    assert "thin_section:Настоящее" in issues


def test_prepare_fixes_label_then_content_pattern() -> None:
    from src.application.interpretation import prepare_interpretation_text

    past_body = "В прошлом вы много работали без отдачи. " + ("А" * 80)
    present_body = "Сейчас вы чувствуете опустошение. " + ("Б" * 80)
    future_body = "В будущем откроются новые возможности. " + ("В" * 80)
    raw = (
        f"Прошлое:\n\n{past_body}\n\n"
        f"Настоящее:\n\n{present_body}\n\n"
        f"Будущее:\n\n{future_body}"
    )
    prepared = prepare_interpretation_text(raw)
    issues = validate_interpretation(
        finalize_interpretation(prepared, spread_code=SPREAD_THREE),
        spread_code=SPREAD_THREE,
        pre_clamp_text=prepared,
    )
    assert thin_sections(prepared, spread_code=SPREAD_THREE) == []
    assert not any(issue.startswith("thin_section:") for issue in issues)
