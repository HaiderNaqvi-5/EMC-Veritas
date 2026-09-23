from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import AdminLookupRequest, AdminLookupResponse, AdminSessionResponse, LoginRequest, PasswordChangeRequest
from app.services.audit import record_audit_event
from app.services.auth import authenticate, change_password, find_admin_by_roll_number

router = APIRouter(prefix="/auth", tags=["admin-auth"])


def session_response(request: Request) -> AdminSessionResponse:
    role = request.session.get("role")
    return AdminSessionResponse(authenticated=bool(request.session.get("admin_id")), role=role, temporary_password_change_required=bool(request.session.get("must_change_password")))


@router.post("/lookup", response_model=AdminLookupResponse)
def lookup(payload: AdminLookupRequest, db: Session = Depends(get_db)) -> AdminLookupResponse:
    admin = find_admin_by_roll_number(db, payload.roll_number)
    return AdminLookupResponse(is_admin=admin is not None and admin.active, active=admin is not None and admin.active)


@router.post("/login", response_model=AdminSessionResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> AdminSessionResponse:
    admin = authenticate(db, payload.roll_number, payload.password)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid administrator credentials")
    request.session.clear()
    request.session.update({"admin_id": str(admin.id), "role": admin.role.value, "must_change_password": admin.must_change_password})
    record_audit_event(db, event_type="ADMIN_LOGIN", entity_type="admin", entity_id=admin.id, payload={}, actor_admin_id=admin.id)
    db.commit()
    return session_response(request)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/session", response_model=AdminSessionResponse)
def current_session(request: Request) -> AdminSessionResponse:
    return session_response(request)


@router.post("/change-temporary-password", status_code=status.HTTP_204_NO_CONTENT)
def change_temporary_password(payload: PasswordChangeRequest, request: Request, db: Session = Depends(get_db)) -> Response:
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin session required")
    from app.models.domain import Admin
    admin = db.get(Admin, admin_id)
    if admin is None or not admin.active or not change_password(admin, payload.current_password, payload.new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    request.session["must_change_password"] = False
    record_audit_event(db, event_type="ADMIN_PASSWORD_CHANGED", entity_type="admin", entity_id=admin.id, payload={}, actor_admin_id=admin.id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
