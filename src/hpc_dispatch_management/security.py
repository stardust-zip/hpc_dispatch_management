from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from .schemas import User, UserType
from .settings import settings

# Tells FastAPI to look for an Authorization header in incoming HTTP requests,
# specifically expecting the format Bearer <token>
# Since I don't have /token endpoint becuase System-Management handles login
# , the Authorize button in /docs Swagger UI will fail with a 404 error when
# dev try to login
# By that, we point tokenUrl directly to System-Management's login endpoint.
# Ack, wait, i'm not changning SysMa code.
# just get the jwt from curl and paste it when authorize
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    """
    Dependency to get the current user from a JWT token.
    Enforces the rule that ONLY Lecturers or Admins can access.
    """

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGO],
            options={
                "verify_aud": False,
                "verify_iss": False,
                "verify_sub": False,
            },
        )

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
