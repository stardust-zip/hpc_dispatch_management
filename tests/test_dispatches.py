import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


from hpc_dispatch_management.main import app
from hpc_dispatch_management.database import Base, get_db
from hpc_dispatch_management import crud, schemas

# --- Test Database Setup ---
# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency override to use the test database
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Apply the override to our app
app.dependency_overrides[get_db] = override_get_db


# Fixture to create a fresh database for each test function
@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)

# --- MOCK TOKENS ---
LECTURER_TOKEN = "mock_token_lecturer"  # User ID: 1, is_admin: False
ADMIN_TOKEN = "mock_token_admin"  # User ID: 2, is_admin: True

# --- TESTS ---


def test_create_dispatch(db_session):
    response = client.post(
        "/dispatches/",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
        json={
            "title": "Test Dispatch",
            "serial_number": "TD-001",
            "description": "This is a test.",
            "file_url": "http://example.com/file.pdf",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Dispatch"
    assert data["author_id"] == 1  # Lecturer's ID is 1
    assert data["status"] == "Nháp"  # Should be DRAFT


def test_read_dispatch(db_session):
    # First, create a dispatch to read
    lecturer_user = schemas.User.model_validate(
        {
            "sub": 1,
            "user_type": "lecturer",
            "username": "l1",
            "is_admin": False,
            "email": "l@1.com",
            "full_name": "l1",
            "department_id": 1,
        }
    )
    crud.sync_user_from_jwt(db_session, lecturer_user)
    dispatch_data = schemas.DispatchCreate(
        title="Read Test", serial_number="RT-001", description="desc"
    )
    created_dispatch = crud.create_dispatch(db_session, dispatch_data, author_id=1)

    response = client.get(
        f"/dispatches/{created_dispatch.id}",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Read Test"


def test_update_draft_by_owner(db_session):
    # Create a draft dispatch as lecturer (user 1)
    response = client.post(
        "/dispatches/",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
        json={
            "title": "Draft to Edit",
            "serial_number": "DTE-001",
            "description": "desc",
        },
    )
    dispatch_id = response.json()["id"]

    # Update it as the same lecturer
    update_response = client.put(
        f"/dispatches/{dispatch_id}",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
        json={"title": "Updated Draft Title"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Draft Title"


def test_fail_update_draft_by_non_owner(db_session):
    # Create a draft dispatch as lecturer (user 1)
    response = client.post(
        "/dispatches/",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
        json={
            "title": "Another Draft",
            "serial_number": "AD-001",
            "description": "desc",
        },
    )
    dispatch_id = response.json()["id"]

    # Try to update it as admin (user 2)
    update_response = client.put(
        f"/dispatches/{dispatch_id}",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        json={"title": "Illegal Update"},
    )
    assert update_response.status_code == 403
    assert "not have permission to edit this draft" in update_response.json()["detail"]


def test_update_sent_dispatch_by_admin(db_session):
    # Create a dispatch as lecturer
    lecturer_user = schemas.User.model_validate(
        {
            "sub": 1,
            "user_type": "lecturer",
            "username": "l1",
            "is_admin": False,
            "email": "l@1.com",
            "full_name": "l1",
            "department_id": 1,
        }
    )
    crud.sync_user_from_jwt(db_session, lecturer_user)
    dispatch_data = schemas.DispatchCreate(
        title="Sent Dispatch", serial_number="SD-001", description="desc"
    )
    db_dispatch = crud.create_dispatch(db_session, dispatch_data, author_id=1)

    # Manually update its status to 'PENDING' to simulate it being sent
    db_dispatch.status = schemas.DispatchStatus.PENDING
    db_session.commit()

    # Admin updates the sent dispatch
    update_response = client.put(
        f"/dispatches/{db_dispatch.id}",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        json={"description": "Admin was here."},
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Admin was here."


def test_fail_update_sent_dispatch_by_owner(db_session):
    # Create a dispatch as lecturer
    lecturer_user = schemas.User.model_validate(
        {
            "sub": 1,
            "user_type": "lecturer",
            "username": "l1",
            "is_admin": False,
            "email": "l@1.com",
            "full_name": "l1",
            "department_id": 1,
        }
    )
    crud.sync_user_from_jwt(db_session, lecturer_user)
    dispatch_data = schemas.DispatchCreate(
        title="Another Sent", serial_number="AS-001", description="desc"
    )
    db_dispatch = crud.create_dispatch(db_session, dispatch_data, author_id=1)
    db_dispatch.status = schemas.DispatchStatus.PENDING
    db_session.commit()

    # Owner (not admin) tries to update it
    update_response = client.put(
        f"/dispatches/{db_dispatch.id}",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
        json={"title": "I want to change this!"},
    )
    assert update_response.status_code == 403
    assert "Only admins can edit a sent dispatch" in update_response.json()["detail"]


def test_delete_draft_by_owner(db_session):
    response = client.post(
        "/dispatches/",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
        json={
            "title": "To Be Deleted",
            "serial_number": "TBD-001",
            "description": "desc",
        },
    )
    dispatch_id = response.json()["id"]

    delete_response = client.delete(
        f"/dispatches/{dispatch_id}",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
    )
    assert delete_response.status_code == 204

    # Verify it's gone
    get_response = client.get(
        f"/dispatches/{dispatch_id}",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
    )
    assert get_response.status_code == 404


def test_assign_dispatch_and_send_notification(db_session, mocker):
    # Mock the notification service function
    mock_send_noti = mocker.patch(
        "hpc_dispatch_management.services.send_new_dispatch_notification"
    )

    # Create a dispatch as the lecturer (user 1)
    response = client.post(
        "/dispatches/",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
        json={
            "title": "Dispatch to Assign",
            "serial_number": "DTA-001",
            "description": "desc",
        },
    )
    dispatch_id = response.json()["id"]

    # The admin (user 2) will be the assignee. We need to sync them to the test DB first.
    admin_user_data = schemas.User(
        sub=2,
        user_type="lecturer",
        username="admin1",
        is_admin=True,
        email="admin1@s.com",
        full_name="Admin User",
        department_id=1,
    )
    crud.sync_user_from_jwt(db_session, admin_user_data)

    # Now, assign the dispatch
    assign_response = client.post(
        f"/dispatches/{dispatch_id}/assign",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
        json={"assignee_ids": [2], "action_required": "Please review."},
    )

    assert assign_response.status_code == 200
    assert "notifications sent" in assign_response.json()["message"]

    # Verify that our mocked notification function was called exactly once
    mock_send_noti.assert_called_once()
    # You can even inspect the arguments it was called with
    call_args = mock_send_noti.call_args[1]
    assert call_args["assignee"].id == 2
    assert call_args["assigner"].id == 1
