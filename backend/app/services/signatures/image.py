"""Fast normalisation of uploaded handwritten signatures for certificates."""

from io import BytesIO
from statistics import median

from PIL import Image, ImageChops, ImageFilter, ImageOps, UnidentifiedImageError


def _luminance(red: int, green: int, blue: int) -> float:
    return (299 * red + 587 * green + 114 * blue) / 1000


def _background_luminance(image: Image.Image) -> float:
    """Estimate paper brightness from the outer edge of a photographed page."""
    width, height = image.size
    edge = max(1, min(width, height) // 30)
    samples = []
    for y in range(0, height, max(1, height // 80)):
        for x in range(0, width, max(1, width // 80)):
            if x < edge or y < edge or x >= width - edge or y >= height - edge:
                red, green, blue, _alpha = image.getpixel((x, y))
                samples.append(_luminance(red, green, blue))
    return float(median(samples)) if samples else 255.0


def _soft_threshold(image: Image.Image, start: int, range_size: int) -> Image.Image:
    """Build a soft alpha mask using Pillow's C-backed point operation."""
    return image.point(
        [max(0, min(255, round((value - start) * 255 / range_size))) for value in range(256)]
    )


def _has_visible_ink(mask: Image.Image) -> bool:
    """Reject tiny colour noise before treating it as a handwritten stroke."""
    _minimum, maximum = mask.getextrema()
    if maximum < 32:
        return False
    visible_pixels = sum(count for value, count in enumerate(mask.histogram()) if value >= 32)
    return visible_pixels >= max(16, mask.width * mask.height // 10_000)


def _crop_to_ink(image: Image.Image, alpha: Image.Image) -> Image.Image:
    # Median filtering removes isolated camera noise without erasing strokes.
    cleaned = alpha.filter(ImageFilter.MedianFilter(5))
    visible = cleaned.getbbox() or alpha.getbbox()
    if visible is None:
        raise ValueError("No visible signature ink was found in the uploaded image")
    left, top, right, bottom = visible
    padding = max(8, min(image.size) // 80)
    return image.crop(
        (
            max(0, left - padding),
            max(0, top - padding),
            min(image.width, right + padding),
            min(image.height, bottom + padding),
        )
    )


def prepare_signature_image(content: bytes) -> bytes:
    """Crop handwriting, remove paper, and store ink as a transparent black PNG."""
    try:
        with Image.open(BytesIO(content)) as source:
            image = source.convert("RGBA")
    except (OSError, UnidentifiedImageError) as error:
        raise ValueError("Signature image is unreadable") from error

    red, green, blue, source_alpha = image.split()
    colour_difference = ImageChops.lighter(
        ImageChops.difference(red, green),
        ImageChops.lighter(ImageChops.difference(red, blue), ImageChops.difference(green, blue)),
    )
    colour_mask = _soft_threshold(colour_difference, start=50, range_size=65)
    # Orange/blue pen strokes are best isolated by colour. Black pen strokes
    # are isolated by darkness relative to the measured paper background.
    # A photographed page can have weak colour noise at the edges.  That used
    # to select a mask with alpha 1-2/255 and turn a black signature invisible.
    # Only use the colour path when it contains genuinely visible ink.
    if _has_visible_ink(colour_mask):
        alpha = colour_mask
    else:
        background = max(0, round(_background_luminance(image)) - 12)
        dark_difference = ImageChops.subtract(
            Image.new("L", image.size, color=background), ImageOps.grayscale(image)
        )
        alpha = _soft_threshold(dark_difference, start=16, range_size=72)
    alpha = ImageChops.multiply(alpha, source_alpha)
    output_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
    output_image.putalpha(alpha)
    output_image = _crop_to_ink(output_image, alpha)
    output = BytesIO()
    output_image.save(output, format="PNG", optimize=True)
    return output.getvalue()
