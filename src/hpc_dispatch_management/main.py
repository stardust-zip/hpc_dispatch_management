import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_db_and_tables
from .routers import dispatches, folders
from .settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events.
    Handles DB creation and shared HTTP client.
    """
    # Configure logging ONLY when the app start
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s: %(name)s - %(message)s"
    )

    # Startup
    logger.info("Application starting up...")
    if settings.MOCK_AUTH_ENABLED:
        logger.warning("!!! MOCK AUTHENTICATION IS ENABLED !!!")
    else:
        logger.info(f"Connecting to User Service at: {settings.HPC_USER_SERVICE_URL}")

    # Call your original DB creation function
    create_db_and_tables()

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
app.include_router(folders.router)


@app.get("/debug-settings", tags=["Health Check"])
async def debug_settings():
    """
    Temporary endpoint to verify environment variables are loaded.
    Check the container logs after calling this.
    """
    # This will print to your docker compose logs, NOT to the user.
    # This is a safe way to debug.
    print("--- DEBUG SETTINGS CHECK ---")
    print(f"RUNNING WITH SECRET: '{settings.JWT_SECRET}'")
    print(f"RUNNING WITH ALGO:   '{settings.JWT_ALGO}'")
    print(f"USER SERVICE URL:  '{settings.HPC_USER_SERVICE_URL}'")
    print(f"MOCK AUTH ENABLED: '{settings.MOCK_AUTH_ENABLED}'")
    print("----------------------------")
    return {
        "message": "Settings have been printed to container logs. Please check them.",
        "loaded_algo": settings.JWT_ALGO,
    }


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
