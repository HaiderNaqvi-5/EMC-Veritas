from io import BytesIO

import fitz
from reportlab.pdfgen import canvas

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


def test_analysis_detects_common_certificate_placeholders_with_positions() -> None:
    result = analysis.detect_certificate_placeholders(
        _pdf_with_page_text("Student Name\nStudent Roll Number\nActivity Name\nActivity Date")
    )

    assert [field.field_name for field in result] == [
        "student_name",
        "roll_number",
        "activity_name",
        "activity_date", "qr_code",
    ]
    assert all(field.page_number == 1 and field.width > 0 and field.height > 0 for field in result)
    # The synthetic PDF uses Helvetica.  Keep this expectation aligned with
    # style detection rather than the legacy Times fallback.
    assert result[0].font_family == "helv"
    assert result[0].font_size == 11
    assert result[0].text_color == "#000000"
    assert result[-1].detected_text == "dedicated QR square"


def test_analysis_combines_split_placeholder_fragments() -> None:
    first = fitz.Rect(10, 20, 40, 35)
    second = fitz.Rect(40, 20, 90, 35)

    assert analysis._combined_placeholder_rect([first, second]) == fitz.Rect(10, 20, 90, 35)


def test_analysis_detects_tracked_placeholders_exported_as_split_glyphs() -> None:
    output = BytesIO()
    pdf = canvas.Canvas(output)
    text = pdf.beginText(72, 720)
    text.setCharSpace(2)
    for placeholder in (
        "{{roll_number}}",
        "{{activity_name}}",
        "{{activity_date}}",
    ):
        text.textLine(placeholder)
    pdf.drawText(text)
    pdf.save()

    fields = analysis.detect_certificate_placeholders(output.getvalue())
    names = {field.field_name for field in fields}

    assert {"roll_number", "activity_name", "activity_date"} <= names


def test_detected_fields_stay_in_bounds_without_adjacent_line_overlap() -> None:
    document = fitz.open()
    page = document.new_page(width=842, height=595)
    page.insert_text((250, 300), "Student Roll Number")
    page.insert_text((250, 322), "Activity Name")
    page.insert_text((700, 500), "Serial No")
    pdf_bytes = document.tobytes()
    document.close()

    fields = analysis.detect_certificate_placeholders(pdf_bytes)
    by_name = {field.field_name: field for field in fields}

    assert by_name["verification_id"].x + by_name["verification_id"].width <= 842
    assert by_name["roll_number"].y + by_name["roll_number"].height <= by_name["activity_name"].y


def test_analysis_accepts_the_legacy_serial_placeholder_syntax() -> None:
    fields = analysis.detect_certificate_placeholders(_pdf_with_page_text("{{serial_no.}}"))

    verification = next(field for field in fields if field.field_name == "verification_id")
    assert verification.detected_text == "{{serial_no.}}"


def test_analysis_prefers_an_explicit_qr_tag_over_a_decorative_frame() -> None:
    fields = analysis.detect_certificate_placeholders(_pdf_with_page_text("{{qr_code}}"))

    qr = next(field for field in fields if field.field_name == "qr_code")
    assert qr.detected_text == "{{qr_code}}"


def test_analysis_expands_an_explicit_qr_tag_to_its_enclosing_panel() -> None:
    document = fitz.open()
    page = document.new_page(width=600, height=400)
    panel = fitz.Rect(48, 260, 108, 330)
    page.draw_rect(panel)
    page.insert_text((54, 295), "{{qr_code}}")
    pdf_bytes = document.tobytes()
    document.close()

    fields = analysis.detect_certificate_placeholders(pdf_bytes)
    qr = next(field for field in fields if field.field_name == "qr_code")

    assert qr.detected_text == "{{qr_code}}"
    assert qr.width >= 50
    assert qr.height >= 50
    assert qr.x >= panel.x0
    assert qr.y >= panel.y0


def test_analysis_uses_the_square_area_inside_a_wide_qr_panel() -> None:
    document = fitz.open()
    page = document.new_page(width=600, height=400)
    panel = fitz.Rect(48, 260, 132, 328)
    page.draw_rect(panel)
    page.insert_text((70, 295), "{{qr_code}}")
    pdf_bytes = document.tobytes()
    document.close()

    qr = next(field for field in analysis.detect_certificate_placeholders(pdf_bytes) if field.field_name == "qr_code")

    assert qr.width >= 60
    assert qr.height >= 60


def test_analysis_detects_dynamic_signature_placeholders() -> None:
    result = analysis.detect_certificate_placeholders(
        _pdf_with_page_text("{{signature_dsa}}\n{{signature_hod}}")
    )

    by_name = {field.field_name: field for field in result}
    assert by_name["signature_dsa"].detected_text == "{{signature_dsa}}"
    assert by_name["signature_hod"].detected_text == "{{signature_hod}}"
    assert by_name["signature_dsa"].width >= 160
    assert by_name["signature_dsa"].height >= 60
