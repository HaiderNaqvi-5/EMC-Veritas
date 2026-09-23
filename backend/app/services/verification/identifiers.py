import secrets

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_verification_id() -> str:
    """Return a random, human-readable, non-sequential public verification ID."""
    return "EMC-" + "".join(secrets.choice(ALPHABET) for _ in range(8))
