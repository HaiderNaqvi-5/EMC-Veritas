import re
from dataclasses import dataclass
from io import BytesIO

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
            match: tuple[int, fitz.Rect, str] | None = None
            for page_index, page in enumerate(document):
                for alias in aliases:
                    rectangles = page.search_for(alias)
                    if rectangles:
                        match = (page_index, rectangles[0], alias)
                        break
                if match is not None:
                    break
            if match is None:
                if field_name == "qr_code" and document.page_count:
                    page = document[0]
                    detected.append(
                        DetectedTemplateField(
                            field_name="qr_code",
                            page_number=1,
                            x=max(0, int(page.rect.width) - 170),
                            y=max(0, int(page.rect.height) - 150),
                            width=96,
                            height=96,
                            detected_text="suggested footer QR area",
                            font_family="helv",
                            font_size=12,
                            text_color="#000000",
                        )
                    )
                continue
            page_index, rectangle, alias = match
            font_family, font_size, text_color = _style_at(document[page_index], rectangle)
            detected.append(
                DetectedTemplateField(
                    field_name=field_name,
                    page_number=page_index + 1,
                    x=max(0, int(rectangle.x0) - 2),
                    y=max(0, int(rectangle.y0) - 2),
                    width=max(16, int(rectangle.width) + 4),
                    height=max(16, int(rectangle.height) + 4),
                    detected_text=alias,
                    font_family=font_family,
                    font_size=font_size,
                    text_color=text_color,
                )
            )
    return detected


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
