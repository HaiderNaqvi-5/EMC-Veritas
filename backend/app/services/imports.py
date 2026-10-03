from io import BytesIO

from openpyxl import Workbook, load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import Activity, ActivityParticipant, Student
from app.services.students import normalize_roll_number

ROLL = {"roll number", "roll no", "registration no", "roll_number"}
NAME = {"full name", "student name", "name", "full_name"}
EMAIL = {"email", "email address", "student email", "email_address"}

# Keep roster-email support available for a future rollout without making it
# part of the current student-import workflow.
STUDENT_IMPORT_EMAIL_ENABLED = False

def preview_students(db: Session, content: bytes) -> dict:
    sheet = load_workbook(BytesIO(content), read_only=True, data_only=True).active
    headers = {str(value).strip().lower(): index for index, value in enumerate(next(sheet.iter_rows(values_only=True))) if value}
    roll_index = next((headers[key] for key in ROLL if key in headers), None); name_index = next((headers[key] for key in NAME if key in headers), None); email_index = next((headers[key] for key in EMAIL if key in headers), None) if STUDENT_IMPORT_EMAIL_ENABLED else None
    if roll_index is None or name_index is None: raise ValueError("Spreadsheet must include Roll Number and Full Name headings")

    # ⚡ Bolt: Bulk fetch existing students to prevent N+1 queries during preview
    raw_rows = list(sheet.iter_rows(min_row=2, values_only=True))
    all_rolls = []
    for values in raw_rows:
        roll = normalize_roll_number(str(values[roll_index])) if values[roll_index] is not None else ""
        if roll:
            all_rolls.append(roll)

    student_by_roll = {}
    if all_rolls:
        existing_students = db.scalars(select(Student).where(Student.roll_number.in_(all_rolls))).all()
        student_by_roll = {s.roll_number: s for s in existing_students}

    seen=set(); rows=[]; counts={"valid_rows":0,"duplicate_rows":0,"conflicting_rows":0,"invalid_rows":0}
    for number, values in enumerate(raw_rows, start=2):
        roll=normalize_roll_number(str(values[roll_index])) if values[roll_index] is not None else ""; name=str(values[name_index]).strip() if values[name_index] is not None else ""; email=str(values[email_index]).strip().lower() if email_index is not None and values[email_index] is not None else ""
        outcome="valid"; detail=None
        if not roll or not name: outcome="invalid"; detail="Roll number and full name are required"
        elif roll in seen: outcome="duplicate"; detail="Duplicate roll number in spreadsheet"
        else:
            existing = student_by_roll.get(roll)
            if existing and existing.full_name != name: outcome="conflict"; detail="Existing student name differs; choose a resolution explicitly"
            elif STUDENT_IMPORT_EMAIL_ENABLED and email and existing and existing.email and existing.email.lower() != email: outcome="conflict"; detail="Existing verified email differs; use the Super Admin recovery flow instead"
        seen.add(roll)
        count_key = "conflicting_rows" if outcome == "conflict" else f"{outcome}_rows"
        counts[count_key] += 1
        rows.append({"row_number":number,"roll_number":roll or None,"full_name":name or None,"email":email or None,"outcome":outcome,"detail":detail})
    return {**counts,"rows":rows}

def participant_export(db: Session, activity_id) -> bytes:
    activity = db.get(Activity, activity_id)
    if activity is None: raise LookupError("Activity not found")
    rows = db.execute(select(ActivityParticipant, Student).join(Student, ActivityParticipant.student_id == Student.id).where(ActivityParticipant.activity_id == activity_id)).all()
    workbook=Workbook(); sheet=workbook.active; sheet.title="Participants"
    sheet.append(["Roll Number","Student Name","Activity Name","Activity Date","Eligibility Status"])
    for participant, student in rows: sheet.append([student.roll_number,student.full_name,activity.name,activity.activity_date.isoformat(),"Eligible" if participant.eligible else "Ineligible"])
    output=BytesIO(); workbook.save(output); return output.getvalue()

def import_activity_participants(db: Session, activity_id, content: bytes) -> dict:
    """Link existing active students from an Excel attendee list to one activity."""
    activity = db.get(Activity, activity_id)
    if activity is None: raise LookupError("Activity not found")
    sheet = load_workbook(BytesIO(content), read_only=True, data_only=True).active
    headers = {str(value).strip().lower(): index for index, value in enumerate(next(sheet.iter_rows(values_only=True))) if value}
    roll_index = next((headers[key] for key in ROLL if key in headers), None)
    if roll_index is None: raise ValueError("Spreadsheet must include a Roll Number heading")

    # ⚡ Bolt: Bulk fetch students and participants to prevent N+1 queries during import
    raw_rows = list(sheet.iter_rows(min_row=2, values_only=True))
    all_rolls = []
    seen_in_sheet: set[str] = set()
    for values in raw_rows:
        roll = normalize_roll_number(str(values[roll_index])) if values[roll_index] is not None else ""
        if roll and roll not in seen_in_sheet:
            seen_in_sheet.add(roll)
            all_rolls.append(roll)

    student_by_roll = {}
    if all_rolls:
        existing_students = db.scalars(select(Student).where(Student.roll_number.in_(all_rolls), Student.active.is_(True))).all()
        student_by_roll = {s.roll_number: s for s in existing_students}

    existing_participant_student_ids = set()
    student_ids = [s.id for s in student_by_roll.values()]
    if student_ids:
        existing_participant_student_ids = set(db.scalars(
            select(ActivityParticipant.student_id)
            .where(
                ActivityParticipant.activity_id == activity_id,
                ActivityParticipant.student_id.in_(student_ids)
            )
        ).all())

    added = existing = 0; unknown_roll_numbers: list[str] = []; processed: set[str] = set()
    for values in raw_rows:
        roll = normalize_roll_number(str(values[roll_index])) if values[roll_index] is not None else ""
        if not roll or roll in processed: continue
        processed.add(roll)

        student = student_by_roll.get(roll)
        if student is None:
            unknown_roll_numbers.append(roll); continue

        if student.id in existing_participant_student_ids:
            existing += 1; continue

        db.add(ActivityParticipant(activity_id=activity_id, student_id=student.id, eligible=True)); added += 1
    return {"added": added, "already_present": existing, "unknown_roll_numbers": unknown_roll_numbers}
