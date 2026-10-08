from io import BytesIO

import qrcode


def qr_png(payload: str, *, border: int = 1) -> bytes:
    # The certificate template already reserves a dedicated white QR panel.
    # qrcode.make() adds a four-module white border of its own, making the
    # readable pattern look undersized inside that panel. Keep one quiet-zone
    # module for reliable scanning and let the actual code use the space.
    code = qrcode.QRCode(box_size=10, border=border)
    code.add_data(payload)
    code.make(fit=True)
    image = code.make_image(fill_color="black", back_color="white")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
