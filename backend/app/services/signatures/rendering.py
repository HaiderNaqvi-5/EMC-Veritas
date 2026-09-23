from collections.abc import Iterable

from app.models.domain import TemplateField


def signature_field_name(official_title: str) -> str:
    return "signature_" + official_title.lower().replace(" ", "_")


def missing_signature_fields(fields: Iterable[TemplateField], titles: Iterable[str]) -> list[str]:
    configured = {field.field_name for field in fields}
    return [field_name for field_name in map(signature_field_name, titles) if field_name not in configured]
