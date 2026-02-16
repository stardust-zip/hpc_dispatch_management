import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from .schemas import User, UserType
from .settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

logger = logging.getLogger(__name__)

MOCK_USERS = {
    "lecturer1": User(
        sub=1,
        full_name="Mock Lecturer 1",
        user_type=UserType.LECTURER,
        is_admin=False,
        username="lecturer1",
        email="l1@mock.com",
        department_id=1,
    ),
    "admin": User(
        sub=2,
        full_name="Mock Admin",
        user_type=UserType.LECTURER,
        is_admin=True,
        username="admin",
        email="admin@mock.com",
        department_id=1,
    ),
    "student1": User(
        sub=3,
        full_name="Mock Student 1",
        user_type=UserType.STUDENT,
        is_admin=False,
        username="student1",
        email="s1@mock.com",
        department_id=1,
        class_id=10,
    ),
}


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    """
    Dependency to get the current user from a JWT token.
    Enforces the rule that ONLY Lecturers or Admins can access.

    This version calls the User Service /me endpoint to validate the token.
    """

    if settings.MOCK_AUTH_ENABLED:
        user = MOCK_USERS.get(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid mock user token. Valid are: {list(MOCK_USERS.keys())}",
            )

        if user.user_type == UserType.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only lecturers and admins can use this service.",
            )
        return user

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGO])

        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credential: ID invalid",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = User.model_validate(payload)

        if user.user_type == UserType.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied"
            )

        return user

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: JWT Error",
            headers={"WWW-Authenticate": "Bearer"},
        )
