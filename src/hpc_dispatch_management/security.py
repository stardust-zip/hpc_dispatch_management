from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
import jwt # PyJWT or python-jose, let's plan for python-jose
from pydantic import ValidationError

from .schemas import User, UserType

# This tells FastAPI to look for an "Authorization: Bearer <token>" header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # We don't have a token URL, but this is needed

# We will need these later when we decode real tokens
# We should get these from environment variables!
# ALGORITHM = "HS256"
# JWT_SECRET_KEY = "your-user-service-secret-key" 

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """
    Dependency to get the current user from a JWT token.
    Enforces the rule that ONLY Lecturers or Admins can access.
    
    In a real app, we would decode and verify the token.
    For now, we'll use a placeholder/mock logic to enable TDD.
    """
    
    # --- MOCK LOGIC FOR TDD ---
    # In our test, we'll pass special "mock" tokens.
    # In a real app, this block would be replaced by jwt.decode()
    if token == "mock_token_lecturer":
        user_data = {
            "sub": 1, "user_type": "lecturer", "username": "lecturer1",
            "is_admin": False, "email": "lecturer1@system.com",
            "full_name": "Lecturer 1", "department_id": 1
        }
    elif token == "mock_token_admin":
        user_data = {
            "sub": 2, "user_type": "lecturer", "username": "admin1",
            "is_admin": True, "email": "admin1@system.com",
            "full_name": "Admin User", "department_id": 1
        }
    elif token == "mock_token_student":
        user_data = {
            "sub": 3, "user_type": "student", "username": "student1",
            "is_admin": False, "email": "student1@system.com",
            "full_name": "Student 1", "department_id": 1, "class_id": 101
        }
    else:
        # This simulates a real JWT decode error
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # --- END MOCK LOGIC ---

    # --- REAL LOGIC (commented out for now) ---
    # try:
    #     payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
    #     user_data = payload
    # except (jwt.PyJWTError, ValidationError):
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid authentication credentials",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    # --- END REAL LOGIC ---

    try:
        user = User.model_validate(user_data) # Use model_validate in Pydantic v2
    except ValidationError:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user data in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --- OUR CORE BUSINESS RULE ---
    # Only lecturers or admins can access this service.
    if user.user_type == UserType.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only lecturers and admins can use this service."
        )

    return user
