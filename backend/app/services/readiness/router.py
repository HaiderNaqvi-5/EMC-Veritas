import os

import pymupdf
from fastapi import APIRouter

router = APIRouter(tags=["readiness"])


@router.get("/health/ready")
async def readiness() -> dict[str, bool]:
    """A deliberately dependency-free probe for frontend warm-up."""
    return {"ready": True}


@router.get("/health/info")
async def runtime_info() -> dict[str, str]:
    """Expose non-secret build details so deployment/runtime mismatches are diagnosable."""
    return {
        "commit": os.getenv("RENDER_GIT_COMMIT", os.getenv("GIT_COMMIT", "development")),
        "pymupdf": pymupdf.VersionBind,
        "font_validator": "fonttools",
    }
