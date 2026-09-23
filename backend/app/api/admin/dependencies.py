from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain import Admin, AdminRole


def current_active_admin(request: Request, db: Session = Depends(get_db)) -> Admin:
    raw_admin_id = request.session.get("admin_id")
    if not raw_admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin session required")
    try:
        admin_id = UUID(raw_admin_id)
    except (TypeError, ValueError) as error:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin session required") from error
    admin = db.get(Admin, admin_id)
    if admin is None or not admin.active:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin session required")
    return admin


def super_admin_required(admin: Admin = Depends(current_active_admin)) -> Admin:
    if admin.role != AdminRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin access required")
    return admin
