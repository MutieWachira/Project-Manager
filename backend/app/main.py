"""SherlskyyCommand FastAPI application entry point."""

from fastapi import FastAPI

from app.api.routes import auth, health
from app.core.config import settings


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "A centralized project management and administration "
        "platform for software applications."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(
    health.router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    auth.router,
    prefix=settings.API_V1_PREFIX,
)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "message": "Welcome to SherlskyyCommand API",
        "documentation": "/docs",
    }
