import re
from collections.abc import Iterable, Mapping
from datetime import date
from io import BytesIO
from pathlib import Path

import fitz

from app.models.domain import TemplateField
from app.services.documents.qr_image import qr_png
from app.services.documents.text_fit import fit_font_size
from app.services.templates.fields import REQUIRED_CERTIFICATE_FIELDS


class CertificateRenderingError(ValueError):
    """Raised when an approved PDF template cannot produce a safe certificate."""


def _text_width(text: str, size: float, font_family: str, font_bytes: bytes | None = None) -> float:
    if font_bytes is not None:
        return fitz.Font(fontbuffer=font_bytes).text_length(text, fontsize=size)
    return fitz.get_text_length(text, fontname=font_family, fontsize=size)


def _color(value: str) -> tuple[float, float, float]:
    if len(value) != 7 or not value.startswith("#"):
        raise CertificateRenderingError("Template text color is invalid")
    try:
        return tuple(int(value[index : index + 2], 16) / 255 for index in (1, 3, 5))  # type: ignore[return-value]
    except ValueError as error:
        raise CertificateRenderingError("Template text color is invalid") from error


def _insert_text(
    page: fitz.Page,
    field: TemplateField,
    value: str,
    custom_fonts: Mapping[str, bytes],
) -> None:
    if field.width <= 0 or field.height < 6:
        raise CertificateRenderingError(f"Template field '{field.field_name}' has an invalid box")
    font_family = getattr(field, "font_family", "helv")
    custom_font_key = getattr(field, "custom_font_storage_key", None)
    if field.field_name == "student_name" and font_family != "custom" and custom_font_key is None:
        font_bytes = (Path(__file__).resolve().parents[2] / "assets" / "Amsterdam.ttf").read_bytes()
        font_name = "EMCAmsterdam"
        try:
            page.insert_font(fontname=font_name, fontbuffer=font_bytes)
        except (RuntimeError, ValueError) as error:
            raise CertificateRenderingError("Amsterdam font for the student name is unreadable") from error
    elif font_family == "custom":
        if not custom_font_key or custom_font_key not in custom_fonts:
            raise CertificateRenderingError(
                f"Template field '{field.field_name}' references an unavailable custom font"
            )
        font_bytes = custom_fonts[custom_font_key]
        font_name = f"EMCF{abs(hash(custom_font_key)) % 10_000_000}"
        try:
            page.insert_font(fontname=font_name, fontbuffer=font_bytes)
        except (RuntimeError, ValueError) as error:
            raise CertificateRenderingError(
                f"Custom font for template field '{field.field_name}' is unreadable"
            ) from error
    elif font_family in {"helv", "tiro", "cour"} and custom_font_key is None:
        font_bytes = None
        font_name = font_family
    else:
        raise CertificateRenderingError("Template font is invalid")
    preferred = getattr(field, "font_size", None)
    maximum = min(preferred or 18, field.height - 2)
    try:
        font_size = fit_font_size(
            value,
            field.width,
            maximum,
            lambda text, size: _text_width(text, size, font_name, font_bytes),
        )
        text_width = _text_width(value, font_size, font_name, font_bytes)
    except (RuntimeError, ValueError) as error:
        raise CertificateRenderingError(
            f"Custom font for template field '{field.field_name}' is unreadable"
        ) from error
    if font_size <= 4:
        raise CertificateRenderingError(f"Value for template field '{field.field_name}' does not fit")
    point = fitz.Point(field.x + max((field.width - text_width) / 2, 0), field.y + (field.height + font_size) / 2)
    page.insert_text(
        point,
        value,
        fontname=font_name,
        fontsize=font_size,
        color=_color(getattr(field, "text_color", "#000000")),
    )


def _insert_qr(page: fitz.Page, field: TemplateField, verification_url: str) -> None:
    if field.width <= 0 or field.height <= 0:
        raise CertificateRenderingError("Template QR field has an invalid box")
    rectangle = fitz.Rect(field.x, field.y, field.x + field.width, field.y + field.height)
    page.insert_image(rectangle, stream=qr_png(verification_url), keep_proportion=True)


def _insert_image(page: fitz.Page, field: TemplateField, image_bytes: bytes) -> None:
    if field.width <= 0 or field.height <= 0:
        raise CertificateRenderingError(f"Template field '{field.field_name}' has an invalid box")
    rectangle = fitz.Rect(field.x, field.y, field.x + field.width, field.y + field.height)
    try:
        page.insert_image(rectangle, stream=image_bytes, keep_proportion=True)
    except (ValueError, RuntimeError) as error:
        raise CertificateRenderingError(
            f"Signature image for template field '{field.field_name}' is unreadable"
        ) from error


def _remove_inline_placeholder(page: fitz.Page, field_name: str) -> None:
    """Erase a literal {{field_name}} token before rendering its real value.

    This makes templates authored as a single flowing paragraph work without
    requiring a user to manually drag a field into a separate blank space.
    """
    tokens = ["{{" + field_name + "}}"]
    # Older, human-authored templates sometimes reserve the serial reference
    # with this label instead of the machine field name.
    if field_name == "verification_id":
        tokens.extend(("{{Serial No.}}", "{{Serial No}}", "{{Serial Number}}"))
    rectangles: list[fitz.Rect] = []
    for token in tokens:
        rectangles = page.search_for(token)
        if rectangles:
            break
    if not rectangles:
        return
    combined = fitz.Rect(rectangles[0])
    for rectangle in rectangles[1:]:
        combined.include_rect(rectangle)
    page.add_redact_annot(combined, fill=(1, 1, 1))


def _source_text_style(page: fitz.Page, rectangle: fitz.Rect) -> tuple[str, float, tuple[float, float, float]]:
    """Return a safe approximation of the style visibly used in a text block."""
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if fitz.Rect(span["bbox"]).intersects(rectangle):
                    source_font = str(span.get("font", "")).lower()
                    font = "cour" if "cour" in source_font else "tiro" if "times" in source_font else "helv"
                    color = int(span.get("color", 0))
                    return font, float(span.get("size", 10)), tuple(color >> shift & 255 for shift in (16, 8, 0))
    return "helv", 10, (14, 135, 204)


def _paragraph_rectangle(page: fitz.Page, rectangle: fitz.Rect) -> fitz.Rect:
    """Provide enough room to redraw a paragraph, without touching nearby content."""
    return fitz.Rect(
        max(36, rectangle.x0 - 28),
        max(36, rectangle.y0 - 10),
        min(page.rect.width - 36, rectangle.x1 + 28),
        min(page.rect.height - 36, rectangle.y1 + 20),
    )


def _block_text_from_words(page: fitz.Page, rectangle: fitz.Rect) -> str:
    """Reconstruct PDF prose from positioned words, preserving word boundaries.

    Canva and similar tools often split a phrase into several drawing spans.
    Raw span concatenation can turn ``His leadership`` into
    ``Hisleadership``.  The word list carries the true word boundaries.
    """
    lines: dict[tuple[int, int], list[tuple[float, str]]] = {}
    for x0, y0, x1, y1, word, block_number, line_number, _word_number in page.get_text("words"):
        word_rect = fitz.Rect(x0, y0, x1, y1)
        if not word_rect.intersects(rectangle):
            continue
        lines.setdefault((block_number, line_number), []).append((x0, word))
    return " ".join(
        " ".join(word for _x, word in sorted(words))
        for _line, words in sorted(lines.items())
    )


def _paragraph_from_tagged_block(page: fitz.Page, values: Mapping[str, str]) -> tuple[fitz.Rect, str, set[str], str, float, tuple[float, float, float]] | None:
    """Find a paragraph authored with field tags and make it one clean block.

    The author writes normal prose such as ``... {{roll_number}} ...`` in the
    PDF.  This replaces the *whole* text block, not just the tags, so the old
    paragraph cannot remain visible beneath replacement values.
    """
    token_pattern = re.compile(r"\{\{(student_name|roll_number|activity_name|activity_date)\}\}")
    for block in page.get_text("dict").get("blocks", []):
        if "lines" not in block:
            continue
        text = _block_text_from_words(page, fitz.Rect(block["bbox"]))
        names = set(token_pattern.findall(text))
        if len(names) < 2 or not names.issubset(values):
            continue
        rectangle = _paragraph_rectangle(page, fitz.Rect(block["bbox"]))
        content = token_pattern.sub(lambda match: values[match.group(1)], text).strip()
        font, size, rgb = _source_text_style(page, rectangle)
        page.add_redact_annot(rectangle, fill=(1, 1, 1))
        return rectangle, content, names, font, size, rgb
    return None


def _inline_activity_paragraph(page: fitz.Page, values: Mapping[str, str]) -> tuple[fitz.Rect, str, set[str], str, float, tuple[int, int, int]] | None:
    """Replace a flowing certificate sentence as one typographic block.

    A PDF stores the words of a paragraph as independent drawing operations.
    Removing only placeholder words therefore leaves unnatural gaps.  For the
    standard EMC recognition sentence, replace the complete paragraph with one
    centred line-wrapped block instead.
    """
    start = page.search_for("In recognition")
    end = page.search_for("successful execution of the activity.")
    needed = {"roll_number", "activity_name", "activity_date"}
    if not start or not end or not needed.issubset(values):
        return None
    first, last = start[0], end[-1]
    source_blocks = [
        fitz.Rect(block["bbox"])
        for block in page.get_text("dict").get("blocks", [])
        if "lines" in block
        # Include only paragraph blocks fully between its first and final
        # lines. A tall decorative student-name span can overlap this range
        # at the edge and must never enlarge the paragraph wipe area.
        and fitz.Rect(block["bbox"]).y0 >= first.y0 - 2
        and fitz.Rect(block["bbox"]).y1 <= last.y1 + 2
    ]
    combined = fitz.Rect(first)
    for block in source_blocks:
        combined.include_rect(block)
    combined.include_rect(last)
    rectangle = _paragraph_rectangle(page, combined)
    text = (
        f"In recognition of {values['roll_number']}, for outstanding efforts in organizing "
        f"and managing {values['activity_name']} on {values['activity_date']} under the EMC. "
        "Their leadership, coordination, and commitment significantly contributed to the "
        "successful execution of the activity."
    )
    page.add_redact_annot(rectangle, fill=(1, 1, 1))
    return rectangle, text, needed, "helv", 10, (14, 135, 204)


def _render_activity_paragraph(
    page: fitz.Page,
    rectangle: fitz.Rect,
    text: str,
    font: str,
    font_size: float,
    rgb: tuple[int, int, int],
) -> None:
    size = min(max(font_size, 5), 16)
    while size >= 5:
        result = page.insert_textbox(
            rectangle,
            text,
            fontname=font,
            fontsize=size,
            color=tuple(channel / 255 for channel in rgb),
            align=fitz.TEXT_ALIGN_CENTER,
            lineheight=1.15,
        )
        if result >= 0:
            return
        size -= 0.5
    raise CertificateRenderingError("Activity paragraph does not fit its detected template area")


def render_certificate(
    template_pdf: bytes,
    fields: Iterable[TemplateField],
    values: Mapping[str, str | date],
    *,
    verification_url: str,
    watermark: str | None = None,
    image_values: Mapping[str, bytes] | None = None,
    custom_fonts: Mapping[str, bytes] | None = None,
    required_field_names: frozenset[str] = REQUIRED_CERTIFICATE_FIELDS,
) -> bytes:
    """Overlay configured fields and an optional QR code onto a PDF certificate template.

    Field coordinates use one-based PDF page numbers and point units. The template itself is
    never changed in Storage; this returns a new, immutable issued-document byte stream.
    """
    field_list = list(fields)
    configured_names = {field.field_name for field in field_list}
    missing = required_field_names - configured_names
    if missing:
        raise CertificateRenderingError(
            "Template is missing required fields: " + ", ".join(sorted(missing))
        )

    normalized_values = {
        name: value.isoformat() if isinstance(value, date) else str(value)
        for name, value in values.items()
    }
    images = image_values or {}
    fonts = custom_fonts or {}
    unknown_images = set(images) - configured_names
    if unknown_images:
        raise CertificateRenderingError(
            "Template is missing image fields: " + ", ".join(sorted(unknown_images))
        )
    needed_values = configured_names - {"qr_code", *images}
    absent_values = sorted(name for name in needed_values if name not in normalized_values)
    if absent_values:
        raise CertificateRenderingError(
            "Certificate data is missing values for: " + ", ".join(absent_values)
        )

    try:
        document = fitz.open(stream=template_pdf, filetype="pdf")
    except fitz.FileDataError as error:
        raise CertificateRenderingError("Template is not a readable PDF") from error

    try:
        paragraph_jobs: dict[int, tuple[fitz.Rect, str, str, float, tuple[int, int, int]]] = {}
        paragraph_fields: set[tuple[int, str]] = set()
        # Paragraph replacement is derived from the PDF itself, not from the
        # saved box configuration. Older templates can carry imperfect field
        # records, but their visible certificate paragraph must still be
        # removed completely before the fresh paragraph is drawn.
        for page_number in range(1, document.page_count + 1):
            page = document[page_number - 1]
            job = _paragraph_from_tagged_block(page, normalized_values)
            if job is None:
                job = _inline_activity_paragraph(page, normalized_values)
            if job:
                rectangle, text, replaced_names, font, size, rgb = job
                paragraph_jobs[page_number] = rectangle, text, font, size, rgb
                paragraph_fields.update((page_number, name) for name in replaced_names)
        for field in field_list:
            if field.page_number < 1 or field.page_number > document.page_count:
                raise CertificateRenderingError(
                    f"Template field '{field.field_name}' references an invalid page"
                )
            if (field.page_number, field.field_name) not in paragraph_fields:
                _remove_inline_placeholder(document[field.page_number - 1], field.field_name)
        for page in document:
            page.apply_redactions()
        for page_number, (rectangle, text, font, size, rgb) in paragraph_jobs.items():
            _render_activity_paragraph(document[page_number - 1], rectangle, text, font, size, rgb)
        for field in field_list:
            page = document[field.page_number - 1]
            if field.field_name == "qr_code":
                _insert_qr(page, field, verification_url)
            elif field.field_name in images:
                _insert_image(page, field, images[field.field_name])
            elif (field.page_number, field.field_name) in paragraph_fields:
                continue
            else:
                _insert_text(page, field, normalized_values[field.field_name], fonts)
        if watermark:
            for page in document:
                center = fitz.Point(page.rect.width / 2 - 110, page.rect.height / 2)
                page.insert_text(
                    center,
                    watermark,
                    fontname="helv",
                    fontsize=42,
                    color=(0.75, 0.75, 0.75),
                    fill_opacity=0.45,
                )
        output = BytesIO()
        document.save(output, garbage=4, deflate=True)
        return output.getvalue()
    finally:
        document.close()
