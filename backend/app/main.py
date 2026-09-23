from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.admin.activities import router as admin_activities_router
from app.api.admin.admins import router as admin_admins_router
from app.api.admin.audit import router as admin_audit_router
from app.api.admin.auth import router as admin_auth_router
from app.api.admin.documents import router as admin_documents_router
from app.api.admin.executive import router as admin_executive_router
from app.api.admin.imports import router as admin_imports_router
from app.api.admin.leadership_templates import router as admin_leadership_templates_router
from app.api.admin.sessions import router as admin_sessions_router
from app.api.admin.signatories import router as admin_signatories_router
from app.api.admin.students import router as admin_students_router
from app.api.admin.templates import router as admin_templates_router
from app.api.public.router import router as public_router
from app.core.settings import settings
from app.services.readiness.router import router as readiness_router


def create_app() -> FastAPI:
    app = FastAPI(title="EMC Veritas API", version="0.1.0")
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        https_only=settings.cookie_secure,
        same_site=settings.cookie_same_site,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(readiness_router, prefix=settings.api_prefix)
    app.include_router(public_router, prefix=settings.api_prefix)
    app.include_router(admin_auth_router, prefix=f"{settings.api_prefix}/admin")
    app.include_router(admin_admins_router, prefix=f"{settings.api_prefix}/admin")
    app.include_router(admin_audit_router, prefix=f"{settings.api_prefix}/admin")
    app.include_router(admin_activities_router, prefix=f"{settings.api_prefix}/admin")
    app.include_router(admin_documents_router, prefix=f"{settings.api_prefix}/admin")
    app.include_router(admin_executive_router, prefix=f"{settings.api_prefix}/admin")
    app.include_router(admin_imports_router, prefix=f"{settings.api_prefix}/admin")
    app.include_router(admin_leadership_templates_router, prefix=f"{settings.api_prefix}/admin")
    app.include_router(admin_sessions_router, prefix=f"{settings.api_prefix}/admin")
    app.include_router(admin_signatories_router, prefix=f"{settings.api_prefix}/admin")
    app.include_router(admin_students_router, prefix=f"{settings.api_prefix}/admin")
    app.include_router(admin_templates_router, prefix=f"{settings.api_prefix}/admin")
    return app


app = create_app()
