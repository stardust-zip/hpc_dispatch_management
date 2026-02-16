import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_db_and_tables
from .routers import dispatches
from .settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events.
    Handles DB creation and shared HTTP client.
    """

    # Dynamically read the log level from settings and convert to logging integer
    numeric_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure logging ONLY when the app start using dynamic level
    logging.basicConfig(
        level=numeric_level, format="%(levelname)s: %(name)s - %(message)s"
    )

    # Startup
    logger.info("Application starting up...")
    if settings.MOCK_AUTH_ENABLED:
        logger.warning("!!! MOCK AUTHENTICATION IS ENABLED !!!")
    else:
        logger.info(f"Connecting to User Service at: {settings.HPC_USER_SERVICE_URL}")

    # Call your original DB creation function
    if settings.APP_ENV == "local":
        logger.info("Using local development, creating tables now!")
        create_db_and_tables()
    elif settings.APP_ENV == "production":
        logger.info("Skipped local development settings")

    client = httpx.AsyncClient()
    logger.info("Startup complete.")

    yield {"http_client": client}

    # Shutdown
    logger.info("Application shutting down...")
    await client.aclose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="HPC Dispatch Management Service",
    description="Handles creation, tracking, and notification of official dispatches.",
    version="0.1.0",
    lifespan=lifespan,
)

# cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(dispatches.router)
# app.include_router(folders.router)


@app.get("/debug-settings", tags=["Health Check"])
async def debug_settings():
    """
    Temporary endpoint to verify environment variables are loaded.
    Check the container logs after calling this.
    """
    if settings.APP_ENV == "local":
        mock_authentication_enabled = True if settings.MOCK_AUTH_ENABLED else False
        return {
            "MOCK_AUTHENTICATION": mock_authentication_enabled,
            "APP_ENV": f"{settings.APP_ENV}",
            "LOG_LEVEL": f"{settings.LOG_LEVEL}",
            "JWT_SECRET": f"{settings.JWT_SECRET}",
            "JWT_ALGO": f"{settings.JWT_ALGO}",
            "HPC_USER_SERVICE_URL": f"{settings.HPC_USER_SERVICE_URL}",
            "HPC_DRIVE_SERVICE_URL": f"{settings.HPC_DRIVE_SERVICE_URL}",
            "NOTIFICATION_SERVICE_URL": f"{settings.NOTIFICATION_SERVICE_URL}",
        }
    else:
        return {"message": "Debug enpoint disabled for safety."}


@app.get("/", tags=["Health Check"])
async def read_root():
    """
    Root endpoint for health check.
    """
    return {
        "status": "ok",
        "service": "HPC Dispatch Management",
    }


# uvicorn --app-dir src hpc_dispatch_management.main:app --host 0.0.0.0 --port 8888 --reload
