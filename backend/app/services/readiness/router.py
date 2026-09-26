import os

from fastapi import APIRouter

from app.services.documents import rendering

router = APIRouter(tags=["readiness"])


@router.get("/health/ready")
async def readiness() -> dict[str, bool]:
    """A deliberately dependency-free probe for frontend warm-up."""
    return {"ready": True}


@router.get("/health/build")
async def build_revision() -> dict[str, str]:
    """Expose the deployed revision and active paragraph strategy without secrets."""
    constants = rendering._inline_activity_paragraph.__code__.co_consts
    paragraph_mode = (
        "independent"
        if any(isinstance(value, str) and "Their leadership, coordination" in value for value in constants)
        else "legacy"
    )
    return {
        "revision": os.getenv("RENDER_GIT_COMMIT", "unknown"),
        "paragraph_mode": paragraph_mode,
    }
