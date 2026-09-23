import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SessionStatus(str, enum.Enum): ACTIVE = "ACTIVE"; CLOSED = "CLOSED"
class ActivityStatus(str, enum.Enum): DRAFT = "DRAFT"; READY = "READY"; PUBLISHED = "PUBLISHED"; ARCHIVED = "ARCHIVED"
class MembershipStatus(str, enum.Enum): ACTIVE = "ACTIVE"; COMPLETED = "COMPLETED"; REMOVED = "REMOVED"
class DocumentStatus(str, enum.Enum): VALID = "VALID"; REVOKED = "REVOKED"; SUPERSEDED = "SUPERSEDED"
class DocumentType(str, enum.Enum): ACTIVITY_CERTIFICATE = "ACTIVITY_CERTIFICATE"; LEADERSHIP_RECOGNITION = "LEADERSHIP_RECOGNITION"; END_OF_TENURE_APPRECIATION = "END_OF_TENURE_APPRECIATION"
class AdminRole(str, enum.Enum): ADMIN = "ADMIN"; SUPER_ADMIN = "SUPER_ADMIN"


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Student(Timestamped, Base):
    __tablename__ = "students"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roll_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Admin(Timestamped, Base):
    __tablename__ = "admins"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[AdminRole] = mapped_column(Enum(AdminRole, name="admin_role"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class EmcSession(Timestamped, Base):
    __tablename__ = "emc_sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus, name="session_status"), nullable=False)
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="session_valid_dates"),
        Index("uq_active_emc_session", "status", unique=True, postgresql_where=(status == SessionStatus.ACTIVE)),
    )


class Activity(Timestamped, Base):
    __tablename__ = "activities"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("emc_sessions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    issue_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ActivityStatus] = mapped_column(Enum(ActivityStatus, name="activity_status"), default=ActivityStatus.DRAFT, nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("templates.id"))
    created_by_admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admins.id"), nullable=False)


class ActivityParticipant(Timestamped, Base):
    __tablename__ = "activity_participants"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("activities.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    __table_args__ = (UniqueConstraint("activity_id", "student_id", name="uq_participant_per_activity"),)


class Society(Timestamped, Base):
    __tablename__ = "societies"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ExecutiveMembership(Timestamped, Base):
    __tablename__ = "executive_memberships"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("emc_sessions.id"), nullable=False)
    society_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("societies.id"))
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[MembershipStatus] = mapped_column(Enum(MembershipStatus, name="membership_status"), nullable=False)
    __table_args__ = (
        UniqueConstraint("student_id", "session_id", name="uq_ec_role_per_student_session"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="membership_valid_dates"),
        ExcludeConstraint(
            ("session_id", "="),
            ("society_id", "="),
            (func.daterange(start_date, func.coalesce(end_date, text("'infinity'::date")), "[]"), "&&"),
            name="excl_society_head_tenure",
            using="gist",
            where=(role == "Society Head"),
        ),
    )


class Template(Timestamped, Base):
    __tablename__ = "templates"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Set only after a Super Admin explicitly chooses retain or replace.
    signature_handling: Mapped[str | None] = mapped_column(String(16))


class TemplateField(Timestamped, Base):
    __tablename__ = "template_fields"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("templates.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    x: Mapped[int] = mapped_column(Integer, nullable=False); y: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False); height: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("template_id", "field_name", name="uq_template_field"),)


class LeadershipTemplate(Timestamped, Base):
    __tablename__ = "leadership_templates"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type", create_type=False), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    # Set only after a Super Admin explicitly chooses retain or replace.
    signature_handling: Mapped[str | None] = mapped_column(String(16))
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    __table_args__ = (
        Index(
            "uq_active_leadership_template",
            "role",
            "document_type",
            unique=True,
            postgresql_where=(active.is_(True) & archived.is_(False)),
        ),
    )


class LeadershipTemplateField(Timestamped, Base):
    __tablename__ = "leadership_template_fields"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    leadership_template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leadership_templates.id"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (
        UniqueConstraint("leadership_template_id", "field_name", name="uq_leadership_template_field"),
    )


class Signatory(Timestamped, Base):
    __tablename__ = "signatories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    official_title: Mapped[str] = mapped_column(String(255), nullable=False)
    signature_storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    effective_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_end_date: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DocumentSignatory(Base):
    """Immutable signatory snapshot chosen when a document is reserved."""

    __tablename__ = "document_signatories"
    issued_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("issued_documents.id"), primary_key=True
    )
    signatory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("signatories.id"), primary_key=True)
    official_title: Mapped[str] = mapped_column(String(255), nullable=False)


class IssuedDocument(Timestamped, Base):
    __tablename__ = "issued_documents"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    activity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("activities.id"))
    executive_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("executive_memberships.id")
    )
    leadership_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("leadership_templates.id")
    )
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType, name="document_type"), nullable=False)
    verification_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus, name="document_status"), default=DocumentStatus.VALID, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(500))
    sha256: Mapped[str | None] = mapped_column(String(64))
    # A leadership letter must render from its reserved record, not mutable live membership data.
    render_payload_json: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint(
            "executive_membership_id",
            "document_type",
            "version",
            name="uq_leadership_document_membership_type_version",
        ),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admins.id"))
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
