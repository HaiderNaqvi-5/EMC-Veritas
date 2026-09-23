from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.public.router import router as public_router
from app.core.settings import settings
from app.services.readiness.router import router as readiness_router


def create_app() -> FastAPI:
    app = FastAPI(title="EMC Veritas API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(readiness_router, prefix=settings.api_prefix)
    app.include_router(public_router, prefix=settings.api_prefix)
    return app


app = create_app()
