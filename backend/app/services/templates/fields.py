REQUIRED_CERTIFICATE_FIELDS = frozenset({"student_name", "roll_number", "activity_name", "activity_date"})
SYSTEM_MANAGED_CERTIFICATE_FIELDS = frozenset({"verification_id", "qr_code"})
APPROVAL_REQUIRED_CERTIFICATE_FIELDS = REQUIRED_CERTIFICATE_FIELDS | SYSTEM_MANAGED_CERTIFICATE_FIELDS


def missing_required_fields(field_names: set[str]) -> set[str]:
    return APPROVAL_REQUIRED_CERTIFICATE_FIELDS - field_names
