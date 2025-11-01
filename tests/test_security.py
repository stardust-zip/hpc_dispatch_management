from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends
from typing import Annotated


# Import the dependency we want to test
from hpc_dispatch_management.security import get_current_user
from hpc_dispatch_management.schemas import User

# Create a minimal app to test the dependency
app = FastAPI()


@app.get("/test-security")
async def secure_endpoint(current_user: Annotated[User, Depends(get_current_user)]):
    """A test endpoint that uses our security dependency."""
    return {"user": current_user.username}


# Create the test client
client = TestClient(app)


def test_get_current_user_as_student():
    """
    TDD: Test that a user with 'student' type is FORBIDDEN (403).
    """
    response = client.get(
        "/test-security", headers={"Authorization": "Bearer mock_token_student"}
    )
    # We expect a 403 Forbidden error
    assert response.status_code == 403
    assert response.json() == {
        "detail": "Access denied. Only lecturers and admins can use this service."
    }


def test_get_current_user_as_lecturer():
    """
    TDD: Test that a 'lecturer' user is ALLOWED (200).
    """
    response = client.get(
        "/test-security", headers={"Authorization": "Bearer mock_token_lecturer"}
    )
    assert response.status_code == 200
    assert response.json() == {"user": "lecturer1"}


def test_get_current_user_as_admin():
    """
    TDD: Test that an 'admin' (who is also a lecturer) is ALLOWED (200).
    """
    response = client.get(
        "/test-security", headers={"Authorization": "Bearer mock_token_admin"}
    )
    assert response.status_code == 200
    assert response.json() == {"user": "admin1"}


def test_get_current_user_invalid_token():
    """
    TDD: Test that a bad or expired token is UNAUTHORIZED (401).
    """
    response = client.get(
        "/test-security", headers={"Authorization": "Bearer bad_token"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid authentication credentials"}


def test_get_current_user_no_token():
    """
    TDD: Test that a missing token is UNAUTHORIZED (401).
    (TestClient handles this, but FastAPI would return 401)
    """
    response = client.get("/test-security")
    # The dependency expects an auth header, so it fails
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
