from io import BytesIO

from PIL import Image, ImageDraw

from app.services.signatures.image import prepare_signature_image


def test_prepare_signature_image_removes_paper_and_blackens_ink() -> None:
    image = Image.new("RGB", (100, 80), (145, 145, 145))
    ImageDraw.Draw(image).rectangle((35, 30, 65, 42), fill=(220, 90, 20))
    source = BytesIO()
    image.save(source, format="PNG")

    output = prepare_signature_image(source.getvalue())
    with Image.open(BytesIO(output)).convert("RGBA") as result:
        assert result.size[0] < 50
        assert result.size[1] < 40
        red, green, blue, alpha = result.getpixel((result.width // 2, result.height // 2))
        assert (red, green, blue) == (0, 0, 0)
        assert alpha > 0
