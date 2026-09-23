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


def requires_ocr(extracted_pages: list[str]) -> bool:
    return not any(page.strip() for page in extracted_pages)
