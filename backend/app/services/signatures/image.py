"""Normalise uploaded handwritten signatures for clean certificate placement."""

from collections import deque
from io import BytesIO
from statistics import median

from PIL import Image, ImageFilter, UnidentifiedImageError


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


def _largest_ink_bounds(alpha: Image.Image) -> tuple[int, int, int, int] | None:
    """Locate the handwriting cluster while ignoring isolated camera/paper noise."""
    scale = 4
    small = alpha.resize(
        (max(1, alpha.width // scale), max(1, alpha.height // scale)), Image.Resampling.LANCZOS
    )
    # Expand strokes slightly so the individual pen strokes form one cluster.
    mask = small.point(lambda value: 255 if value >= 96 else 0).filter(ImageFilter.MaxFilter(5))
    width, height = mask.size
    pixels = mask.load()
    visited = bytearray(width * height)
    largest: tuple[int, int, int, int, int] | None = None
    for start_y in range(height):
        for start_x in range(width):
            index = start_y * width + start_x
            if visited[index] or pixels[start_x, start_y] == 0:
                continue
            queue = deque([(start_x, start_y)])
            visited[index] = 1
            count = 0
            left = right = start_x
            top = bottom = start_y
            while queue:
                x, y = queue.popleft()
                count += 1
                left, right = min(left, x), max(right, x)
                top, bottom = min(top, y), max(bottom, y)
                for next_x, next_y in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    next_index = next_y * width + next_x
                    if (
                        0 <= next_x < width
                        and 0 <= next_y < height
                        and not visited[next_index]
                        and pixels[next_x, next_y] != 0
                    ):
                        visited[next_index] = 1
                        queue.append((next_x, next_y))
            if largest is None or count > largest[0]:
                largest = count, left, top, right, bottom
    if largest is None:
        return None
    _count, left, top, right, bottom = largest
    padding = max(8, min(alpha.size) // 80)
    return (
        max(0, left * scale - padding),
        max(0, top * scale - padding),
        min(alpha.width, (right + 1) * scale + padding),
        min(alpha.height, (bottom + 1) * scale + padding),
    )


def prepare_signature_image(content: bytes) -> bytes:
    """Crop handwriting, remove paper, and store the ink as transparent black PNG."""
    try:
        with Image.open(BytesIO(content)) as source:
            image = source.convert("RGBA")
    except (OSError, UnidentifiedImageError) as error:
        raise ValueError("Signature image is unreadable") from error

    background = _background_luminance(image)
    source_pixels = list(image.getdata())
    has_coloured_ink = any(
        max(red, green, blue) > 0
        and (max(red, green, blue) - min(red, green, blue)) / max(red, green, blue) >= 0.28
        for red, green, blue, _alpha in source_pixels
    )
    pixels = []
    for red, green, blue, alpha in source_pixels:
        maximum = max(red, green, blue)
        saturation = 0 if maximum == 0 else (maximum - min(red, green, blue)) / maximum
        luminance = _luminance(red, green, blue)
        # Coloured pens (like the supplied orange signatures) are separated by
        # saturation, while black ink is separated from the page by darkness.
        coloured_ink = max(0.0, min(1.0, (saturation - 0.16) / 0.30))
        dark_ink = max(0.0, min(1.0, (background - luminance - 12) / 72))
        ink_opacity = coloured_ink if has_coloured_ink else max(coloured_ink, dark_ink)
        pixels.append((0, 0, 0, round(alpha * ink_opacity)))
    image.putdata(pixels)
    visible = _largest_ink_bounds(image.getchannel("A"))
    if visible is None:
        raise ValueError("No visible signature ink was found in the uploaded image")
    image = image.crop(visible)
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
