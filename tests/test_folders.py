import pytest
from fastapi.testclient import TestClient

from .test_dispatches import app, db_session, LECTURER_TOKEN

client = TestClient(app)


def test_create_folder(db_session):
    response = client.post(
        "/folders/",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
        json={"name": "My First Folder"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My First Folder"
    assert data["owner_id"] == 1  # Lecturer's user ID


def test_add_dispatch_to_folder(db_session):
    # 1. Create a folder
    folder_res = client.post(
        "/folders/",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
        json={"name": "Project X"},
    )
    folder_id = folder_res.json()["id"]

    # 2. Create a dispatch
    dispatch_res = client.post(
        "/dispatches/",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
        json={
            "title": "Project X Document",
            "serial_number": "PXD-001",
            "description": "Details",
        },
    )
    dispatch_id = dispatch_res.json()["id"]

    # 3. Add the dispatch to the folder
    add_res = client.post(
        f"/folders/{folder_id}/dispatches/{dispatch_id}",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
    )
    assert add_res.status_code == 200
    folder_data = add_res.json()
    assert len(folder_data["dispatches"]) == 1
    assert folder_data["dispatches"][0]["id"] == dispatch_id


def test_remove_dispatch_from_folder(db_session):
    # Setup: Create folder and dispatch, then add it
    folder_res = client.post(
        "/folders/",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
        json={"name": "Project Y"},
    )
    folder_id = folder_res.json()["id"]
    dispatch_res = client.post(
        "/dispatches/",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
        json={
            "title": "Project Y Doc",
            "serial_number": "PYD-001",
            "description": "...",
        },
    )
    dispatch_id = dispatch_res.json()["id"]
    client.post(
        f"/folders/{folder_id}/dispatches/{dispatch_id}",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
    )

    # Action: Remove the dispatch
    remove_res = client.delete(
        f"/folders/{folder_id}/dispatches/{dispatch_id}",
        headers={"Authorization": f"Bearer {LECTURER_TOKEN}"},
    )
    assert remove_res.status_code == 204

    # Verification: Get the folder again and check it's empty
    get_res = client.get(
        f"/folders/{folder_id}", headers={"Authorization": f"Bearer {LECTURER_TOKEN}"}
    )
    # NOTE: To get a single folder, we need an endpoint. Let's assume we add one.
    # For now, we can check the list of all folders.
    list_res = client.get(
        "/folders/", headers={"Authorization": f"Bearer {LECTURER_TOKEN}"}
    )
    folder_data = next(f for f in list_res.json() if f["id"] == folder_id)
    assert len(folder_data["dispatches"]) == 0
