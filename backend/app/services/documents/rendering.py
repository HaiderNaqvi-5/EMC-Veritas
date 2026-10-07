import re
from collections.abc import Iterable, Mapping
from copy import copy
from datetime import date
from io import BytesIO
from pathlib import Path

import fitz

from app.models.domain import TemplateField
from app.services.documents.qr_image import qr_png
from app.services.documents.text_fit import fit_font_size
from app.services.signatures.image import restore_legacy_signature_alpha
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
    *,
    alignment: str = "center",
    emphasize: bool = True,
) -> None:
    if field.width <= 0 or field.height < 6:
        raise CertificateRenderingError(f"Template field '{field.field_name}' has an invalid box")
    font_family = getattr(field, "font_family", "helv")
    custom_font_key = getattr(field, "custom_font_storage_key", None)
    if field.field_name == "student_name" and font_family != "custom" and custom_font_key is None:
        # IBM Plex Sans is IBM's corporate typeface and provides a clear,
        # modern, professional recipient-name treatment in every document type.
        font_bytes = (Path(__file__).resolve().parents[2] / "assets" / "IBMPlexSans-Medium.ttf").read_bytes()
        font_name = "EMCIBMPlexSansMedium"
        try:
            page.insert_font(fontname=font_name, fontbuffer=font_bytes)
        except (RuntimeError, ValueError) as error:
            raise CertificateRenderingError("IBM Plex font for the student name is unreadable") from error
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
    if field.field_name == "issue_date":
        # Keep the inline metadata date in the same Calibri-compatible face as
        # the leadership letter, rather than inheriting a generic field font.
        font_bytes = (Path(__file__).resolve().parents[2] / "assets" / "Carlito-Regular.ttf").read_bytes()
        font_name = "EMCIssueDateCalibri"
        try:
            page.insert_font(fontname=font_name, fontbuffer=font_bytes)
        except (RuntimeError, ValueError) as error:
            raise CertificateRenderingError("Leadership issue-date font is unreadable") from error
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
    baseline_y = field.y + (field.height + font_size) / 2
    if field.field_name == "issue_date":
        # A date token sits inline after the fixed "Issue Date:" label. Its
        # source bbox starts at the glyph top, so centring in the saved box
        # moves its baseline visibly below the label.
        baseline_y = field.y + font_size
    if field.field_name == "student_name":
        # A recipient name is normally placed immediately above an underline.
        # Reserve a bottom margin so the visible glyphs remain above it.
        baseline_y = field.y + max(4, field.height - font_size * 0.35)
    x = field.x if alignment == "left" else field.x + max((field.width - text_width) / 2, 0)
    point = fitz.Point(x, baseline_y)
    page.insert_text(
        point,
        value,
        fontname=font_name,
        fontsize=font_size,
        color=_color(getattr(field, "text_color", "#000000")),
        render_mode=2 if emphasize else 0,
        border_width=0.04 if emphasize else 1,
    )


def _effective_qr_field(page: fitz.Page, field: TemplateField) -> TemplateField:
    """Expand a saved QR tag box to the QR panel that contains it.

    Earlier template analysis saved the small ``{{qr_code}}`` text bounds.
    Keep those templates usable by resolving the enclosing drawn panel while
    rendering instead of requiring an admin to recreate every template.
    """
    frame = _qr_panel_for_field(page, field)
    if frame is None:
        return field
    size = max(16, min(frame.width, frame.height) - 8)
    effective = copy(field)
    effective.x = frame.x0 + (frame.width - size) / 2
    effective.y = frame.y0 + (frame.height - size) / 2
    effective.width = size
    effective.height = size
    return effective


def _qr_panel_for_field(page: fitz.Page, field: TemplateField) -> fitz.Rect | None:
    """Return the smallest drawn QR panel containing a configured QR field."""
    center = fitz.Point(field.x + field.width / 2, field.y + field.height / 2)
    frames = [
        drawing["rect"]
        for drawing in page.get_drawings()
        # A QR holder can be a little wider than it is tall. Its usable QR
        # area is the largest square inside it, not the narrow tag label.
        if 32 <= min(drawing["rect"].width, drawing["rect"].height) <= 160
        and max(drawing["rect"].width, drawing["rect"].height) <= 180
        and max(drawing["rect"].width, drawing["rect"].height)
        / min(drawing["rect"].width, drawing["rect"].height) <= 1.6
        and drawing["rect"].contains(center)
    ]
    if not frames:
        return None
    return min(frames, key=lambda rectangle: rectangle.width * rectangle.height)


def _insert_qr(page: fitz.Page, field: TemplateField, verification_url: str) -> None:
    field = _effective_qr_field(page, field)
    if field.width <= 0 or field.height <= 0:
        raise CertificateRenderingError("Template QR field has an invalid box")
    rectangle = fitz.Rect(field.x, field.y, field.x + field.width, field.y + field.height)
    page.insert_image(rectangle, stream=qr_png(verification_url), keep_proportion=True)


def _verification_field_below_qr(
    page: fitz.Page, field: TemplateField, qr_field: TemplateField | None
) -> TemplateField:
    """Keep a certificate serial centred directly beneath its QR code.

    Template analysis can detect a wide footer text area that extends past a
    decorative QR border.  A serial is part of the QR verification block, so
    derive its safe position from the QR field whenever both fields are on the
    same page.
    """
    if qr_field is None:
        return field
    aligned = copy(field)
    panel = _qr_panel_for_field(page, qr_field)
    # A tall, wide QR card can reserve a dedicated bottom strip for the
    # serial. A normal square panel cannot, so leave it outside the outline.
    if panel is not None and panel.width >= 72 and panel.height >= qr_field.height + 26:
        aligned.width = max(16, panel.width - 8)
        aligned.height = 12
        aligned.x = panel.x0 + (panel.width - aligned.width) / 2
        aligned.y = panel.y1 - aligned.height - 4
        aligned.font_size = min(getattr(field, "font_size", None) or 10, 8)
        return aligned
    aligned.width = min(84, max(qr_field.width + 22, 68))
    aligned.height = max(12, min(field.height, 16))
    aligned.x = max(
        24,
        min(
            qr_field.x + (qr_field.width - aligned.width) / 2,
            page.rect.width - aligned.width - 24,
        ),
    )
    aligned.y = min(qr_field.y + qr_field.height + 8, page.rect.height - aligned.height - 24)
    aligned.font_size = min(getattr(field, "font_size", None) or 10, 8)
    return aligned


def _insert_image(page: fitz.Page, field: TemplateField, image_bytes: bytes) -> None:
    if field.width <= 0 or field.height <= 0:
        raise CertificateRenderingError(f"Template field '{field.field_name}' has an invalid box")
    rectangle = fitz.Rect(field.x, field.y, field.x + field.width, field.y + field.height)
    try:
        # New uploads are already normalized. Legacy files with an alpha mask
        # of 1–2/255 are restored here so their genuine handwriting is visible.
        page.insert_image(
            rectangle,
            stream=restore_legacy_signature_alpha(image_bytes),
            keep_proportion=True,
        )
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
        tokens.extend((
            "{{Serial No.}}", "{{Serial No}}", "{{Serial Number}}",
            "{{serial_no.}}", "{{serial_no}}",
        ))
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
    _remove_text_in_rectangle(page, combined)


def _remove_text_in_rectangle(page: fitz.Page, rectangle: fitz.Rect) -> None:
    """Remove only source text spans while retaining the artwork below them.

    Canva frequently stores a single visible sentence as several partly
    overlapping spans. Redacting one large area can leave edge glyphs behind,
    whereas small padded span redactions remove each glyph cleanly without
    painting a white background over watermark artwork.
    """
    spans = [
        fitz.Rect(span["bbox"])
        for block in page.get_text("dict").get("blocks", [])
        for line in block.get("lines", [])
        for span in line.get("spans", [])
        if str(span.get("text", "")).strip() and fitz.Rect(span["bbox"]).intersects(rectangle)
    ]
    if not spans:
        page.add_redact_annot(rectangle, fill=None)
        return
    for span in spans:
        padded = fitz.Rect(span.x0 - 1, span.y0 - 1, span.x1 + 1, span.y1 + 1)
        page.add_redact_annot(padded, fill=None)


def _source_text_style(page: fitz.Page, rectangle: fitz.Rect) -> tuple[str, float, tuple[float, float, float]]:
    """Return a safe approximation of the style visibly used in a text block."""
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if fitz.Rect(span["bbox"]).intersects(rectangle):
                    source_font = str(span.get("font", "")).lower()
                    font = (
                        "cour" if "cour" in source_font
                        else "tiro" if "times" in source_font or "boston" in source_font
                        else "helv"
                    )
                    color = int(span.get("color", 0))
                    return font, float(span.get("size", 10)), tuple(color >> shift & 255 for shift in (16, 8, 0))
    return "helv", 10, (14, 135, 204)


def _source_font_bytes(page: fitz.Page, rectangle: fitz.Rect) -> bytes | None:
    """Return the embedded font used by text at ``rectangle`` when available.

    A template preview must keep the source typography.  Reconstructing a
    paragraph with a bundled fallback font subtly changes its word widths and
    line breaks, even when the point size is the same.  PDF subset names are
    prefixed (for example ``DAAAAA+Calibri``), so compare their family suffix.
    """
    source_name: str | None = None
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if fitz.Rect(span["bbox"]).intersects(rectangle):
                    source_name = str(span.get("font", "")).split("+")[-1].lower()
                    break
            if source_name:
                break
        if source_name:
            break
    if not source_name:
        return None
    for font in page.get_fonts(full=True):
        base_name = str(font[3]).split("+")[-1].lower()
        if base_name != source_name:
            continue
        extracted = page.parent.extract_font(font[0])
        font_bytes = extracted[3]
        return font_bytes or None
    return None


def _source_bold_words(page: fitz.Page, rectangle: fitz.Rect) -> set[str]:
    """Return words which the author already made bold in a prose region."""
    bold_words: set[str] = set()
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if not fitz.Rect(span["bbox"]).intersects(rectangle):
                    continue
                if "bold" not in str(span.get("font", "")).lower():
                    continue
                bold_words.update(
                    word.lower() for word in re.findall(r"[A-Za-z0-9]+", str(span.get("text", "")))
                )
    # Individual words such as "the" and "and" may occur both inside a bold
    # activity title and in ordinary prose.  They cannot safely identify a
    # bold span after reflowing, so keep only meaningful title words.
    return bold_words - {"a", "an", "and", "at", "for", "in", "of", "on", "the", "to"}


def _paragraph_rectangle(page: fitz.Page, rectangle: fitz.Rect) -> fitz.Rect:
    """Provide enough room to redraw a paragraph, without touching nearby content."""
    return fitz.Rect(
        max(36, rectangle.x0 - 28),
        # Never creep into the name underline immediately above a paragraph.
        max(36, rectangle.y0),
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


def _paragraph_from_tagged_block(page: fitz.Page, values: Mapping[str, str]) -> tuple[fitz.Rect, str, set[str], float, tuple[float, float, float], bytes | None] | None:
    """Find a paragraph authored with field tags and make it one clean block.

    The author writes normal prose such as ``... {{roll_number}} ...`` in the
    PDF.  This replaces the *whole* text block, not just the tags, so the old
    paragraph cannot remain visible beneath replacement values.
    """
    token_pattern = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
    blocks = [
        (fitz.Rect(block["bbox"]), _block_text_from_words(page, fitz.Rect(block["bbox"])))
        for block in page.get_text("dict").get("blocks", [])
        if "lines" in block
    ]
    activity_names = {"roll_number", "activity_name", "activity_date"}
    for index, (anchor_rectangle, anchor_text) in enumerate(blocks):
        names = {name for name in token_pattern.findall(anchor_text) if name in values}
        # A student-name marker is commonly positioned above the certificate
        # paragraph. Start only from a field that belongs to the paragraph.
        if not names.intersection(activity_names):
            continue
        rectangles = [anchor_rectangle]
        texts = [anchor_text]
        # Canva can export the roll-number clause and the activity/date clause
        # as adjacent blocks. Include preceding activity-field blocks as well;
        # otherwise removing the roll-number token wipes the first sentence
        # while only the later sentence is redrawn.
        first_top = anchor_rectangle.y0
        for rectangle, text in reversed(blocks[:index]):
            if first_top > rectangle.y1 + 24:
                break
            line_names = {name for name in token_pattern.findall(text) if name in values}
            if not line_names.intersection(activity_names):
                break
            rectangles.insert(0, rectangle)
            texts.insert(0, text)
            names.update(line_names)
            first_top = min(first_top, rectangle.y0)
        last_bottom = anchor_rectangle.y1
        for rectangle, text in blocks[index + 1 :]:
            # PDF drawing order is not necessarily top-to-bottom. Canva can
            # place the "presented to" line after the paragraph in the PDF
            # object order even though it is visibly above it. Never let such
            # an out-of-order block enlarge the paragraph's dedicated area.
            if rectangle.y1 <= last_bottom:
                continue
            if rectangle.y0 > last_bottom + 24:
                break
            line_names = {name for name in token_pattern.findall(text) if name in values}
            # A paragraph's final wrapped line often has no tag. Retain it
            # when it follows the tagged activity text, but never absorb a
            # neighbouring non-paragraph block before any continuation starts.
            if not line_names and not names.intersection(activity_names):
                break
            rectangles.append(rectangle)
            texts.append(text)
            names.update(line_names)
            last_bottom = max(last_bottom, rectangle.y1)
        combined = fitz.Rect(rectangles[0])
        for rectangle in rectangles[1:]:
            combined.include_rect(rectangle)
        rectangle = _paragraph_rectangle(page, combined)
        content = token_pattern.sub(
            lambda match: values.get(match.group(1), match.group(0)), " ".join(texts)
        ).strip()
        _font, size, rgb = _source_text_style(page, rectangle)
        font_bytes = _source_font_bytes(page, rectangle)
        _remove_text_in_rectangle(page, rectangle)
        return rectangle, content, names, size, rgb, font_bytes
    return None


_LEADERSHIP_BODY_FIELDS = frozenset(
    {"student_name", "role", "society_name", "role_start_date", "role_end_date", "session_name", "issue_date"}
)


def _leadership_content(template_text: str, values: Mapping[str, str]) -> str:
    """Fill a leadership body without leaving a dangling society phrase.

    Overall EC roles do not belong to one society. Their data intentionally
    contains an empty ``society_name``, so remove the complete optional
    ``of {{society_name}}`` clause before replacing the remaining tags.
    """
    if not values.get("society_name", "").strip():
        template_text = re.sub(
            r"\s+of\s+\{\{society_name\}\}", "", template_text, flags=re.IGNORECASE
        )
    token_pattern = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
    content = token_pattern.sub(lambda match: values.get(match.group(1), match.group(0)), template_text)
    content = re.sub(r"[ \t]+([,.;:])", r"\1", content)
    return re.sub(r"[ \t]{2,}", " ", content).strip()


def _leadership_paragraph_from_tagged_blocks(
    page: fitz.Page, values: Mapping[str, str]
) -> tuple[fitz.Rect, str, set[str], float, tuple[int, int, int], bytes | None, set[str]] | None:
    """Replace the full prose area of a tagged leadership letter.

    Leadership letters use several deterministic fields in a normal flowing
    letter body. Rendering each narrow tag box independently makes the values
    overlap and deletes the source prose. Rebuild that one body at the source
    position and source font size instead.
    """
    token_pattern = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
    blocks = sorted(
        [
            (fitz.Rect(block["bbox"]), _block_text_from_words(page, fitz.Rect(block["bbox"])))
            for block in page.get_text("dict").get("blocks", [])
            if "lines" in block
        ],
        key=lambda item: (item[0].y0, item[0].x0),
    )
    for index, (anchor, anchor_text) in enumerate(blocks):
        names = {name for name in token_pattern.findall(anchor_text) if name in values}
        # ``issue_date`` belongs in the letter's upper metadata line, above
        # the title.  It must never be permitted to become the body anchor.
        if not names.intersection(_LEADERSHIP_BODY_FIELDS - {"student_name", "issue_date"}):
            continue
        rectangles = [anchor]
        texts = [anchor_text]
        last_bottom = anchor.y1
        for rectangle, text in blocks[index + 1 :]:
            if rectangle.y1 <= last_bottom:
                continue
            if rectangle.y0 > last_bottom + 30:
                break
            # Stay inside the letter body; side elements and signature blocks
            # must never be absorbed into the prose replacement rectangle.
            if rectangle.x1 < anchor.x0 - 24 or rectangle.x0 > anchor.x1 + 24:
                continue
            rectangles.append(rectangle)
            texts.append(text)
            names.update(name for name in token_pattern.findall(text) if name in values)
            last_bottom = max(last_bottom, rectangle.y1)
        combined = fitz.Rect(rectangles[0])
        for rectangle in rectangles[1:]:
            combined.include_rect(rectangle)
        # Keep the body anchored at its authored top edge and use only the
        # intentional blank space directly beneath it. This accommodates a
        # real name or society that wraps to one more line without shifting
        # the letter into the recipient heading or signature area.
        rectangle = fitz.Rect(
            combined.x0,
            combined.y0,
            combined.x1,
            min(page.rect.height - 72, combined.y1 + 20),
        )
        content = _leadership_content("\n\n".join(texts), values)
        _font, size, rgb = _source_text_style(page, anchor)
        font_bytes = _source_font_bytes(page, anchor)
        source_bold_words = _source_bold_words(page, combined)
        # Leadership letters reserve a plain white prose area.  Remove that
        # entire area before drawing its fresh paragraph; partial span
        # redactions can leave fragments of Canva's separately-drawn glyphs
        # underneath the replacement text.
        page.add_redact_annot(rectangle, fill=(1, 1, 1))
        return rectangle, content, names, size, rgb, font_bytes, source_bold_words
    return None


def _remove_placeholder_from_field(page: fitz.Page, field: TemplateField) -> None:
    """Erase the placeholder at one saved field box, not every matching tag."""
    rectangle = fitz.Rect(field.x, field.y, field.x + field.width, field.y + field.height)
    token = "{{" + field.field_name + "}}"
    matches = [match for match in page.search_for(token) if match.intersects(rectangle)]
    if not matches:
        return
    combined = fitz.Rect(matches[0])
    for match in matches[1:]:
        combined.include_rect(match)
    # This is intentionally more precise than `_remove_text_in_rectangle`.
    # A saved field may be only the placeholder portion of a single source
    # span, such as "Roll Number: {{roll_number}}".  Redacting the full span
    # would remove the fixed label as well.
    page.add_redact_annot(combined, fill=None)


def _remove_leadership_recipient_heading(page: fitz.Page) -> None:
    """Remove certificate-style recipient copy from a prose letter."""
    for rectangle in page.search_for("Presented with appreciation to"):
        page.add_redact_annot(rectangle, fill=None)


def _inline_activity_paragraph(page: fitz.Page, values: Mapping[str, str]) -> tuple[fitz.Rect, str, set[str], float, tuple[int, int, int], bytes | None] | None:
    """Replace a flowing certificate sentence as one typographic block.

    A PDF stores the words of a paragraph as independent drawing operations.
    Removing only placeholder words therefore leaves unnatural gaps.  For the
    standard EMC recognition sentence, replace the complete paragraph with one
    centred line-wrapped block instead.
    """
    start = page.search_for("In recognition")
    end = page.search_for("successful execution of the activity.")
    needed = {"roll_number", "activity_name", "activity_date"}
    if not start or not needed.issubset(values):
        return None
    first = start[0]
    if end:
        last = end[-1]
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
    else:
        # Uploaded PDFs often alter the final sentence through line wrapping,
        # punctuation or PDF text extraction. The opening phrase is enough to
        # locate the standard recognition block; reserve a bounded region
        # beneath it rather than falling back to individual box overlays.
        rectangle = fitz.Rect(
            72,
            max(36, first.y0 - 2),
            page.rect.width - 72,
            min(page.rect.height - 72, first.y0 + 86),
        )
    text = (
        f"In recognition of {values['roll_number']}, for outstanding efforts in organizing "
        f"and managing {values['activity_name']} on {values['activity_date']} under the EMC. "
        "Their leadership, coordination, and commitment significantly contributed to the "
        "successful execution of the activity."
    )
    _font, size, rgb = _source_text_style(page, first)
    font_bytes = _source_font_bytes(page, first)
    _remove_text_in_rectangle(page, rectangle)
    return rectangle, text, needed, size, rgb, font_bytes


def _activity_paragraph_from_field_cluster(
    page: fitz.Page,
    page_number: int,
    fields: Iterable[TemplateField],
    values: Mapping[str, str],
) -> tuple[fitz.Rect, str, set[str], float, tuple[int, int, int], bytes | None] | None:
    """Replace a recognition paragraph from its saved activity-field cluster.

    This is deliberately independent of PDF text extraction. A valid template
    already stores the three activity fields at the paragraph location, so the
    cluster is a reliable final fallback when Canva exports unsearchable text.
    """
    needed = {"roll_number", "activity_name", "activity_date"}
    if not needed.issubset(values):
        return None
    cluster = [
        field for field in fields
        if field.page_number == page_number and field.field_name in needed
    ]
    if {field.field_name for field in cluster} != needed:
        return None
    top = min(field.y for field in cluster)
    bottom = max(field.y + field.height for field in cluster)
    rectangle = fitz.Rect(
        72,
        max(36, top - 1),
        page.rect.width - 72,
        min(page.rect.height - 72, bottom + 76),
    )
    text = (
        f"In recognition of {values['roll_number']}, for outstanding efforts in organizing "
        f"and managing {values['activity_name']} on {values['activity_date']} under the EMC. "
        "Their leadership, coordination, and commitment significantly contributed to the "
        "successful execution of the activity."
    )
    _remove_text_in_rectangle(page, rectangle)
    return rectangle, text, needed, 10, (14, 135, 204), None


def _paragraph_words(
    text: str,
    values: Mapping[str, str],
    tagged_names: set[str],
    source_bold_words: set[str] | None = None,
) -> list[tuple[str | None, bool]]:
    """Split a paragraph into words, retaining which substituted values are bold."""
    dynamic_values = sorted(
        {values[name] for name in tagged_names if values.get(name)}, key=len, reverse=True
    )
    parts: list[tuple[str, bool]] = [(text, False)]
    for value in dynamic_values:
        next_parts: list[tuple[str, bool]] = []
        for part, bold in parts:
            if bold:
                next_parts.append((part, True))
                continue
            fragments = part.split(value)
            for index, fragment in enumerate(fragments):
                if fragment:
                    next_parts.append((fragment, False))
                if index < len(fragments) - 1:
                    next_parts.append((value, True))
        parts = next_parts
    bold_source = source_bold_words or set()
    words: list[tuple[str | None, bool]] = []
    for part, bold in parts:
        for item in re.findall(r"\S+|\n", part):
            normalized = re.sub(r"[^A-Za-z0-9]", "", item).lower()
            words.append((None, False) if item == "\n" else (item, bold or normalized in bold_source))
    return words


def _render_tagged_paragraph(
    page: fitz.Page,
    rectangle: fitz.Rect,
    text: str,
    values: Mapping[str, str],
    tagged_names: set[str],
    font_size: float,
    rgb: tuple[int, int, int],
    *,
    align: int,
    lineheight: float,
    font_name: str,
    font_bytes: bytes | None,
    source_bold_words: set[str] | None = None,
    calibri_compatible: bool = False,
) -> None:
    """Render prose while bolding only values substituted for template tags."""
    if calibri_compatible:
        asset_directory = Path(__file__).resolve().parents[2] / "assets"
        font_bytes = (asset_directory / "Carlito-Regular.ttf").read_bytes()
        bold_font_bytes = (asset_directory / "Carlito-Bold.ttf").read_bytes()
    elif font_bytes is None:
        font_bytes = (Path(__file__).resolve().parents[2] / "assets" / "IBMPlexSans-Medium.ttf").read_bytes()
        bold_font_bytes = font_bytes
    else:
        bold_font_bytes = font_bytes
    try:
        page.insert_font(fontname=font_name, fontbuffer=font_bytes)
    except (RuntimeError, ValueError) as error:
        raise CertificateRenderingError("Certificate paragraph font is unreadable") from error
    font = fitz.Font(fontbuffer=font_bytes)
    bold_font_name = f"{font_name}Bold"
    try:
        page.insert_font(fontname=bold_font_name, fontbuffer=bold_font_bytes)
    except (RuntimeError, ValueError) as error:
        raise CertificateRenderingError("Certificate paragraph bold font is unreadable") from error
    bold_font = fitz.Font(fontbuffer=bold_font_bytes)
    # PDF templates embed subsetted fonts. The source paragraph can be drawn
    # back exactly, but a new roll number or name may contain glyphs that were
    # not used anywhere in the template subset. Keep the template font for all
    # existing prose and use the normal EMC font only for those missing tag
    # glyphs instead of silently dropping characters.
    # The original template font is often a subset. Use the complete EMC sans
    # file only for characters absent from it, but render it at the same point
    # size and without a stroke so values do not look pasted on afterwards.
    fallback_bytes = (Path(__file__).resolve().parents[2] / "assets" / "IBMPlexSans-Medium.ttf").read_bytes()
    fallback_name = f"{font_name}Fallback"
    try:
        page.insert_font(fontname=fallback_name, fontbuffer=fallback_bytes)
    except (RuntimeError, ValueError) as error:
        raise CertificateRenderingError("Certificate paragraph fallback font is unreadable") from error
    fallback_font = fitz.Font(fontbuffer=fallback_bytes)
    size = min(max(font_size, 5), 16)
    space = font.text_length(" ", fontsize=size)
    lines: list[list[tuple[str, bool, float, float, str]] | None] = []
    line: list[tuple[str, bool, float, float, str]] = []
    width = 0.0
    for word, bold in _paragraph_words(text, values, tagged_names, source_bold_words):
        if word is None:
            if line:
                lines.append(line)
                line, width = [], 0.0
            lines.append(None)
            continue
        word_font = bold_font if bold else font
        word_font_name = bold_font_name if bold else font_name
        if not calibri_compatible and not all(word_font.has_glyph(ord(character)) for character in word):
            word_font = fallback_font
            word_font_name = fallback_name
        word_width = word_font.text_length(word, fontsize=size)
        gap = 0.0 if not line or word[0] in ",.;:)]}" or line[-1][0][-1] in "([{" else space
        required = gap + word_width
        if line and width + required > rectangle.width:
            lines.append(line)
            line, width, gap, required = [], 0.0, 0.0, word_width
        line.append((word, bold, word_width, gap, word_font_name))
        width += required
    if line:
        lines.append(line)
    total_height = len(lines) * size * lineheight
    if total_height > rectangle.height + 0.5:
        raise CertificateRenderingError("Certificate paragraph does not fit its dedicated template area at the configured font size")
    color = tuple(channel / 255 for channel in rgb)
    baseline = rectangle.y0 + size
    for items in lines:
        if items is None:
            baseline += size * lineheight
            continue
        line_width = sum(item[2] + item[3] for item in items)
        x = rectangle.x0 + ((rectangle.width - line_width) / 2 if align == fitz.TEXT_ALIGN_CENTER else 0)
        for word, bold, word_width, gap, word_font_name in items:
            x += gap
            point = fitz.Point(x, baseline)
            page.insert_text(
                point,
                word,
                fontname=word_font_name,
                fontsize=size,
                color=color,
                render_mode=0,
                border_width=1,
            )
            x += word_width
        baseline += size * lineheight


def _render_activity_paragraph(
    page: fitz.Page,
    rectangle: fitz.Rect,
    text: str,
    font_size: float,
    rgb: tuple[int, int, int],
    values: Mapping[str, str],
    tagged_names: set[str],
    font_bytes: bytes | None,
) -> None:
    # Use a uniquely embedded font instead of a built-in PDF font alias.
    # Canva templates can already bind aliases such as "helv" to incompatible
    # font resources, which makes newly drawn characters appear fragmented.
    _render_tagged_paragraph(page, rectangle, text, values, tagged_names, font_size, rgb, align=fitz.TEXT_ALIGN_CENTER, lineheight=1.15, font_name="EMCActivityBody", font_bytes=font_bytes)


def _render_leadership_paragraph(
    page: fitz.Page,
    rectangle: fitz.Rect,
    text: str,
    font_size: float,
    rgb: tuple[int, int, int],
    values: Mapping[str, str],
    tagged_names: set[str],
    font_bytes: bytes | None,
    source_bold_words: set[str],
) -> None:
    """Render a letter body at its original left-aligned typography."""
    # Some Canva exports retain visual outline paths even after text
    # redaction. The prose region is intentionally blank in this template, so
    # an opaque cover guarantees no legacy glyph fragments can show through.
    page.draw_rect(rectangle, color=None, fill=(1, 1, 1), overlay=True)
    # The uploaded leadership letter uses Calibri 12.5 pt. Keep that exact
    # size there, while allowing legacy/synthetic templates to retain their
    # own smaller source size.
    effective_size = 12.5 if abs(font_size - 12.5) < 0.6 else font_size
    _render_tagged_paragraph(
        page, rectangle, text, values, tagged_names, effective_size, rgb,
        align=fitz.TEXT_ALIGN_LEFT, lineheight=1.20,
        font_name="EMCLeadershipCalibri", font_bytes=font_bytes,
        source_bold_words=source_bold_words, calibri_compatible=True,
    )


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
    # Signature slots are optional images. A preview should still render when
    # a template contains a signature tag but no active matching upload exists.
    signature_slots = {name for name in configured_names if name.startswith("signature_")}
    needed_values = configured_names - {"qr_code", *images, *signature_slots}
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
        paragraph_jobs: dict[int, tuple[fitz.Rect, str, set[str], float, tuple[int, int, int], bytes | None, set[str]]] = {}
        paragraph_fields: set[tuple[int, str]] = set()
        leadership_paragraph_pages: set[int] = set()
        is_leadership_template = bool(
            (_LEADERSHIP_BODY_FIELDS - {"student_name"}).issubset(configured_names)
        )
        # Paragraph replacement is derived from the PDF itself, not from the
        # saved box configuration. Older templates can carry imperfect field
        # records, but their visible certificate paragraph must still be
        # removed completely before the fresh paragraph is drawn.
        for page_number in range(1, document.page_count + 1):
            page = document[page_number - 1]
            if is_leadership_template:
                job = _leadership_paragraph_from_tagged_blocks(page, normalized_values)
            else:
                # Prefer the standard recognition renderer only for the
                # standard EMC wording. Generic tagged prose keeps its text.
                is_standard_recognition = bool(
                    page.search_for("In recognition") and page.search_for("under the EMC")
                )
                job = (
                    _inline_activity_paragraph(page, normalized_values)
                    if is_standard_recognition
                    else _paragraph_from_tagged_block(page, normalized_values)
                )
                if job is None:
                    job = _activity_paragraph_from_field_cluster(
                        page, page_number, field_list, normalized_values
                    )
            if job:
                if is_leadership_template:
                    rectangle, text, replaced_names, size, rgb, font_bytes, source_bold_words = job
                else:
                    rectangle, text, replaced_names, size, rgb, font_bytes = job
                    source_bold_words = set()
                paragraph_jobs[page_number] = rectangle, text, replaced_names, size, rgb, font_bytes, source_bold_words
                if is_leadership_template:
                    leadership_paragraph_pages.add(page_number)
                    paragraph_fields.update((page_number, name) for name in replaced_names)
                else:
                    # Student names frequently occur twice: once as the
                    # prominent recipient line and once in the body paragraph.
                    paragraph_fields.update(
                        (page_number, name) for name in replaced_names - {"student_name"}
                    )
        for field in field_list:
            if field.page_number < 1 or field.page_number > document.page_count:
                raise CertificateRenderingError(
                    f"Template field '{field.field_name}' references an invalid page"
                )
            if (field.page_number, field.field_name) in paragraph_fields:
                if is_leadership_template and field.field_name == "student_name":
                    # The letter body already includes the student's name; do
                    # not render a duplicate recipient name above it.
                    _remove_placeholder_from_field(document[field.page_number - 1], field)
                    _remove_leadership_recipient_heading(document[field.page_number - 1])
                continue
            if is_leadership_template and field.field_name == "roll_number":
                # The roll number normally follows a fixed "Roll Number:"
                # label.  Removing the entire source span would erase that
                # label, so redact only the configured placeholder box.
                _remove_placeholder_from_field(document[field.page_number - 1], field)
                continue
            if is_leadership_template:
                # Fields such as ``issue_date`` share a text span with their
                # fixed label ("Issue Date:").  A broad span redaction would
                # erase that original template text as well.
                _remove_placeholder_from_field(document[field.page_number - 1], field)
            else:
                _remove_inline_placeholder(document[field.page_number - 1], field.field_name)
        for page in document:
            # Preserve vector artwork. Canva commonly stores the decorative
            # frame and the QR holder as large grouped drawings, so removing
            # intersecting graphics would erase those template elements.
            page.apply_redactions(images=0, graphics=0, text=0)
        for page_number, (rectangle, text, replaced_names, size, rgb, font_bytes, source_bold_words) in paragraph_jobs.items():
            if page_number in leadership_paragraph_pages:
                _render_leadership_paragraph(
                    document[page_number - 1], rectangle, text, size, rgb, normalized_values, replaced_names, font_bytes, source_bold_words
                )
            else:
                _render_activity_paragraph(
                    document[page_number - 1], rectangle, text, size, rgb, normalized_values, replaced_names, font_bytes
                )
        qr_fields = {
            field.page_number: _effective_qr_field(document[field.page_number - 1], field)
            for field in field_list
            if field.field_name == "qr_code"
        }
        for field in field_list:
            page = document[field.page_number - 1]
            if field.field_name == "qr_code":
                _insert_qr(page, field, verification_url)
            elif field.field_name in images:
                _insert_image(page, field, images[field.field_name])
            elif field.field_name in signature_slots:
                # An unconfigured signature box is intentionally blank in
                # previews. Its source placeholder was already redacted.
                continue
            elif (field.page_number, field.field_name) in paragraph_fields:
                continue
            else:
                text_field = (
                    _verification_field_below_qr(page, field, qr_fields.get(field.page_number))
                    if field.field_name == "verification_id"
                    else field
                )
                _insert_text(
                    page,
                    text_field,
                    normalized_values[field.field_name],
                    fonts,
                    alignment="left" if is_leadership_template and field.field_name == "roll_number" else "center",
                    emphasize=not is_leadership_template,
                )
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
