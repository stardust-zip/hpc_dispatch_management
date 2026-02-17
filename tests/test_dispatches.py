import pytest
from fastapi.testclient import TestClient
from httpx import Response

from hpc_dispatch_management.schemas import Dispatch


@pytest.fixture(scope="function")
def sample_dispatches(auth_client: TestClient) -> list[Response]:
    test_dispatch_1 = auth_client.post(
        "/dispatches/",
        json={
            "title": "Test Dispatch #1",
            "serial_number": "TEST-001",
            "description": "My First Test Dispatch",
        },
    )

    test_dispatch_2 = auth_client.post(
        "/dispatches/",
        json={
            "title": "Test Dispatch #2",
            "serial_number": "TEST-002",
            "description": "My Second Test Dispatch",
        },
    )

    test_dispatch_3 = auth_client.post(
        "/dispatches/",
        json={
            "title": "Test Dispatch #3",
            "serial_number": "TEST-003",
            "description": "My Third Test Dispatch",
        },
    )

    return [test_dispatch_1, test_dispatch_2, test_dispatch_3]


def test_get_all_dispatch(auth_client: TestClient, sample_dispatches: list[Response]):
    response = auth_client.get("/dispatches/")

    assert response.status_code == 200
    assert response.json()[0]["title"] == sample_dispatches[0].json()["title"]
    assert response.json()[1]["title"] == sample_dispatches[1].json()["title"]


def test_get_individual_dispatch(
    auth_client: TestClient, sample_dispatches: list[Response]
):
    dispatch = Dispatch.model_validate(sample_dispatches[0].json())
    dispatch_id = dispatch.id

    response = auth_client.get(f"/dispatches/{dispatch_id}")

    assert response.status_code == 200
    assert response.json()["title"] == dispatch.title


def test_create_dispatch(auth_client: TestClient):
    response = auth_client.post(
        "/dispatches/",
        json={
            "title": "Test Dispatch Create",
            "serial_number": "FIRST-001",
            "description": "My first test dispatch",
            "file_url": "http://test-file-url.md",
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Test Dispatch Create"


def test_create_dispatch_failed(auth_client: TestClient):
    response = auth_client.post(
        "/dispatches/",
        json={
            "serial_number": "FIRST-001",
            "description": "My first test dispatch",
        },
    )

    assert response.status_code == 422


def test_update_dispatch_title(
    auth_client: TestClient, sample_dispatches: list[Response]
):
    dispatch = Dispatch.model_validate(sample_dispatches[0].json())

    response = auth_client.put(
        f"/dispatches/{dispatch.id}",
        json={"title": "Updated Title"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"
    assert response.json()["serial_number"] == "TEST-001"


def test_delete_dispatch(auth_client: TestClient, sample_dispatches: list[Response]):
    dispatch_id = Dispatch.model_validate(sample_dispatches[0].json()).id
    response = auth_client.delete(f"/dispatches/{dispatch_id}")

    assert response.status_code == 204
