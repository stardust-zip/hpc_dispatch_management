import pytest
from fastapi.testclient import TestClient

# We can reuse the setup from the other test file
from .test_dispatches import app, db_session

from hpc_dispatch_management import crud, schemas

client = TestClient(app)

# --- Define User IDs and Tokens for Clarity ---
AUTHOR_ID = 1
ASSIGNEE_ID = 2
UNRELATED_ID = 3

AUTHOR_TOKEN = "mock_token_lecturer"  # Corresponds to User ID 1
ASSIGNEE_TOKEN = "mock_token_admin"  # Corresponds to User ID 2


@pytest.fixture(scope="function")
def setup_test_data(db_session):
    """
    A fixture to create a predictable set of users and dispatches for search tests.
    """
    # 1. Create Users
    user_a = crud.sync_user_from_jwt(
        db_session,
        schemas.User(
            sub=AUTHOR_ID,
            user_type="lecturer",
            username="author",
            is_admin=False,
            email="a@test.com",
            full_name="Author User",
            department_id=1,
        ),
    )
    user_b = crud.sync_user_from_jwt(
        db_session,
        schemas.User(
            sub=ASSIGNEE_ID,
            user_type="lecturer",
            username="assignee",
            is_admin=True,
            email="b@test.com",
            full_name="Assignee User",
            department_id=1,
        ),
    )
    crud.sync_user_from_jwt(
        db_session,
        schemas.User(
            sub=UNRELATED_ID,
            user_type="lecturer",
            username="unrelated",
            is_admin=False,
            email="c@test.com",
            full_name="Unrelated User",
            department_id=2,
        ),
    )

    # 2. Create Dispatches
    # Dispatch 1: Outgoing for User A, Incoming for User B, Status PENDING
    dispatch1 = crud.create_dispatch(
        db_session,
        schemas.DispatchCreate(
            title="Fiscal Year Report Q3", serial_number="FY-Q3", description="..."
        ),
        author_id=user_a.id,
    )
    crud.assign_dispatch_to_users(
        db_session,
        dispatch1,
        schemas.DispatchAssign(assignee_ids=[user_b.id], action_required="Review"),
    )  # This makes its status PENDING

    # Dispatch 2: Outgoing for User A, Status DRAFT
    dispatch2 = crud.create_dispatch(
        db_session,
        schemas.DispatchCreate(
            title="Holiday Schedule", serial_number="HR-HS", description="..."
        ),
        author_id=user_a.id,
    )

    # Dispatch 3: Incoming for User A, Status PENDING
    dispatch3 = crud.create_dispatch(
        db_session,
        schemas.DispatchCreate(
            title="Department Budget Proposal",
            serial_number="FIN-DBP",
            description="...",
        ),
        author_id=user_b.id,
    )  # Created by User B
    crud.assign_dispatch_to_users(
        db_session,
        dispatch3,
        schemas.DispatchAssign(assignee_ids=[user_a.id], action_required="Approve"),
    )

    # Return the created dispatches to use their IDs in tests if needed
    return {"d1": dispatch1, "d2": dispatch2, "d3": dispatch3}


def test_search_outgoing_dispatches(db_session, setup_test_data):
    """
    Test if `dispatch_type=outgoing` correctly returns only dispatches authored by the current user.
    """
    response = client.get(
        "/dispatches?dispatch_type=outgoing",
        headers={"Authorization": f"Bearer {AUTHOR_TOKEN}"},
    )
    assert response.status_code == 200
    data = response.json()

    # User A authored dispatch 1 and 2
    assert len(data) == 2
    dispatch_ids = {d["id"] for d in data}
    assert setup_test_data["d1"].id in dispatch_ids
    assert setup_test_data["d2"].id in dispatch_ids


def test_search_incoming_dispatches(db_session, setup_test_data):
    """
    Test if `dispatch_type=incoming` correctly returns only dispatches assigned to the current user.
    """
    response = client.get(
        "/dispatches?dispatch_type=incoming",
        headers={"Authorization": f"Bearer {AUTHOR_TOKEN}"},
    )
    assert response.status_code == 200
    data = response.json()

    # User A was assigned dispatch 3
    assert len(data) == 1
    assert data[0]["id"] == setup_test_data["d3"].id


def test_search_by_status(db_session, setup_test_data):
    """
    Test filtering by a specific status.
    """
    # Note: The status string must be URL-encoded. TestClient handles this.
    response = client.get(
        "/dispatches?status=Chờ xử lý",  # PENDING
        headers={"Authorization": f"Bearer {AUTHOR_TOKEN}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Dispatch 1 and 3 are PENDING for User A (one outgoing, one incoming)
    assert len(data) == 2
    dispatch_ids = {d["id"] for d in data}
    assert setup_test_data["d1"].id in dispatch_ids
    assert setup_test_data["d3"].id in dispatch_ids


def test_search_by_text_term(db_session, setup_test_data):
    """
    Test the free-text search filter.
    """
    response = client.get(
        "/dispatches?search=Report",  # Search is case-insensitive
        headers={"Authorization": f"Bearer {AUTHOR_TOKEN}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Only Dispatch 1 has "Report" in its title
    assert len(data) == 1
    assert data[0]["id"] == setup_test_data["d1"].id


def test_combined_filters_incoming_pending(db_session, setup_test_data):
    """
    Test combining multiple filters: incoming AND pending.
    This is a very common and important use case.
    """
    response = client.get(
        "/dispatches?dispatch_type=incoming&status=Chờ xử lý",
        headers={"Authorization": f"Bearer {AUTHOR_TOKEN}"},
    )
    assert response.status_code == 200
    data = response.json()

    # User A's only incoming dispatch (d3) is also PENDING.
    assert len(data) == 1
    assert data[0]["id"] == setup_test_data["d3"].id


def test_search_no_results(db_session, setup_test_data):
    """
    Test that a valid search with no matches returns an empty list, not an error.
    """
    response = client.get(
        "/dispatches?search=nonexistent",
        headers={"Authorization": f"Bearer {AUTHOR_TOKEN}"},
    )
    assert response.status_code == 200
    assert response.json() == []
