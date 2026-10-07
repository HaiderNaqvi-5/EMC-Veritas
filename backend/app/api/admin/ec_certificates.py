from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.admin.dependencies import super_admin_required
from app.core.settings import settings
from app.db.session import get_db
from app.models.domain import (
    Activity,
    ActivityOrganizer,
    ActivityStatus,
    Admin,
    DocumentStatus,
    DocumentType,
    ExecutiveMembership,
    IssuedDocument,
    MembershipStatus,
    Signatory,
    Student,
    Template,
    TemplateField,
)
from app.services.audit import record_audit_event
from app.services.documents.issuance import reserve_document
from app.services.documents.lifecycle import DocumentLifecycleError, generate_on_first_download
from app.services.signatures.availability import select_effective_signatories_for_fields
from app.services.signatures.rendering import (
    configured_signature_field_names,
    should_replace_signatures,
)
from app.services.storage.supabase import SupabaseStorage
from app.services.templates.fields import missing_required_fields

router = APIRouter(prefix="/ec-certificates", tags=["executive council certificates"])
EMC_TIMEZONE = ZoneInfo("Asia/Karachi")


class OrganizerSelection(BaseModel):
    membership_ids: list[UUID]


class TemplateSelection(BaseModel):
    template_id: UUID


class EcActivityResponse(BaseModel):
    id: UUID
    session_id: UUID
    name: str
    activity_date: str
    status: str


class EcMemberResponse(BaseModel):
    membership_id: UUID
    student_id: UUID
    roll_number: str
    full_name: str
    role: str
    selected: bool


class EcIssueResponse(BaseModel):
    issued: int
    already_issued: int
    document_ids: list[UUID]


def _activity(db: Session, activity_id: UUID) -> Activity:
    activity = db.get(Activity, activity_id)
    if activity is None or activity.status is ActivityStatus.ARCHIVED:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.get("/activities", response_model=list[EcActivityResponse])
def list_ec_activities(
    db: Session = Depends(get_db), _: Admin = Depends(super_admin_required)
) -> list[EcActivityResponse]:
    activities = db.scalars(
        select(Activity)
        .where(Activity.status != ActivityStatus.ARCHIVED)
        .order_by(Activity.activity_date.desc(), Activity.name)
    ).all()
    return [
        EcActivityResponse(
            id=item.id,
            session_id=item.session_id,
            name=item.name,
            activity_date=item.activity_date.isoformat(),
            status=item.status.value,
        )
        for item in activities
    ]


@router.get("/activities/{activity_id}/members", response_model=list[EcMemberResponse])
def list_ec_members(
    activity_id: UUID,
    db: Session = Depends(get_db),
    _: Admin = Depends(super_admin_required),
) -> list[EcMemberResponse]:
    activity = _activity(db, activity_id)
    selected = set(
        db.scalars(
            select(ActivityOrganizer.executive_membership_id).where(
                ActivityOrganizer.activity_id == activity.id
            )
        ).all()
    )
    rows = db.execute(
        select(ExecutiveMembership, Student)
        .join(Student, ExecutiveMembership.student_id == Student.id)
        .where(
            ExecutiveMembership.session_id == activity.session_id,
            ExecutiveMembership.status != MembershipStatus.REMOVED,
            Student.active.is_(True),
        )
        .order_by(ExecutiveMembership.role, Student.full_name)
    ).all()
    return [
        EcMemberResponse(
            membership_id=membership.id,
            student_id=student.id,
            roll_number=student.roll_number,
            full_name=student.full_name,
            role=membership.role,
            selected=membership.id in selected,
        )
        for membership, student in rows
    ]


@router.put("/activities/{activity_id}/members", response_model=list[EcMemberResponse])
def select_ec_members(
    activity_id: UUID,
    payload: OrganizerSelection,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> list[EcMemberResponse]:
    activity = _activity(db, activity_id)
    unique_ids = set(payload.membership_ids)
    valid_ids = set(
        db.scalars(
            select(ExecutiveMembership.id).where(
                ExecutiveMembership.id.in_(unique_ids),
                ExecutiveMembership.session_id == activity.session_id,
                ExecutiveMembership.status != MembershipStatus.REMOVED,
            )
        ).all()
    )
    if valid_ids != unique_ids:
        raise HTTPException(
            status_code=422,
            detail="Every selected organizer must be an EC member of the activity session",
        )
    db.execute(delete(ActivityOrganizer).where(ActivityOrganizer.activity_id == activity.id))
    for membership_id in sorted(valid_ids, key=str):
        db.add(
            ActivityOrganizer(
                activity_id=activity.id, executive_membership_id=membership_id
            )
        )
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="ACTIVITY_EC_ORGANIZERS_UPDATED",
        entity_type="activity",
        entity_id=activity.id,
        payload={"membership_ids": [str(item) for item in sorted(valid_ids, key=str)]},
    )
    db.commit()
    return list_ec_members(activity.id, db, admin)


@router.post("/activities/{activity_id}/issue", response_model=EcIssueResponse)
def issue_ec_certificates(
    activity_id: UUID,
    payload: TemplateSelection,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> EcIssueResponse:
    activity = _activity(db, activity_id)
    template = db.scalar(
        select(Template).where(
            Template.id == payload.template_id,
            Template.purpose == "EXECUTIVE_COUNCIL",
            Template.approved.is_(True),
            Template.archived.is_(False),
        )
    )
    if template is None:
        raise HTTPException(status_code=409, detail="Choose an approved EC certificate template")
    fields = list(
        db.scalars(select(TemplateField).where(TemplateField.template_id == template.id)).all()
    )
    missing = missing_required_fields({field.field_name for field in fields})
    if missing:
        raise HTTPException(
            status_code=409,
            detail="EC template is missing required fields: " + ", ".join(sorted(missing)),
        )
    rows = db.execute(
        select(ActivityOrganizer, ExecutiveMembership, Student)
        .join(
            ExecutiveMembership,
            ActivityOrganizer.executive_membership_id == ExecutiveMembership.id,
        )
        .join(Student, ExecutiveMembership.student_id == Student.id)
        .where(ActivityOrganizer.activity_id == activity.id, Student.active.is_(True))
    ).all()
    if not rows:
        raise HTTPException(status_code=409, detail="Select at least one EC organizer first")
    existing_student_ids = set(
        db.scalars(
            select(IssuedDocument.student_id).where(
                IssuedDocument.activity_id == activity.id,
                IssuedDocument.document_type == DocumentType.EXECUTIVE_COUNCIL_CERTIFICATE,
                IssuedDocument.status == DocumentStatus.VALID,
            )
        ).all()
    )
    issue_date = datetime.now(EMC_TIMEZONE).date()
    selected_signatories: dict[str, Signatory] = {}
    if should_replace_signatures(template.signature_handling, fields):
        signature_fields = configured_signature_field_names(fields)
        available = list(db.scalars(select(Signatory).where(Signatory.active.is_(True))).all())
        selected_signatories = select_effective_signatories_for_fields(
            available, signature_fields, issue_date
        )
        unavailable = sorted(set(signature_fields) - set(selected_signatories))
        if unavailable:
            raise HTTPException(
                status_code=409,
                detail="Configured signatories are unavailable for: " + ", ".join(unavailable),
            )
    storage = SupabaseStorage()
    try:
        template_pdf = storage.download(template.storage_key)
        signature_images = {
            field_name: storage.download(signatory.signature_storage_key)
            for field_name, signatory in selected_signatories.items()
        }
        document_ids: list[UUID] = []
        skipped = 0
        for _, membership, student in rows:
            if student.id in existing_student_ids:
                skipped += 1
                continue
            values = {
                "student_name": student.full_name,
                "roll_number": student.roll_number,
                "activity_name": activity.name,
                "activity_date": activity.activity_date,
                "role": membership.role,
                "issue_date": issue_date,
            }
            document = reserve_document(
                db,
                student_id=student.id,
                activity_id=activity.id,
                template_id=template.id,
                document_type=DocumentType.EXECUTIVE_COUNCIL_CERTIFICATE,
                issue_date=issue_date,
                render_values=values,
                actor_admin_id=admin.id,
                signatories=tuple(selected_signatories.values()),
            )
            values["verification_id"] = document.verification_id
            generate_on_first_download(
                db,
                document=document,
                template_pdf=template_pdf,
                template_fields=fields,
                values=values,
                storage=storage,
                public_base_url=settings.public_app_url,
                actor_admin_id=admin.id,
                image_values=signature_images,
            )
            document_ids.append(document.id)
        record_audit_event(
            db,
            actor_admin_id=admin.id,
            event_type="ACTIVITY_EC_CERTIFICATES_ISSUED",
            entity_type="activity",
            entity_id=activity.id,
            payload={
                "template_id": str(template.id),
                "issued_document_ids": [str(item) for item in document_ids],
                "already_issued": skipped,
            },
        )
        db.commit()
    except (RuntimeError, DocumentLifecycleError) as error:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="EC certificates could not be prepared in document storage",
        ) from error
    return EcIssueResponse(
        issued=len(document_ids), already_issued=skipped, document_ids=document_ids
    )
