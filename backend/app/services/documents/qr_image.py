from io import BytesIO

import qrcode


def qr_png(payload: str) -> bytes:
    image = qrcode.make(payload)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
