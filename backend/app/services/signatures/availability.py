from datetime import date


def missing_titles(required: tuple[str, ...], available: dict[str, tuple[date, date | None]], governing_date: date) -> list[str]:
    missing = []
    for title in required:
        period = available.get(title)
        if period is None or governing_date < period[0] or (period[1] is not None and governing_date > period[1]):
            missing.append(title)
    return missing
