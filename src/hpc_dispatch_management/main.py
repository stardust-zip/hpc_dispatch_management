import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from typing import Annotated

app = FastAPI(
    title="HPC Dispatch Management Service",
    description="Handles creation, tracking, and notification of official dispatches.",
    version="0.1.0",
)

@app.get("/", tags=["Health Check"])
async def read_root():
    """
    Root endpoint for health check.
    """
    return {"status": "ok", "service": "HPC Dispatch Management"}



# Uvicorn runner for local development
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)

