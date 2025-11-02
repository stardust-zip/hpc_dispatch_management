from fastapi import FastAPI
from .routers import dispatches, folders
from fastapi.middleware.cors import CORSMiddleware
from .settings import settings

app = FastAPI(
    title="HPC Dispatch Management Service",
    description="Handles creation, tracking, and notification of official dispatches.",
    version="0.1.0",
)

# cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    print("----------------------------")
    return {
        "message": "Settings have been printed to container logs. Please check them.",
        "loaded_algo": settings.JWT_ALGO,
    }


@app.get("/", tags=["Health Check"])
async def read_root():
    """
    Root endpoint for health check.
    Even if your health already sucked 😔.
    """
    return {
        "status": "ok",
        "service": "HPC Dispatch Management",
        "mind": "controlled",
        "life": "failed",
        "solulu": "delulu",
        "faith": False,
    }


# uvicorn --app-dir src hpc_dispatch_management.main:app --host 0.0.0.0 --port 8888 --reload
