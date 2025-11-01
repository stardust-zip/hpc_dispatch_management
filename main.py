import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from typing import Annotated
from . import schemas


app = FastAPI(
    title="HPC Dispatch Management Service",
    description="Hanldes creation, tracking, and notification of official dispatches.",
    version="0.1.0",
)


# Simple healthcheck endpoint to make sure
# our service is running.
@app.get("/", tags=["Health Check"])
async def read_root():
    """
    Root endpoint for health check.
    """
    return {"status": "ok", "service": "HPC Dispatch Management"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)
