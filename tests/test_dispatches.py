from fastapi.testclient import TestClient


def create_dispatches_for_tests(auth_client: TestClient):
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

    test_dispatches = [test_dispatch_1, test_dispatch_2, test_dispatch_3]

    return test_dispatches


def test_get_all_dispatch(auth_client: TestClient):
    _ = create_dispatches_for_tests(auth_client)

    response = auth_client.get("/dispatches/")

    assert response.status_code == 200
    assert response.json()[0]["title"] == "Test Dispatch #1"
    assert response.json()[1]["title"] == "Test Dispatch #2"


def test_get_individual_dispatch(auth_client: TestClient):
    dispatches = create_dispatches_for_tests(auth_client)

    dispatch_id: int = dispatches[0].json()["id"]

    response = auth_client.get(f"/dispatches/{dispatch_id}")

    assert response.status_code == 200
    assert response.json()["title"] == "Test Dispatch #1"


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


def test_update_dispatch_title(auth_client: TestClient):
    dispatches = create_dispatches_for_tests(auth_client)

    dispatch_id = dispatches[0].json()["id"]

    response = auth_client.put(
        f"/dispatches/{dispatch_id}",
        json={"title": "Updated Title"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_delete_dispatch(auth_client: TestClient):
    dispatches = create_dispatches_for_tests(auth_client)

    dispatch_id = dispatches[0].json()["id"]
    response = auth_client.delete(f"/dispatches/{dispatch_id}")

    assert response.status_code == 204
