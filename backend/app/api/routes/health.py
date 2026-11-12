from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return{
        "status": "healthy",
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }