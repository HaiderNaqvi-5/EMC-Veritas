from fastapi import APIRouter

router = APIRouter(tags=["readiness"])


@router.get("/health/ready")
async def readiness() -> dict[str, bool]:
    """A deliberately dependency-free probe for frontend warm-up."""
    return {"ready": True}
