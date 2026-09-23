import fitz


def extract_pdf_text(pdf_bytes: bytes) -> list[str]:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    return [page.get_text("text") for page in document]


def requires_ocr(extracted_pages: list[str]) -> bool:
    return not any(page.strip() for page in extracted_pages)
