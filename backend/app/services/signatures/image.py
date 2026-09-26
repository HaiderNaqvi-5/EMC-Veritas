"""Normalise uploaded handwritten signatures for clean certificate placement."""

from io import BytesIO

from PIL import Image, UnidentifiedImageError


def prepare_signature_image(content: bytes) -> bytes:
    """Remove a light paper background and store the visible ink as black PNG."""
    try:
        with Image.open(BytesIO(content)) as source:
            image = source.convert("RGBA")
    except (OSError, UnidentifiedImageError) as error:
        raise ValueError("Signature image is unreadable") from error

    pixels = []
    for red, green, blue, alpha in image.getdata():
        # White/light paper becomes transparent; dark coloured ink is preserved
        # as opaque black.  The soft transition avoids jagged handwriting edges.
        luminance = (299 * red + 587 * green + 114 * blue) / 1000
        ink_opacity = max(0.0, min(1.0, (248 - luminance) / 104))
        pixels.append((0, 0, 0, round(alpha * ink_opacity)))
    image.putdata(pixels)
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
