from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from jose import JWTError, jwt
from pydantic import ValidationError

import httpx
import logging
from .database import get_http_client

from .schemas import User, UserType
from .settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

logger = logging.getLogger(__name__)

MOCK_USERS = {
    "lecturer1": User(
        sub=1,
        full_name="Mock Lecturer 1",
        user_type="lecturer",
        is_admin=False,
        username="lecturer1",
        email="l1@mock.com",
        department_id=1,
    ),
    "admin": User(
        sub=2,
        full_name="Mock Admin",
        user_type="lecturer",
        is_admin=True,
        username="admin",
        email="admin@mock.com",
        department_id=1,
    ),
    "student1": User(
        sub=3,
        full_name="Mock Student 1",
        user_type="student",
        is_admin=False,
        username="student1",
        email="s1@mock.com",
        department_id=1,
        class_id=10,
    ),
}


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    client: httpx.AsyncClient = Depends(get_http_client),
) -> User:
    """
    Dependency to get the current user from a JWT token.
    Enforces the rule that ONLY Lecturers or Admins can access.

    This version calls the User Service /me endpoint to validate the token.
    """

    # --- MOCK LOGIC FOR TDD ---
    if settings.MOCK_AUTH_ENABLED:
        user = MOCK_USERS.get(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid mock user token. Valid are: {list(MOCK_USERS.keys())}",
            )

        # --- OUR CORE BUSINESS RULE ---
        if user.user_type == UserType.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only lecturers and admins can use this service.",
            )
        return user
    # --- END MOCK LOGIC ---

    # --- REAL LOGIC (API Call) ---
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(
            f"{settings.HPC_USER_SERVICE_URL}/me", headers=headers
        )

        if response.status_code == 200:
            user_data = response.json()

            # The User Service API doc shows data is nested under "data"
            if user_data and "data" in user_data and user_data["data"] is not None:
                # --- ADAPT THE USER SERVICE RESPONSE TO OUR SCHEMA ---
                # The /me endpoint response is different from the JWT payload.
                # We must adapt it to our internal 'User' schema.

                me_data = user_data["data"]
                account_data = me_data.get("account", {})
                info_data = me_data.get(
                    "lecturer_info", me_data.get("student_info", {})
                )

                # Get class_id (for students) or department_id (for lecturers)
                class_id = info_data.get("class", {}).get("id")
                department_id = info_data.get("unit", {}).get("id")

                adapted_data = {
                    "sub": me_data.get("id"),
                    "user_type": me_data.get("user_type"),
                    "username": account_data.get("username"),
                    "is_admin": account_data.get("is_admin", False),
                    "email": me_data.get("email"),
                    "full_name": me_data.get("full_name"),
                    "department_id": department_id,
                    "class_id": class_id,
                }

                user = User.model_validate(adapted_data)

                # --- OUR CORE BUSINESS RULE ---
                if user.user_type == UserType.STUDENT:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied. Only lecturers and admins can use this service.",
                    )
                return user

        # Handle other non-200 responses from user service
        logger.warning(
            f"User service validation failed with status {response.status_code}. Response: {response.text}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials with user service",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except httpx.RequestError as e:
        logger.error(f"Could not connect to user service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not connect to user service: {e}",
        )
    except ValidationError as e:
        logger.error(f"Failed to validate user data from /me endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user data received from user service",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # --- END REAL LOGIC ---
