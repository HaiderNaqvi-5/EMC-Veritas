import fitz

from app.services.templates import analysis


def _pdf_with_page_text(text: str | None) -> bytes:
    document = fitz.open()
    page = document.new_page()
    if text is not None:
        page.insert_text((72, 72), text)
    output = document.tobytes()
    document.close()
    return output


def test_analysis_keeps_embedded_pdf_text_without_ocr(monkeypatch) -> None:
    def fail_if_called(_image):
        raise AssertionError("OCR must not run for embedded PDF text")

    monkeypatch.setattr(analysis.pytesseract, "image_to_string", fail_if_called)

    result = analysis.analyze_pdf_text(_pdf_with_page_text("EMC Certificate"))

    assert result.pages == ["EMC Certificate\n"]
    assert result.ocr_used is False
    assert result.ocr_required is False


def test_analysis_uses_ocr_for_a_scanned_page(monkeypatch) -> None:
    monkeypatch.setattr(analysis.pytesseract, "image_to_string", lambda _image: "Scanned template")

    result = analysis.analyze_pdf_text(_pdf_with_page_text(None))

    assert result.pages == ["Scanned template"]
    assert result.ocr_used is True
    assert result.ocr_required is False


def test_analysis_flags_signature_or_date_labels_for_editor_warning() -> None:
    assert analysis.has_signature_like_content(["President Signature\nDate: 2026-01-01"])
    assert not analysis.has_signature_like_content(["Certificate of participation"])
