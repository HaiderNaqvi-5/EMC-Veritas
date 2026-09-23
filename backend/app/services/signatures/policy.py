def required_titles(*, role: str | None = None, appreciation: bool = False) -> tuple[str, ...]:
    if appreciation or role in {"President", "Vice President"}:
        return ("DSA", "HOD")
    if role:
        return ("President", "DSA", "HOD")
    return ("President", "DSA")
