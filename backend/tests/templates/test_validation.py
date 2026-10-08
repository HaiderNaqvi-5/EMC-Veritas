from pathlib import Path

import pytest

from app.services.templates.validation import ensure_font


def test_ensure_font_accepts_a_structurally_valid_truetype_font() -> None:
    content = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "assets"
        / "Montserrat-VariableFont_wght.ttf"
    ).read_bytes()

    assert ensure_font("Montserrat.ttf", "font/ttf", content) == "font/ttf"


def test_ensure_font_accepts_browser_specific_mime_type() -> None:
    content = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "assets"
        / "Montserrat-VariableFont_wght.ttf"
    ).read_bytes()

    assert (
        ensure_font("Montserrat.ttf", "application/x-font-ttf", content)
        == "font/ttf"
    )


def test_ensure_font_rejects_a_spoofed_opentype_header() -> None:
    with pytest.raises(ValueError, match="structure is invalid"):
        ensure_font("fake.otf", "font/otf", b"OTTO" + bytes(64))
