REQUIRED_CERTIFICATE_FIELDS = frozenset({"student_name", "roll_number", "activity_name", "activity_date"})


def missing_required_fields(field_names: set[str]) -> set[str]:
    return REQUIRED_CERTIFICATE_FIELDS - field_names
