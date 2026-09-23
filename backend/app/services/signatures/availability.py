from collections.abc import Iterable, Mapping
from datetime import date

from app.models.domain import Signatory


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


def select_effective_signatories(
    signatories: Iterable[Signatory], required: tuple[str, ...], governing_date: date
) -> dict[str, Signatory]:
    """Choose one historical signatory per required title deterministically."""
    selected: dict[str, Signatory] = {}
    for title in required:
        candidates = [
            signatory
            for signatory in signatories
            if signatory.active
            and signatory.official_title == title
            and governing_date >= signatory.effective_start_date
            and (
                signatory.effective_end_date is None
                or governing_date <= signatory.effective_end_date
            )
        ]
        if candidates:
            selected[title] = max(
                candidates, key=lambda signatory: (signatory.effective_start_date, str(signatory.id))
            )
    return selected
