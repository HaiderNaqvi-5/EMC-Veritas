from io import BytesIO

from PIL import Image

from app.services.signatures.image import prepare_signature_image


def test_prepare_signature_image_removes_paper_and_blackens_ink() -> None:
    image = Image.new("RGB", (2, 1), "white")
    image.putpixel((1, 0), (20, 90, 180))
    source = BytesIO()
    image.save(source, format="PNG")

    output = prepare_signature_image(source.getvalue())
    with Image.open(BytesIO(output)).convert("RGBA") as result:
        assert result.getpixel((0, 0)) == (0, 0, 0, 0)
        red, green, blue, alpha = result.getpixel((1, 0))
        assert (red, green, blue) == (0, 0, 0)
        assert alpha > 0
