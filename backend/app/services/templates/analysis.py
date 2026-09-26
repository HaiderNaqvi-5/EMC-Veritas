import re
from dataclasses import dataclass
from io import BytesIO
from math import ceil

import fitz
import pytesseract
from PIL import Image


@dataclass(frozen=True)
class PdfTextAnalysis:
    pages: list[str]
    ocr_used: bool
    ocr_required: bool


@dataclass(frozen=True)
class DetectedTemplateField:
    """A recognised visible placeholder and its PDF-coordinate placement."""

    field_name: str
    page_number: int
    x: int
    y: int
    width: int
    height: int
    detected_text: str
    font_family: str
    font_size: int
    text_color: str


_CERTIFICATE_PLACEHOLDERS: dict[str, tuple[str, ...]] = {
    "student_name": ("{{student_name}}", "student_name", "student name"),
    "roll_number": ("{{roll_number}}", "roll_number", "student roll number", "roll number"),
    "activity_name": ("{{activity_name}}", "activity_name", "activity name"),
    "activity_date": ("{{activity_date}}", "activity_date", "activity date"),
    "verification_id": ("{{verification_id}}", "verification_id", "verification id", "serial number", "serial no"),
    "qr_code": ("{{qr_code}}", "qr_code", "qr code"),
}
_SIGNATURE_PLACEHOLDER = re.compile(r"\{\{(signature_[a-z][a-z0-9_]*)\}\}", re.IGNORECASE)


def has_signature_like_content(pages: list[str]) -> bool:
    """Flag text that merits an explicit retain/replace signature decision.

    Image-only handwritten signatures cannot be reliably classified as text, so
    every template still requires the explicit choice. This signal warns the
    editor when the PDF itself exposes date/signature labels.
    """
    return bool(re.search(r"\b(signature|signatory|signed|date)\b", "\n".join(pages), re.IGNORECASE))


def extract_pdf_text(pdf_bytes: bytes) -> list[str]:
    """Return embedded text without using the external OCR executable."""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        return [page.get_text("text") for page in document]


def analyze_pdf_text(pdf_bytes: bytes) -> PdfTextAnalysis:
    """Extract template text, using OCR only for pages without embedded text.

    A template can contain a mix of normal PDF pages and scanned pages.  OCR is
    therefore deliberately page-specific instead of replacing reliable PDF
    text for the entire document.
    """
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        pages = [page.get_text("text") for page in document]
        ocr_used = False
        for index, text in enumerate(pages):
            if text.strip():
                continue
            page = document[index]
            image_bytes = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")
            try:
                with Image.open(BytesIO(image_bytes)) as image:
                    recognized = pytesseract.image_to_string(image).strip()
            except (OSError, pytesseract.TesseractError, pytesseract.TesseractNotFoundError):
                recognized = ""
            if recognized:
                pages[index] = recognized
                ocr_used = True
    return PdfTextAnalysis(pages=pages, ocr_used=ocr_used, ocr_required=requires_ocr(pages))


def detect_certificate_placeholders(pdf_bytes: bytes) -> list[DetectedTemplateField]:
    """Find common visible certificate placeholders and return editable field suggestions.

    Text extraction alone is informational.  This separate step supplies the
    coordinates that the template editor needs in order to create its saved
    field configuration.  It deliberately does not save or approve anything.
    """
    detected: list[DetectedTemplateField] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        for field_name, aliases in _CERTIFICATE_PLACEHOLDERS.items():
            if field_name == "qr_code" and document.page_count:
                page = document[0]
                qr_rectangle = _dedicated_qr_rectangle(page)
                detected.append(
                    DetectedTemplateField(
                        field_name="qr_code", page_number=1,
                        x=int(qr_rectangle.x0), y=int(qr_rectangle.y0),
                        width=int(qr_rectangle.width), height=int(qr_rectangle.height),
                        detected_text="dedicated QR square",
                        font_family="helv", font_size=12, text_color="#000000",
                    )
                )
                continue
            match: tuple[int, fitz.Rect, str] | None = None
            for page_index, page in enumerate(document):
                for alias in aliases:
                    rectangles = page.search_for(alias)
                    if rectangles:
                        match = (page_index, _combined_placeholder_rect(rectangles), alias)
                        break
                if match is not None:
                    break
            if match is None:
                continue
            page_index, rectangle, alias = match
            font_family, font_size, text_color = _style_at(document[page_index], rectangle)
            if field_name == "student_name":
                center_x = (rectangle.x0 + rectangle.x1) / 2
                center_y = (rectangle.y0 + rectangle.y1) / 2
                rectangle = fitz.Rect(center_x - 140, center_y - 18, center_x + 140, center_y + 18)
                font_family, font_size = "tiro", 28
            if field_name == "verification_id":
                # The serial placeholder is normally printed at the right edge.
                # Expanding it to the right can put it past the page boundary,
                # which then prevents the admin editor from approving the draft.
                # Keep the field over the visible serial token and expand only
                # into available page space.
                available_width = document[page_index].rect.width - rectangle.x0 - 8
                rectangle = fitz.Rect(
                    rectangle.x0,
                    rectangle.y0,
                    rectangle.x0 + min(128, max(16, available_width)),
                    rectangle.y1,
                )
            x, y, width, height = _safe_field_geometry(document[page_index], rectangle)
            detected.append(
                DetectedTemplateField(
                    field_name=field_name,
                    page_number=page_index + 1,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    detected_text=alias,
                    font_family=font_family,
                    font_size=font_size,
                    text_color=text_color,
                )
            )
        # Signature fields are intentionally dynamic: an activity can use any
        # uploaded signatory, not a hard-coded President/DSA pair.  Detect
        # every explicit {{signature_title}} placeholder as an image box.
        for page_index, page in enumerate(document):
            names = sorted({name.lower() for name in _SIGNATURE_PLACEHOLDER.findall(page.get_text("text"))})
            for field_name in names:
                rectangles = page.search_for("{{" + field_name + "}}")
                if not rectangles:
                    continue
                rectangle = _combined_placeholder_rect(rectangles)
                font_family, font_size, text_color = _style_at(page, rectangle)
                rectangle = _signature_field_rectangle(page, rectangle)
                x, y, width, height = _safe_field_geometry(page, rectangle)
                detected.append(
                    DetectedTemplateField(
                        field_name=field_name,
                        page_number=page_index + 1,
                        x=x,
                        y=y,
                        width=width,
                        height=height,
                        detected_text="{{" + field_name + "}}",
                        font_family=font_family,
                        font_size=font_size,
                        text_color=text_color,
                    )
                )
    return detected


def _signature_field_rectangle(page: fitz.Page, placeholder: fitz.Rect) -> fitz.Rect:
    """Give a signature token a practical, visible image area around its marker."""
    target_width = min(180, page.rect.width - 16)
    target_height = min(72, page.rect.height - 16)
    center_x = (placeholder.x0 + placeholder.x1) / 2
    center_y = (placeholder.y0 + placeholder.y1) / 2
    x0 = min(max(8, center_x - target_width / 2), page.rect.width - target_width - 8)
    y0 = min(max(8, center_y - target_height / 2), page.rect.height - target_height - 8)
    return fitz.Rect(x0, y0, x0 + target_width, y0 + target_height)


def _safe_field_geometry(page: fitz.Page, rectangle: fitz.Rect) -> tuple[int, int, int, int]:
    """Convert a detected PDF rectangle into an in-bounds editor box.

    Do not add arbitrary padding here: adjacent lines in certificate prose are
    often only a few points apart, and padding turns valid neighbouring fields
    into overlapping boxes that the approval guard correctly rejects.
    """
    minimum_size = 16
    page_width = int(page.rect.width)
    page_height = int(page.rect.height)
    x = min(max(0, int(rectangle.x0)), max(0, page_width - minimum_size))
    y = min(max(0, int(rectangle.y0)), max(0, page_height - minimum_size))
    width = min(max(minimum_size, ceil(rectangle.width)), page_width - x)
    height = min(max(minimum_size, ceil(rectangle.height)), page_height - y)
    return x, y, width, height


def _combined_placeholder_rect(rectangles: list[fitz.Rect]) -> fitz.Rect:
    """Return one box for a token split into multiple PDF text fragments."""
    combined = fitz.Rect(rectangles[0])
    for rectangle in rectangles[1:]:
        combined.include_rect(rectangle)
    return combined


def _dedicated_qr_rectangle(page: fitz.Page) -> fitz.Rect:
    """Find a footer QR frame drawn in the PDF and inset the generated code."""
    frames = [
        drawing["rect"]
        for drawing in page.get_drawings()
        if drawing["rect"].x0 > page.rect.width / 2
        and 64 <= drawing["rect"].width <= 160
        and drawing["rect"].height >= drawing["rect"].width
    ]
    if frames:
        frame = min(frames, key=lambda rectangle: rectangle.y0)
        size = min(frame.width, frame.height) - 16
        return fitz.Rect(
            frame.x0 + (frame.width - size) / 2,
            frame.y0 + 8,
            frame.x0 + (frame.width + size) / 2,
            frame.y0 + 8 + size,
        )
    size = 80
    return fitz.Rect(page.rect.width - size - 74, page.rect.height - size - 74, page.rect.width - 74, page.rect.height - 74)


def _style_at(page: fitz.Page, rectangle: fitz.Rect) -> tuple[str, int, str]:
    """Infer a safe rendering style from the text span overlapping a placeholder."""
    best_span: dict[str, object] | None = None
    best_area = 0.0
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                span_rect = fitz.Rect(span["bbox"])
                overlap = span_rect & rectangle
                area = max(0.0, overlap.width) * max(0.0, overlap.height)
                if area > best_area:
                    best_area = area
                    best_span = span
    if best_span is None:
        return "helv", 12, "#000000"
    source_font = str(best_span.get("font", "")).lower()
    font_family = "cour" if "cour" in source_font else "tiro" if "times" in source_font else "helv"
    color = int(best_span.get("color", 0))
    return font_family, min(72, max(5, round(float(best_span.get("size", 12))))), f"#{color:06x}"


def requires_ocr(extracted_pages: list[str]) -> bool:
    return not any(page.strip() for page in extracted_pages)
