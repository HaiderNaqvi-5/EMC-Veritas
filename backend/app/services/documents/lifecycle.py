from collections.abc import Iterable, Mapping
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.domain import DocumentStatus, IssuedDocument, TemplateField
from app.services.audit import record_audit_event
from app.services.documents.hashing import sha256_hex
from app.services.documents.qr import verification_url
from app.services.documents.rendering import CertificateRenderingError, render_certificate
from app.services.templates.fields import REQUIRED_CERTIFICATE_FIELDS


class DocumentLifecycleError(ValueError):
    """Raised when a document cannot be safely generated or downloaded."""


def document_storage_key(document: IssuedDocument) -> str:
    return f"issued-documents/{document.id}/v{document.version}.pdf"


def generate_on_first_download(
    db: Session,
    *,
    document: IssuedDocument,
    template_pdf: bytes,
    template_fields: Iterable[TemplateField],
    values: Mapping[str, str | date],
    storage: object,
    public_base_url: str,
    actor_admin_id: UUID | None = None,
    image_values: Mapping[str, bytes] | None = None,
    required_field_names: frozenset[str] | None = None,
) -> bytes:
    """Return an issued PDF, creating and caching it only on the first valid download."""
    if document.status is not DocumentStatus.VALID:
        raise DocumentLifecycleError("Only valid documents can be downloaded")

    if document.storage_key:
        return storage.download(document.storage_key)

    try:
        field_list = list(template_fields)
        custom_fonts = {
            field.custom_font_storage_key: storage.download(field.custom_font_storage_key)
            for field in field_list
            if getattr(field, "custom_font_storage_key", None)
        }
        output = render_certificate(
            template_pdf,
            field_list,
            values,
            verification_url=verification_url(public_base_url, document.verification_id),
            image_values=image_values,
            custom_fonts=custom_fonts,
            required_field_names=required_field_names or REQUIRED_CERTIFICATE_FIELDS,
        )
    except CertificateRenderingError as error:
        raise DocumentLifecycleError(str(error)) from error

    key = document_storage_key(document)
    storage.upload(key, output, "application/pdf")
    document.storage_key = key
    document.sha256 = sha256_hex(output)
    record_audit_event(
        db,
        actor_admin_id=actor_admin_id,
        event_type="DOCUMENT_GENERATED",
        entity_type="issued_document",
        entity_id=document.id,
        payload={"storage_key": key, "sha256": document.sha256, "version": document.version},
    )
    return output
