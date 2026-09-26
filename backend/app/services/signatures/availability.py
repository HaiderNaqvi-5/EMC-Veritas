from collections.abc import Iterable, Mapping
from datetime import date

from app.models.domain import Signatory
from app.services.signatures.rendering import signature_field_name


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


def select_effective_signatories_for_fields(
    signatories: Iterable[Signatory], field_names: Iterable[str], governing_date: date
) -> dict[str, Signatory]:
    """Select the current uploaded signatory for each configured signature box."""
    selected: dict[str, Signatory] = {}
    for field_name in field_names:
        candidates = [
            signatory
            for signatory in signatories
            if signatory.active
            and signature_field_name(signatory.official_title) == field_name
            and governing_date >= signatory.effective_start_date
            and (
                signatory.effective_end_date is None
                or governing_date <= signatory.effective_end_date
            )
        ]
        if candidates:
            selected[field_name] = max(
                candidates, key=lambda signatory: (signatory.effective_start_date, str(signatory.id))
            )
    return selected
