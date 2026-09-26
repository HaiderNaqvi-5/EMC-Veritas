from io import BytesIO

from PIL import Image, ImageDraw

from app.services.signatures.image import prepare_signature_image


def test_prepare_signature_image_removes_paper_and_blackens_ink() -> None:
    image = Image.new("RGB", (100, 80), (145, 145, 145))
    ImageDraw.Draw(image).rectangle((35, 30, 65, 42), fill=(220, 90, 20))
    image.putpixel((0, 0), (20, 90, 180))
    source = BytesIO()
    image.save(source, format="PNG")

    output = prepare_signature_image(source.getvalue())
    with Image.open(BytesIO(output)).convert("RGBA") as result:
        assert result.size[0] < 70
        assert result.size[1] < 50
        red, green, blue, alpha = result.getpixel((result.width // 2, result.height // 2))
        assert (red, green, blue) == (0, 0, 0)
        assert alpha > 0


def test_prepare_signature_image_ignores_one_coloured_noise_pixel_for_black_ink() -> None:
    image = Image.new("RGB", (160, 100), (160, 160, 160))
    drawing = ImageDraw.Draw(image)
    drawing.line((45, 55, 115, 40), fill=(20, 20, 20), width=5)
    image.putpixel((0, 0), (20, 90, 180))
    source = BytesIO()
    image.save(source, format="PNG")

    output = prepare_signature_image(source.getvalue())
    with Image.open(BytesIO(output)).convert("RGBA") as result:
        assert result.size[0] < 100
        assert result.size[1] < 60
        assert max(result.getchannel("A").getextrema()) >= 100


def test_prepare_signature_image_recovers_ink_from_a_nearly_transparent_legacy_png() -> None:
    image = Image.new("RGBA", (160, 100), (160, 160, 160, 2))
    drawing = ImageDraw.Draw(image)
    drawing.line((45, 55, 115, 40), fill=(20, 20, 20, 2), width=5)
    source = BytesIO()
    image.save(source, format="PNG")

    output = prepare_signature_image(source.getvalue())
    with Image.open(BytesIO(output)).convert("RGBA") as result:
        assert max(result.getchannel("A").getextrema()) >= 100
