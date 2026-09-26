import re
from collections.abc import Iterable

from app.models.domain import TemplateField


def signature_field_name(official_title: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", official_title.lower()).strip("_")
    return "signature_" + normalized


def configured_signature_field_names(fields: Iterable[TemplateField]) -> list[str]:
    """Return every image field explicitly requested by a certificate template."""
    return sorted({field.field_name for field in fields if field.field_name.startswith("signature_")})


def should_replace_signatures(signature_handling: str | None, fields: Iterable[TemplateField]) -> bool:
    """Decide whether a template must draw configured signature images.

    Explicit ``signature_<title>`` fields are image placeholders, not sample
    signatures.  Older drafts could accidentally be saved with ``retain``
    while containing those fields, which left a blank rectangle in every
    preview.  Treating an explicit image placeholder as replace mode keeps
    those existing templates usable without mutating their approved config.
    """
    return signature_handling == "replace" or bool(configured_signature_field_names(fields))


def missing_signature_fields(fields: Iterable[TemplateField], titles: Iterable[str]) -> list[str]:
    configured = {field.field_name for field in fields}
    return [field_name for field_name in map(signature_field_name, titles) if field_name not in configured]
