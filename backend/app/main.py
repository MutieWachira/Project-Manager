"""SherlskyyCommand FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, health, projects
from app.core.config import settings
from app.services.database_status import DatabaseStatusMonitor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    monitor = DatabaseStatusMonitor()
    app.state.database_status_monitor = monitor
    await monitor.start()
    try:
        yield
    finally:
        await monitor.stop()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "A centralized project management and administration "
        "platform for software applications."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Restrict browser access to the configured frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL.rstrip("/")],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
    ],
    max_age=600,
)

app.include_router(
    health.router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    auth.router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    projects.router,
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
