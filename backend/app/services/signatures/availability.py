from collections.abc import Iterable, Mapping
from datetime import date


def missing_titles(
    required: tuple[str, ...],
    available: Mapping[str, Iterable[tuple[date, date | None]]],
    governing_date: date,
) -> list[str]:
    missing = []
    for title in required:
        periods = available.get(title, ())
        if not any(
            governing_date >= start and (end is None or governing_date <= end)
            for start, end in periods
        ):
            missing.append(title)
    return missing
