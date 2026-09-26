import os

from fastapi import APIRouter

router = APIRouter(tags=["readiness"])


@router.get("/health/ready")
async def readiness() -> dict[str, bool]:
    """A deliberately dependency-free probe for frontend warm-up."""
    return {"ready": True}


@router.get("/health/build")
async def build_revision() -> dict[str, str]:
    """Expose the deployed Render revision without exposing configuration secrets."""
    return {"revision": os.getenv("RENDER_GIT_COMMIT", "unknown")}
