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


def test_rendering_preserves_word_boundaries_when_pdf_splits_a_tagged_paragraph() -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((80, 120), "His")
    page.insert_text((101, 120), "leadership for {{student_name}} in {{activity_name}}")
    template = document.tobytes()
    document.close()
    fields = [
        SimpleNamespace(field_name=name, page_number=1, x=80, y=105, width=80, height=16,
                        font_family="helv", custom_font_storage_key=None, font_size=10, text_color="#000000")
        for name in ("student_name", "activity_name")
    ]

    output = render_certificate(
        template,
        fields,
        {"student_name": "Awais Khan", "activity_name": "Plantation Drive"},
        verification_url="https://example.test/verify/x",
        required_field_names=frozenset({"student_name", "activity_name"}),
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    text = rendered[0].get_text().replace("\u00a0", " ")
    rendered.close()
    assert "His leadership for Awais Khan in Plantation Drive" in text


def test_rendering_replaces_legacy_paragraph_even_when_its_saved_field_boxes_are_incomplete() -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_textbox(
        fitz.Rect(80, 120, 500, 190),
        "In recognition of STUDENT NAME, for outstanding efforts in organizing and managing "
        "ACTIVITY NAME on ACTIVITY DATE under the EMC. His leadership, coordination, and "
        "commitment significantly contributed to the successful execution of the activity.",
        fontsize=10,
    )
    template = document.tobytes()
    document.close()
    only_name_field = SimpleNamespace(
        field_name="student_name", page_number=1, x=100, y=90, width=200, height=20,
        font_family="helv", custom_font_storage_key=None, font_size=11, text_color="#000000",
    )

    output = render_certificate(
        template,
        [only_name_field],
        {"student_name": "Awais Khan", "roll_number": "2K22-340", "activity_name": "Plantation Drive", "activity_date": "2026-09-25"},
        verification_url="https://example.test/verify/x",
        required_field_names=frozenset({"student_name"}),
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    text = rendered[0].get_text()
    rendered.close()
    assert "His leadership" not in text
    assert "Their leadership, coordination, and commitment" in text


def test_rendering_replaces_recognition_paragraph_when_the_final_sentence_is_unsearchable() -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_textbox(
        fitz.Rect(80, 120, 500, 180),
        "In recognition of STUDENT NAME, for outstanding efforts in organizing and managing "
        "ACTIVITY NAME on ACTIVITY DATE under the EMC. His leadership, coordination, and "
        "commitment significantly contributed to the successful execution of this event.",
        fontsize=10,
    )
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
    text = rendered[0].get_text()
    rendered.close()
    assert "successful execution of this event" not in text
    assert "Their leadership, coordination, and commitment" in text


def test_rendering_uses_saved_activity_fields_when_pdf_recognition_text_is_unsearchable() -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_textbox(
        fitz.Rect(80, 160, 500, 220),
        "Legacy certificate prose that cannot be identified by the standard text detector.",
        fontsize=10,
    )
    template = document.tobytes()
    document.close()
    fields = [
        SimpleNamespace(field_name="student_name", page_number=1, x=120, y=100, width=220, height=24,
                        font_family="helv", custom_font_storage_key=None, font_size=12, text_color="#000000"),
    ] + [
        SimpleNamespace(field_name=name, page_number=1, x=140 + index * 90, y=160, width=80, height=18,
                        font_family="helv", custom_font_storage_key=None, font_size=10, text_color="#000000")
        for index, name in enumerate(("roll_number", "activity_name", "activity_date"))
    ]

    output = render_certificate(
        template,
        fields,
        {"student_name": "Awais Khan", "roll_number": "2K22-340", "activity_name": "Plantation Drive", "activity_date": "2026-09-25"},
        verification_url="https://example.test/verify/x",
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    text = rendered[0].get_text()
    rendered.close()
    assert "Legacy certificate prose" not in text
    assert "Their leadership, coordination, and commitment" in text
