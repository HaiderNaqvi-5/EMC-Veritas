def ensure_pdf(filename: str, content_type: str | None) -> None:
    if not filename.lower().endswith(".pdf") or content_type not in {"application/pdf", None}:
        raise ValueError("V1 certificate template uploads must be PDF files")
