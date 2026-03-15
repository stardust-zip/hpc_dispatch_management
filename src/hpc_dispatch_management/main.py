import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_db_and_tables
from .routers import dispatches
from .settings import settings

# Initialize a logger instance for this specific file, naming it after the current module (__name__)
logger = logging.getLogger(__name__)

# It's better to have  logger per file
# For different configurations
# It will also evuate the current py file name


@asynccontextmanager
async def lifespan(_app: FastAPI):  # adding _ so basedpyright be silient
    """
    Manage application startup and shutdown events.
    Handles DB creation and shared HTTP client.
    """

    # The code before yield run when the app starts
    # The code after yield run when the app shuts down

    # Retrives the desired logging lovel defined from the environemnt variable
    # and converts it to standard integer level using loggin module.
    # Default to INFO if missing
    numeric_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure root logger with this
    # Set standard formatting string for all logs output
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

    # This is a shared asynchronous HTTP client that can be reused across the app
    client = httpx.AsyncClient()

    logger.info("Startup complete.")

    # Normally, in python, yield used to craete generator—function that return data one piece at a time
    # Though, in this context, it acts as a pause button that split the function
    yield {"http_client": client}

    # Shutdown
    # Once the server receive shutdown signal,
    # execution resume here
    logger.info("Application shutting down...")

    # Safely close the asynchrounous HTTP client to prevent resource leaks.
    await client.aclose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="HPC Dispatch Management Service",
    description="Quản lý công văn cho Hệ thống điện tử HPC.",
    version="0.1.0",
    lifespan=lifespan,
)

# cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.METHODS,
    allow_headers=settings.HEADERS,
)


app.include_router(dispatches.router)
# app.include_router(folders.router)


@app.get("/debug-settings", tags=["Health Check"])
async def debug_settings():
    """
    Temporary endpoint to verify environment variables are loaded.
    Check the container logs after calling this.
    This endpoint was DISBLAED FOR SECURITY REASON.
    """
    if settings.APP_ENV == "local":
        mock_authentication_enabled = True if settings.MOCK_AUTH_ENABLED else False
        return {"msg": "Nothing"}
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
