def ensure_pdf(filename: str, content_type: str | None) -> None:
    if not filename.lower().endswith(".pdf") or content_type not in {"application/pdf", None}:
        raise ValueError("V1 certificate template uploads must be PDF files")


def ensure_font(filename: str, content_type: str | None, content: bytes) -> str:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    expected_content_type = {"ttf": "font/ttf", "otf": "font/otf"}.get(suffix)
    if expected_content_type is None or content_type not in {expected_content_type, None}:
        raise ValueError("Uploaded template fonts must be TTF or OTF files")
    if not content:
        raise ValueError("Uploaded template font is empty")
    return expected_content_type
