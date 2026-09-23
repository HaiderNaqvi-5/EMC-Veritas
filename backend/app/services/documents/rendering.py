from collections.abc import Iterable, Mapping
from datetime import date
from io import BytesIO

import fitz

from app.models.domain import TemplateField
from app.services.documents.qr_image import qr_png
from app.services.documents.text_fit import fit_font_size
from app.services.templates.fields import missing_required_fields


class CertificateRenderingError(ValueError):
    """Raised when an approved PDF template cannot produce a safe certificate."""


def _text_width(text: str, size: float) -> float:
    return fitz.get_text_length(text, fontname="helv", fontsize=size)


def _insert_text(page: fitz.Page, field: TemplateField, value: str) -> None:
    if field.width <= 0 or field.height < 6:
        raise CertificateRenderingError(f"Template field '{field.field_name}' has an invalid box")
    font_size = fit_font_size(value, field.width, min(18, field.height - 2), _text_width)
    if font_size <= 4:
        raise CertificateRenderingError(f"Value for template field '{field.field_name}' does not fit")
    text_width = _text_width(value, font_size)
    point = fitz.Point(field.x + max((field.width - text_width) / 2, 0), field.y + (field.height + font_size) / 2)
    page.insert_text(
        point,
        value,
        fontname="helv",
        fontsize=font_size,
        color=(0, 0, 0),
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


def render_certificate(
    template_pdf: bytes,
    fields: Iterable[TemplateField],
    values: Mapping[str, str | date],
    *,
    verification_url: str,
    watermark: str | None = None,
    image_values: Mapping[str, bytes] | None = None,
) -> bytes:
    """Overlay configured fields and an optional QR code onto a PDF certificate template.

    Field coordinates use one-based PDF page numbers and point units. The template itself is
    never changed in Storage; this returns a new, immutable issued-document byte stream.
    """
    field_list = list(fields)
    configured_names = {field.field_name for field in field_list}
    missing = missing_required_fields(configured_names)
    if missing:
        raise CertificateRenderingError(
            "Template is missing required fields: " + ", ".join(sorted(missing))
        )

    normalized_values = {
        name: value.isoformat() if isinstance(value, date) else str(value)
        for name, value in values.items()
    }
    images = image_values or {}
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
        for field in field_list:
            if field.page_number < 1 or field.page_number > document.page_count:
                raise CertificateRenderingError(
                    f"Template field '{field.field_name}' references an invalid page"
                )
            page = document[field.page_number - 1]
            if field.field_name == "qr_code":
                _insert_qr(page, field, verification_url)
            elif field.field_name in images:
                _insert_image(page, field, images[field.field_name])
            else:
                _insert_text(page, field, normalized_values[field.field_name])
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
