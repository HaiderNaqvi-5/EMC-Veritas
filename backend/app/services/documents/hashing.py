import hashlib


def sha256_hex(pdf_bytes: bytes) -> str:
    """Calculate the stored integrity hash from the final generated PDF bytes."""
    return hashlib.sha256(pdf_bytes).hexdigest()
