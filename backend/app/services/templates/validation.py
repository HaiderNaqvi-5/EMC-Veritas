from io import BytesIO

from fontTools.ttLib import TTFont, TTLibError


def ensure_pdf(filename: str, content_type: str | None) -> None:
    if not filename.lower().endswith(".pdf") or content_type not in {"application/pdf", None}:
        raise ValueError("V1 certificate template uploads must be PDF files")


def ensure_font(filename: str, content_type: str | None, content: bytes) -> str:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    expected_content_type = {"ttf": "font/ttf", "otf": "font/otf"}.get(suffix)
    # Browsers and operating systems disagree on OpenType MIME labels
    # (for example, Chrome commonly sends ``application/vnd.ms-opentype``).
    # Treat the extension only as a format hint and let the signature plus
    # FontTools parsing below provide the authoritative validation.
    if expected_content_type is None:
        raise ValueError("Uploaded template fonts must be TTF or OTF files")
    if not content:
        raise ValueError("Uploaded template font is empty")
    signatures = {
        "ttf": (b"\x00\x01\x00\x00", b"true", b"typ1"),
        "otf": (b"OTTO",),
    }
    if not content.startswith(signatures[suffix]):
        raise ValueError("Uploaded template font has an invalid TTF or OTF signature")
    try:
        font = TTFont(BytesIO(content), lazy=False)
        if "name" not in font or "cmap" not in font:
            raise ValueError("Uploaded font is missing required name or character-map tables")
        if not font.getBestCmap():
            raise ValueError("Uploaded font contains no usable characters")
        font.close()
    except (TTLibError, ValueError, KeyError) as error:
        raise ValueError(f"Uploaded font structure is invalid: {error}") from error
    return expected_content_type
