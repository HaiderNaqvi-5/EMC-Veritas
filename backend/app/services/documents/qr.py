from urllib.parse import quote


def verification_url(public_base_url: str, verification_id: str) -> str:
    return f"{public_base_url.rstrip('/')}/verify/{quote(verification_id, safe='')}"
