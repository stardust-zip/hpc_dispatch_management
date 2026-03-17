import logging

import httpx
from fastapi import HTTPException, status

from ..core.settings import settings

logger = logging.getLogger(__name__)


def _get_auth_header(token: str):
    """Creates the authorization header."""
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


async def get_lecturer(lecturer_id: int, token: str, client: httpx.AsyncClient) -> dict:
    """
    Fetches lecturer information from the System Management (User) Service.
    """
    # settings.HPC_USER_SERVICE_URL is a Pydantic HttpUrl, so we convert it to string
    base_url = str(settings.HPC_USER_SERVICE_URL).rstrip("/")
    url = f"{base_url}/lecturers/{lecturer_id}"

    headers = _get_auth_header(token)

    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lecturer {lecturer_id} not found in User Service",
            )
        logger.error(f"HTTP error fetching lecturer {lecturer_id}: {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail="Error fetching lecturer data from User Service",
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_lecturer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while communicating with User Service",
        )
