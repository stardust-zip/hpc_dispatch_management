import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import TypeAdapter

from hpc_dispatch_management.schemas import Dispatch, DispatchStatus, DispatchTypeSearch


@pytest.fixture(scope="function")
def sample_admin_dispatches(admin_auth_client: TestClient) -> list[Response]:
    test_dispatch_1 = admin_auth_client.post(
        "/dispatches/",
        json={
            "title": "Admin Report #1",
            "serial_number": "AR-001",
            "description": "Admin's First Report",
        },
    )

    test_dispatch_2 = admin_auth_client.post(
        "/dispatches/",
        json={
            "title": "Admin Report #2",
            "serial_number": "AR-002",
            "description": "Admin's Second Report",
        },
    )

    test_dispatch_3 = admin_auth_client.post(
        "/dispatches/",
        json={
            "title": "Admin Report #3",
            "serial_number": "AR-003",
            "description": "Admin's Third Report",
        },
    )

    return [test_dispatch_1, test_dispatch_2, test_dispatch_3]


@pytest.fixture(scope="function")
def sample_lecturer1_dispatches(lecturer1_auth_client: TestClient) -> list[Response]:
    test_dispatch_1 = lecturer1_auth_client.post(
        "/dispatches/",
        json={
            "title": "Lecturer1 Document #1",
            "serial_number": "LD-001",
            "description": "Lecturer1's First Document",
        },
    )

    test_dispatch_2 = lecturer1_auth_client.post(
        "/dispatches/",
        json={
            "title": "Lecturer1 Document #2",
            "serial_number": "LD-002",
            "description": "Lecturer1's Second Document",
        },
    )

    test_dispatch_3 = lecturer1_auth_client.post(
        "/dispatches/",
        json={
            "title": "Lecturer1 Document #3",
            "serial_number": "LD-003",
            "description": "Lecturer1's Third Document",
        },
    )

    return [test_dispatch_1, test_dispatch_2, test_dispatch_3]


def test_read_dispatches(
    lecturer1_auth_client: TestClient, sample_lecturer1_dispatches: list[Response]
):
    response = lecturer1_auth_client.get("/dispatches/")
    dispatches = TypeAdapter(list[Dispatch]).validate_python(response.json())

    assert response.status_code == 200
    assert len(dispatches) == 3

    assert response.json()[0]["title"] == sample_lecturer1_dispatches[0].json()["title"]
    assert (
        response.json()[1]["serial_number"]
        == sample_lecturer1_dispatches[1].json()["serial_number"]
    )


def test_filter_dispatches(
    lecturer1_auth_client: TestClient, sample_lecturer1_dispatches: list[Response]
):
    response = lecturer1_auth_client.get("/dispatches/", params={"search": "#1"})
    dispatches = TypeAdapter(list[Dispatch]).validate_python(response.json())

    assert response.status_code == 200
    assert response.json()[0]["title"] == sample_lecturer1_dispatches[0].json()["title"]
    assert len(dispatches) == 1

    response = lecturer1_auth_client.get("/dispatches/", params={"search": "#"})
    dispatches = TypeAdapter(list[Dispatch]).validate_python(response.json())
    assert response.status_code == 200
    assert response.json()[0]["title"] == sample_lecturer1_dispatches[0].json()["title"]
    assert len(dispatches) == 3

    response = lecturer1_auth_client.get(
        "/dispatches/", params={"dispatch_type": DispatchTypeSearch.INCOMING.value}
    )
    dispatches = TypeAdapter(list[Dispatch]).validate_python(response.json())
    assert response.status_code == 200
    assert len(dispatches) == 0

    response = lecturer1_auth_client.get(
        "/dispatches/", params={"status": DispatchStatus.DRAFT.value}
    )
    dispatches = TypeAdapter(list[Dispatch]).validate_python(response.json())
    assert response.status_code == 200
    assert len(dispatches) == 3


def test_read_dispatch(
    lecturer1_auth_client: TestClient, sample_lecturer1_dispatches: list[Response]
):
    dispatch = Dispatch.model_validate(sample_lecturer1_dispatches[0].json())
    response = lecturer1_auth_client.get(f"/dispatches/{dispatch.id}")

    assert response.status_code == 200
    assert response.json()["title"] == dispatch.title

    response = response = lecturer1_auth_client.get(f"/dispatches/{dispatch.id + 9999}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Dispatch not found"


def test_create_dispatch(lecturer1_auth_client: TestClient):
    response = lecturer1_auth_client.post(
        "/dispatches/",
        json={
            "title": "Test Dispatch",
            "serial_number": "T-001",
            "description": "My Test Dispatch",
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Test Dispatch"
    assert response.json()["status"] == DispatchStatus.DRAFT.value


def test_update_dispatch(
    lecturer1_auth_client: TestClient,
    sample_lecturer1_dispatches: list[Response],
):
    dispatch = Dispatch.model_validate(sample_lecturer1_dispatches[0].json())
    response = lecturer1_auth_client.put(
        f"/dispatches/{dispatch.id}", json={"title": "Updated Title"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == DispatchStatus.DRAFT.value

    response = lecturer1_auth_client.post(
        f"/dispatches/{dispatch.id}/assign",
        json={
            "assignee_usernames": ["lecturer2"],
            "action_required": "Please check this!",
        },
    )

    # assert response.status_code == 200

    response = lecturer1_auth_client.put(
        f"/dispatches/{dispatch.id}", json={"title": "New Update"}
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Only admins can edit a sent dispatch."


def test_update_dispatch_draft_without_permission(
    lecturer2_auth_client: TestClient,
    sample_lecturer1_dispatches: list[Response],
):
    dispatch = Dispatch.model_validate(sample_lecturer1_dispatches[0].json())
    response = lecturer2_auth_client.put(
        f"/dispatches/{dispatch.id}", json={"title": "Updated Title"}
    )

    assert response.status_code == 403


# WARNING: This currently not working, need to update later
