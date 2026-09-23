from app.services.executive.constants import EXECUTIVE_ROLES, SOCIETIES


def validate_membership(role: str, society_name: str | None) -> None:
    if role not in EXECUTIVE_ROLES:
        raise ValueError("Unsupported Executive Council role")
    if role == "Society Head" and society_name not in SOCIETIES:
        raise ValueError("Society Head must reference an approved society")
    if role != "Society Head" and society_name is not None:
        raise ValueError("Only Society Head memberships may reference a society")
