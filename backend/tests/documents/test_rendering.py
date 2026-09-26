from types import SimpleNamespace

import fitz

from app.services.documents.rendering import render_certificate


def test_rendering_replaces_an_inline_pdf_token_without_leaving_it_visible() -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 100), "Recognition for {{student_name}}")
    template = document.tobytes()
    document.close()
    field = SimpleNamespace(
        field_name="student_name", page_number=1, x=145, y=87, width=100, height=18,
        font_family="helv", custom_font_storage_key=None, font_size=11, text_color="#000000",
    )

    output = render_certificate(
        template, [field], {"student_name": "Awais Khan"}, verification_url="https://example.test/verify/x",
        required_field_names=frozenset({"student_name"}),
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    text = rendered[0].get_text()
    rendered.close()
    assert "{{student_name}}" not in text
    # Amsterdam Four encodes spaces as non-breaking spaces in extracted text.
    assert "Awais Khan" in text.replace("\u00a0", " ")


def test_rendering_replaces_a_complete_tagged_paragraph_without_old_text() -> None:
    document = fitz.open()
    page = document.new_page()
    paragraph = "In recognition of {{student_name}} ({{roll_number}}) for {{activity_name}} on {{activity_date}}."
    page.insert_textbox(fitz.Rect(80, 120, 500, 170), paragraph, fontsize=10, color=(0, 0.4, 0.8))
    template = document.tobytes()
    document.close()
    fields = [
        SimpleNamespace(field_name=name, page_number=1, x=80, y=120, width=80, height=16,
                        font_family="helv", custom_font_storage_key=None, font_size=10, text_color="#000000")
        for name in ("student_name", "roll_number", "activity_name", "activity_date")
    ]

    output = render_certificate(
        template,
        fields,
        {"student_name": "Awais Khan", "roll_number": "2K22-340", "activity_name": "Plantation Drive", "activity_date": "2026-09-25"},
        verification_url="https://example.test/verify/x",
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    text = rendered[0].get_text().replace("\u00a0", " ")
    rendered.close()
    assert "{{student_name}}" not in text
    assert "Awais Khan (2K22-340) for Plantation Drive on 2026-09-25." in text
