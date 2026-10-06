from types import SimpleNamespace

import fitz

from app.services.documents.rendering import _leadership_content, render_certificate


def test_leadership_content_omits_the_society_clause_for_an_overall_ec_role() -> None:
    text = _leadership_content(
        "The Club recognizes {{student_name}} for serving as {{role}} of {{society_name}} during {{session_name}}.",
        {"student_name": "Ayesha Khan", "role": "President", "society_name": "", "session_name": "2K22"},
    )

    assert text == "The Club recognizes Ayesha Khan for serving as President during 2K22."


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


def test_rendering_places_student_name_above_its_underline() -> None:
    document = fitz.open()
    page = document.new_page(width=600, height=400)
    underline_y = 200
    page.draw_line((120, underline_y), (480, underline_y), width=1)
    template = document.tobytes()
    document.close()
    field = SimpleNamespace(
        field_name="student_name", page_number=1, x=160, y=164, width=280, height=36,
        font_family="tiro", custom_font_storage_key=None, font_size=28, text_color="#000000",
    )

    output = render_certificate(
        template, [field], {"student_name": "Awais Khan"}, verification_url="https://example.test/verify/x",
        required_field_names=frozenset({"student_name"}),
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    span = next(
        span
        for block in rendered[0].get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
        if "Awais" in span["text"]
    )
    rendered.close()
    assert span["bbox"][3] < underline_y


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
    text = rendered[0].get_text().replace("\u00a0", " ").replace("\n", " ")
    rendered.close()
    assert "{{student_name}}" not in text
    assert "Awais Khan (2K22-340) for Plantation Drive on 2026-09-25." in text


def test_rendering_keeps_the_roll_number_clause_when_canva_exports_it_as_a_separate_block() -> None:
    document = fitz.open()
    page = document.new_page(width=842, height=596)
    page.insert_text(
        (103, 320),
        "Bearing roll number {{roll_number}}, in recoginzition of outstanding participation.",
        fontsize=12,
    )
    page.insert_textbox(
        fitz.Rect(115, 330, 728, 385),
        "In organizing {{activity_name}} held on {{activity_date}} under the EMC. Their participation, "
        "coordination, and commitment significantly contributed to the successful execution of the activity.",
        fontsize=12,
    )
    # Canva can write this visible line later in the PDF object order despite
    # placing it above the paragraph on the page.
    page.insert_text((267, 225), "This certificate is proudly presented to", fontsize=12)
    template = document.tobytes()
    document.close()
    fields = [
        SimpleNamespace(field_name=name, page_number=1, x=120 + index * 110, y=315, width=100, height=18,
                        font_family="helv", custom_font_storage_key=None, font_size=12, text_color="#000000")
        for index, name in enumerate(("roll_number", "activity_name", "activity_date"))
    ]

    output = render_certificate(
        template,
        fields,
        {"roll_number": "2K23-BSCS-104", "activity_name": "Orientation 2K25", "activity_date": "2025-09-01"},
        verification_url="https://example.test/verify/x",
        required_field_names=frozenset({"roll_number", "activity_name", "activity_date"}),
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    text = rendered[0].get_text().replace("\u00a0", " ").replace("\n", " ")
    paragraph_span = next(
        span
        for block in rendered[0].get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
        if "Bearing roll number" in span["text"]
    )
    rendered.close()
    assert "Bearing roll number 2K23-BSCS-104" in text
    assert "Orientation 2K25 held on 2025-09-01" in text
    assert "This certificate is proudly presented to" in text
    assert paragraph_span["bbox"][1] >= 300
    assert paragraph_span["size"] == 12


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


def test_rendering_keeps_template_artwork_when_replacing_a_paragraph() -> None:
    document = fitz.open()
    page = document.new_page()
    page.draw_rect(fitz.Rect(70, 130, 530, 220), color=None, fill=(0.2, 0.8, 0.4))
    page.draw_line((80, 118), (520, 118), color=(0.1, 0.1, 0.4), width=2)
    page.insert_textbox(
        fitz.Rect(80, 140, 520, 200),
        "In recognition of STUDENT NAME, for outstanding efforts in organizing and managing "
        "ACTIVITY NAME on ACTIVITY DATE under the EMC. His leadership, coordination, and "
        "commitment significantly contributed to the successful execution of the activity.",
        fontsize=10,
    )
    template = document.tobytes()
    document.close()
    fields = [
        SimpleNamespace(field_name=name, page_number=1, x=100 + index * 90, y=140, width=80, height=18,
                        font_family="helv", custom_font_storage_key=None, font_size=10, text_color="#000000")
        for index, name in enumerate(("roll_number", "activity_name", "activity_date"))
    ]

    output = render_certificate(
        template,
        fields,
        {"roll_number": "2K22-340", "activity_name": "Plantation Drive", "activity_date": "2026-09-25"},
        verification_url="https://example.test/verify/x",
        required_field_names=frozenset({"roll_number", "activity_name", "activity_date"}),
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    page = rendered[0]
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
    # The green background (x=90,y=210) and blue underline (x=100,y=118)
    # must still be visible after text-only redaction.
    assert pixmap.pixel(90, 210)[1] > 150
    assert pixmap.pixel(100, 118)[2] > 70
    assert "His leadership" not in page.get_text()
    rendered.close()


def test_rendering_centres_verification_id_below_its_qr_code() -> None:
    document = fitz.open()
    document.new_page(width=600, height=600)
    template = document.tobytes()
    document.close()
    fields = [
        SimpleNamespace(
            field_name="qr_code", page_number=1, x=460, y=420, width=56, height=56,
            font_family="helv", custom_font_storage_key=None, font_size=10, text_color="#000000",
        ),
        # Simulate a detection box that was too wide and too close to the edge.
        SimpleNamespace(
            field_name="verification_id", page_number=1, x=520, y=510, width=120, height=16,
            font_family="helv", custom_font_storage_key=None, font_size=11, text_color="#000000",
        ),
    ]

    output = render_certificate(
        template,
        fields,
        {"verification_id": "EMC-ABCD1234"},
        verification_url="https://example.test/verify/EMC-ABCD1234",
        required_field_names=frozenset(),
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    serial = next(span for block in rendered[0].get_text("dict")["blocks"] for line in block.get("lines", []) for span in line["spans"] if "EMC-ABCD1234" in span["text"])
    rendered.close()
    serial_center = (serial["bbox"][0] + serial["bbox"][2]) / 2
    assert abs(serial_center - 488) < 3
    assert serial["bbox"][1] >= 480


def test_rendering_expands_a_saved_tiny_qr_tag_box_to_its_panel() -> None:
    document = fitz.open()
    page = document.new_page(width=600, height=600)
    panel = fitz.Rect(50, 420, 110, 490)
    page.draw_rect(panel)
    template = document.tobytes()
    document.close()
    field = SimpleNamespace(
        field_name="qr_code", page_number=1, x=58, y=448, width=34, height=14,
        font_family="helv", custom_font_storage_key=None, font_size=10, text_color="#000000",
    )

    output = render_certificate(
        template, [field], {}, verification_url="https://example.test/verify/x", required_field_names=frozenset()
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    image = next(item for item in rendered[0].get_images(full=True) if item[2] > 100)
    rectangle = rendered[0].get_image_rects(image[0])[0]
    rendered.close()
    assert rectangle.width >= 50
    assert rectangle.height >= 50


def test_rendering_keeps_the_qr_frame_when_removing_its_placeholder() -> None:
    document = fitz.open()
    page = document.new_page(width=600, height=600)
    panel = fitz.Rect(50, 420, 110, 490)
    page.draw_rect(panel, radius=0.2)
    page.insert_text((58, 455), "{{qr_code}}", fontsize=10)
    template = document.tobytes()
    document.close()
    field = SimpleNamespace(
        field_name="qr_code", page_number=1, x=58, y=442, width=48, height=16,
        font_family="helv", custom_font_storage_key=None, font_size=10, text_color="#000000",
    )

    output = render_certificate(
        template, [field], {}, verification_url="https://example.test/verify/x", required_field_names=frozenset()
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    drawings = rendered[0].get_drawings()
    rendered.close()
    assert any(drawing["rect"].contains(panel) or panel.contains(drawing["rect"]) for drawing in drawings)


def test_rendering_expands_a_saved_tiny_qr_tag_box_to_a_wide_panel() -> None:
    document = fitz.open()
    page = document.new_page(width=600, height=600)
    panel = fitz.Rect(50, 420, 134, 488)
    page.draw_rect(panel)
    template = document.tobytes()
    document.close()
    field = SimpleNamespace(
        field_name="qr_code", page_number=1, x=70, y=448, width=34, height=14,
        font_family="helv", custom_font_storage_key=None, font_size=10, text_color="#000000",
    )

    output = render_certificate(
        template, [field], {}, verification_url="https://example.test/verify/x", required_field_names=frozenset()
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    image = next(item for item in rendered[0].get_images(full=True) if item[2] > 100)
    rectangle = rendered[0].get_image_rects(image[0])[0]
    rendered.close()
    assert rectangle.width >= 60
    assert rectangle.height >= 60


def test_rendering_keeps_verification_id_inside_a_tall_qr_panel() -> None:
    document = fitz.open()
    page = document.new_page(width=600, height=600)
    panel = fitz.Rect(430, 380, 530, 510)
    page.draw_rect(panel)
    template = document.tobytes()
    document.close()
    fields = [
        SimpleNamespace(field_name="qr_code", page_number=1, x=455, y=420, width=36, height=14,
                        font_family="helv", custom_font_storage_key=None, font_size=10, text_color="#000000"),
        SimpleNamespace(field_name="verification_id", page_number=1, x=300, y=540, width=120, height=16,
                        font_family="helv", custom_font_storage_key=None, font_size=10, text_color="#000000"),
    ]

    output = render_certificate(
        template, fields, {"verification_id": "EMC-TEST123"},
        verification_url="https://example.test/verify/EMC-TEST123", required_field_names=frozenset(),
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    serial = next(
        span
        for block in rendered[0].get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
        if "EMC-TEST123" in span["text"]
    )
    rendered.close()
    assert panel.x0 <= serial["bbox"][0] < serial["bbox"][2] <= panel.x1
    assert panel.y0 <= serial["bbox"][1] < serial["bbox"][3] <= panel.y1


def test_rendering_rebuilds_a_tagged_leadership_letter_body_without_floating_values() -> None:
    document = fitz.open()
    page = document.new_page(width=600, height=700)
    page.insert_text((220, 100), "{{student_name}}", fontsize=16)
    page.insert_text((220, 120), "Roll Number: {{roll_number}}", fontsize=10)
    page.insert_textbox(
        fitz.Rect(80, 160, 520, 310),
        "The Club recognizes {{student_name}} for serving as {{role}} of {{society_name}} during "
        "{{session_name}}, from {{role_start_date}} to {{role_end_date}}.\n\n"
        "Their leadership and commitment strengthened our community.\n\n"
        "Issued on {{issue_date}}.",
        fontsize=10,
    )
    template = document.tobytes()
    document.close()
    names = (
        "student_name", "roll_number", "role", "society_name", "role_start_date",
        "role_end_date", "session_name", "issue_date",
    )
    fields = [
        SimpleNamespace(
            field_name=name, page_number=1, x=290 if name == "roll_number" else 220 if name == "student_name" else 80,
            y=88 if name == "student_name" else 108 if name == "roll_number" else 160,
            width=220, height=26, font_family="helv", custom_font_storage_key=None,
            font_size=10, text_color="#000000",
        )
        for name in names
    ]
    values = {
        "student_name": "Ayesha Khan", "roll_number": "2K22-BSCS-404", "role": "Society Head",
        "society_name": "Media & Graphics", "role_start_date": "2025-05-01",
        "role_end_date": "2026-07-31", "session_name": "Session 2025-26", "issue_date": "2026-10-07",
    }

    output = render_certificate(
        template, fields, values, verification_url="https://example.test/verify/x",
        required_field_names=frozenset(names),
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    text = rendered[0].get_text().replace("\u00a0", " ").replace("\n", " ")
    role_span = next(
        span
        for block in rendered[0].get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
        if "Society Head" in span["text"]
    )
    rendered.close()
    assert "{{role}}" not in text
    assert text.count("Ayesha Khan") == 1
    assert "Roll Number:" in text
    assert "2K22-BSCS-404" in text
    assert "Ayesha Khan for serving as Society Head" in text
    assert "Media & Graphics during Session 2025-26" in text
    assert role_span["bbox"][1] >= 150


def test_leadership_renderer_keeps_title_and_footer_when_issue_date_is_above_body() -> None:
    document = fitz.open()
    page = document.new_page(width=600, height=700)
    page.insert_text((60, 50), "Issue Date: {{issue_date}}", fontsize=10)
    page.insert_text((120, 100), "LETTER OF RECOGNITION", fontsize=18)
    page.insert_textbox(
        fitz.Rect(60, 150, 540, 270),
        "The Club recognizes {{student_name}} as {{role}} during {{session_name}}, from "
        "{{role_start_date}} to {{role_end_date}}. Their service is appreciated.",
        fontsize=10,
    )
    page.insert_text((60, 600), "Original signature block", fontsize=10)
    page.draw_rect(fitz.Rect(260, 570, 320, 630))
    template = document.tobytes()
    document.close()
    names = ("student_name", "role", "society_name", "role_start_date", "role_end_date", "session_name", "issue_date")
    fields = [
        SimpleNamespace(field_name=name, page_number=1, x=60, y=40, width=140, height=18,
                        font_family="helv", custom_font_storage_key=None, font_size=10, text_color="#000000")
        for name in names
    ]
    values = {
        "student_name": "Ayesha Khan", "role": "Society Head", "society_name": "",
        "role_start_date": "2025-05-01", "role_end_date": "2026-07-31",
        "session_name": "2K22", "issue_date": "2026-10-07",
    }

    output = render_certificate(
        template, fields, values, verification_url="https://example.test/verify/x",
        required_field_names=frozenset(names),
    )

    rendered = fitz.open(stream=output, filetype="pdf")
    text = rendered[0].get_text()
    drawings = rendered[0].get_drawings()
    rendered.close()
    assert "LETTER OF RECOGNITION" in text
    assert "Original signature block" in text
    assert any(drawing["rect"].intersects(fitz.Rect(260, 570, 320, 630)) for drawing in drawings)
