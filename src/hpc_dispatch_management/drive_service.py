import logging
import uuid

import httpx

from . import models
from .schemas import DispatchStatus
from .settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FOLDER_OUTGOING = "Công văn đi"
FOLDER_DRAFT = "Công văn nháp"
# Note: "Công văn đến" must be handled by the recipient's client,
# as the sender cannot write to the recipient's drive.


def _get_auth_header(token: str):
    """Creates the authorization header."""
    return {"Authorization": f"Bearer {token}"}


def _extract_item_id_from_url(file_url: str | None) -> str | None:
    """
    Extracts the UUID item_id from a drive URL.
    e.g., 'http://localhost:7777/api/v1/drive/items/abc-123' -> 'abc-123'
    """
    if not file_url:
        return None
    try:
        # Strip trailing slashes just in case, then split
        item_id_str = file_url.rstrip("/").split("/")[-1]
        return str(uuid.UUID(item_id_str))
    except (ValueError, IndexError):
        logger.warning(f"Could not parse item_id from URL: {file_url}")
        return None


async def _get_or_create_folder(
    folder_name: str, token: str, client: httpx.AsyncClient
) -> str | None:
    """
    Finds a folder in the user's root. If it doesn't exist, create it.
    Returns the folder's item_id.
    """
    headers = _get_auth_header(token)
    drive_url = settings.HPC_DRIVE_SERVICE_URL

    try:
        # 1. Check if folder exists in root
        response = await client.get(f"{drive_url}/items", headers=headers)
        response.raise_for_status()

        root_items = response.json().get("items", [])
        existing_folder = next(
            (
                item
                for item in root_items
                if item["name"] == folder_name and item["item_type"] == "FOLDER"
            ),
            None,
        )

        if existing_folder:
            return existing_folder["item_id"]

        # 2. Not found, so create it
        logger.info(f"Folder '{folder_name}' not found. Creating it...")
        create_payload = {
            "name": folder_name,
            "item_type": "FOLDER",
            "parent_id": None,
        }
        response = await client.post(
            f"{drive_url}/items", headers=headers, json=create_payload
        )
        response.raise_for_status()
        return response.json()["item_id"]

    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error while getting/creating folder '{folder_name}': {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Error in _get_or_create_folder: {e}")

    return None


async def _move_item_to_folder(
    item_id: str, folder_id: str, token: str, client: httpx.AsyncClient
):
    """Moves a drive item into a specific parent folder."""
    headers = _get_auth_header(token)
    drive_url = settings.HPC_DRIVE_SERVICE_URL
    update_payload = {"parent_id": folder_id}

    try:
        # HPC Drive uses PATCH for updates
        response = await client.patch(
            f"{drive_url}/items/{item_id}", headers=headers, json=update_payload
        )
        response.raise_for_status()
        logger.info(f"Successfully moved item {item_id} to folder {folder_id}")
    except httpx.HTTPStatusError as e:
        # Ignore 409 Conflict if it's already in that folder
        if e.response.status_code != 409:
            logger.error(f"HTTP error moving item {item_id}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error in _move_item_to_folder: {e}")


async def _share_item_with_user(
    item_id: str, username: str, token: str, client: httpx.AsyncClient
):
    """Shares a drive item with another user by their username."""
    headers = _get_auth_header(token)
    drive_url = settings.HPC_DRIVE_SERVICE_URL
    share_payload = {"username": username}

    try:
        response = await client.post(
            f"{drive_url}/items/{item_id}/share", headers=headers, json=share_payload
        )
        response.raise_for_status()
        logger.info(f"Successfully shared item {item_id} with user {username}")
    except httpx.HTTPStatusError as e:
        # Ignore 409 Conflict if it's already shared
        if e.response.status_code != 409:
            logger.error(
                f"HTTP error sharing item {item_id} with {username}: {e.response.text}"
            )
    except Exception as e:
        logger.error(f"Error in _share_item_with_user: {e}")


async def organize_dispatch_in_drive(
    dispatch: models.Dispatch,
    assignees: list[models.User],
    token: str,
    client: httpx.AsyncClient,
):
    """
    Main service function to organize a dispatch in the drive.
    1. Moves the sender's file to "Công văn đi" OR "Công văn nháp" based on status.
    2. Shares the file with all assignees (if not a draft).
    """
    item_id = _extract_item_id_from_url(dispatch.file_url)
    if not item_id:
        logger.error(
            f"Dispatch {dispatch.id} has no valid file_url. Skipping drive logic."
        )
        return

    # --- 1. Sender's Action: Move to appropriate folder ---
    # Determine the target folder based on the dispatch status
    target_folder = (
        FOLDER_DRAFT if dispatch.status == DispatchStatus.DRAFT else FOLDER_OUTGOING
    )

    folder_id = await _get_or_create_folder(target_folder, token, client)
    if folder_id:
        await _move_item_to_folder(item_id, folder_id, token, client)

    # --- 2. Recipient's Action: Share with assignees ---
    # We only share the document if it's an actual sent dispatch (not a draft)
    if dispatch.status != DispatchStatus.DRAFT:
        for assignee in assignees:
            if assignee.id == dispatch.author_id:
                continue  # Don't share with yourself

            await _share_item_with_user(item_id, assignee.username, token, client)
