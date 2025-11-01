from fastapi import FastAPI
from .routers import dispatches, folders

app = FastAPI(
    title="HPC Dispatch Management Service",
    description="Handles creation, tracking, and notification of official dispatches.",
    version="0.1.0",
)

app.include_router(dispatches.router)
app.include_router(folders.router)


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
