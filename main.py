from fastapi import FastAPI, Depends, HTTPException, status
from contextlib import asynccontextmanager
from hpc_dispatch_management.database import (
    create_db_and_tables,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Async context manager for FastAPI lifespan events.
    This replaces the old @app.on_event("startup") decorator.
    """
    print("Service starting up...")
    # Create database tables on startup
    create_db_and_tables()
    yield
    # Code here would run on shutdown
    print("Service shutting down...")


app = FastAPI(
    title="HPC Dispatch Management Service",
    description="Handles creation, tracking, and notification of official dispatches.",
    version="0.1.0",
    lifespan=lifespan,  # Register the lifespan event handler
)


# Simple healthcheck endpoint
@app.get("/", tags=["Health Check"])
async def read_root():
    """
    Root endpoint for health check.
    """
    return {"status": "ok", "service": "HPC Dispatch Management"}


if __name__ == "__main__":
    import uvicorn

    print("Starting Uvicorn server...")
    uvicorn.run(
        "hpc_dispatch_management.main:app",
        host="0.0.0.0",
        port=8888,
        reload=True,
        # Set the app_dir to the 'src' directory
        # to ensure correct module loading
        app_dir="src",
    )
