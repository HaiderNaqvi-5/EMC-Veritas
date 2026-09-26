import re
from collections.abc import Iterable

from app.models.domain import TemplateField


def signature_field_name(official_title: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", official_title.lower()).strip("_")
    return "signature_" + normalized


def configured_signature_field_names(fields: Iterable[TemplateField]) -> list[str]:
    """Return every image field explicitly requested by a certificate template."""
    return sorted({field.field_name for field in fields if field.field_name.startswith("signature_")})


def missing_signature_fields(fields: Iterable[TemplateField], titles: Iterable[str]) -> list[str]:
    configured = {field.field_name for field in fields}
    return [field_name for field_name in map(signature_field_name, titles) if field_name not in configured]
