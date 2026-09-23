VALID_SIGNATURE_CHOICES = frozenset({"retain", "replace"})


def require_signature_choice(choice: str | None) -> str:
    if choice not in VALID_SIGNATURE_CHOICES:
        raise ValueError("Choose whether to retain or replace sample signatures")
    return choice
