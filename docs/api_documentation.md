# HPC Dispatch Management API Documentation

This document provides a detailed explanation of the HPC Dispatch Management API endpoints for frontend integration.

## Base URL

The base URL for all API endpoints is `http://localhost:8888`.

## Authentication

All endpoints require a valid JSON Web Token (JWT) to be included in the `Authorization` header of the request. The token should be prefixed with `Bearer `.

**Example:** `Authorization: Bearer <your_jwt_token>`

The user information is extracted from the JWT and used for authorization and to identify the current user.

## User Information

The user information is based on the user schema from the user microservice. Here is an example of the user object that is available in the backend after decoding the JWT:

```json
{
  "sub": 2,
  "user_type": "lecturer",
  "username": "lecturer1",
  "is_admin": false,
  "email": "lecturer1@system.com",
  "full_name": "Lecturer 1",
  "department_id": 1,
  "class_id": null
}
```

## Endpoints

### Dispatches

#### Create a new dispatch

- **Endpoint:** `POST /dispatches/`
- **Description:** Creates a new dispatch. The creator is automatically assigned as the author. New dispatches always start with 'DRAFT' status.
- **Request Body:**
  ```json
  {
    "title": "string",
    "content": "string",
    "serial_number": "string",
    "urgency": "NORMAL"
  }
  ```
- **Response:**
  - `201 Created`: Returns the created dispatch object.
  - `401 Unauthorized`: If the user is not authenticated.

#### Get a list of dispatches

- **Endpoint:** `GET /dispatches/`
- **Description:** Retrieves a list of dispatches with advanced filtering.
- **Query Parameters:**
  - `skip` (integer, optional, default: 0): Number of dispatches to skip.
  - `limit` (integer, optional, default: 100): Maximum number of dispatches to return.
  - `status` (string, optional): Filter by dispatch status (e.g., 'PENDING', 'DRAFT', 'APPROVED', 'REJECTED').
  - `dispatch_type` (string, optional, default: 'ALL'): Filter by user perspective ('incoming', 'outgoing', or 'all').
  - `search` (string, optional): Search term for title or serial number.
- **Response:**
  - `200 OK`: Returns a list of dispatch objects.
  - `401 Unauthorized`: If the user is not authenticated.

#### Get a single dispatch by ID

- **Endpoint:** `GET /dispatches/{dispatch_id}`
- **Description:** Retrieves a single dispatch by its ID.
- **Path Parameters:**
  - `dispatch_id` (integer, required): The ID of the dispatch to retrieve.
- **Response:**
  - `200 OK`: Returns the dispatch object.
  - `401 Unauthorized`: If the user is not authenticated.
  - `404 Not Found`: If the dispatch with the given ID does not exist.

#### Update a dispatch

- **Endpoint:** `PUT /dispatches/{dispatch_id}`
- **Description:** Updates a dispatch.
  - If the dispatch is in 'DRAFT' status, only the creator can edit it.
  - If the dispatch has been sent (not in 'DRAFT' status), only an admin can edit it.
- **Path Parameters:**
  - `dispatch_id` (integer, required): The ID of the dispatch to update.
- **Request Body:**
  ```json
  {
    "title": "string",
    "content": "string",
    "serial_number": "string",
    "urgency": "NORMAL"
  }
  ```
- **Response:**
  - `200 OK`: Returns the updated dispatch object.
  - `401 Unauthorized`: If the user is not authenticated.
  - `403 Forbidden`: If the user does not have permission to edit the dispatch.
  - `404 Not Found`: If the dispatch with the given ID does not exist.

#### Delete a dispatch

- **Endpoint:** `DELETE /dispatches/{dispatch_id}`
- **Description:** Deletes a dispatch.
  - If the dispatch is in 'DRAFT' status, only the creator can delete it.
  - If the dispatch has been sent (not in 'DRAFT' status), only an admin can delete it.
- **Path Parameters:**
  - `dispatch_id` (integer, required): The ID of the dispatch to delete.
- **Response:**
  - `204 No Content`: If the dispatch was deleted successfully.
  - `401 Unauthorized`: If the user is not authenticated.
  - `403 Forbidden`: If the user does not have permission to delete the dispatch.

#### Assign a dispatch to users

- **Endpoint:** `POST /dispatches/{dispatch_id}/assign`
- **Description:** Assigns a 'DRAFT' dispatch to users. This changes the status from 'DRAFT' to 'PENDING' and sends a notification to each assignee.
- **Path Parameters:**
  - `dispatch_id` (integer, required): The ID of the dispatch to assign.
- **Request Body:**
  ```json
  {
    "assignee_ids": [
      0
    ],
    "action_required": "string"
  }
  ```
- **Response:**
  - `200 OK`: Returns a success message.
  - `400 Bad Request`: If the dispatch is not in 'DRAFT' status or if there is an issue with the assignment.
  - `401 Unauthorized`: If the user is not authenticated.
  - `403 Forbidden`: If the user is not the author of the dispatch.
  - `404 Not Found`: If the dispatch with the given ID does not exist.

#### Update the status of a dispatch

- **Endpoint:** `PUT /dispatches/{dispatch_id}/status`
- **Description:** Updates the status of a dispatch (Approve/Reject). Only an assignee can perform this action. Sends a notification back to the original author.
- **Path Parameters:**
  - `dispatch_id` (integer, required): The ID of the dispatch to update.
- **Request Body:**
  ```json
  {
    "status": "APPROVED",
    "review_comment": "string"
  }
  ```
- **Response:**
  - `200 OK`: Returns the updated dispatch object.
  - `401 Unauthorized`: If the user is not authenticated.
  - `403 Forbidden`: If the user is not an assignee of the dispatch.
  - `404 Not Found`: If the dispatch with the given ID does not exist.

### Folders

#### Create a new folder

- **Endpoint:** `POST /folders/`
- **Description:** Creates a new folder for the current user.
- **Request Body:**
  ```json
  {
    "name": "string"
  }
  ```
- **Response:**
  - `201 Created`: Returns the created folder object.
  - `401 Unauthorized`: If the user is not authenticated.

#### Get a list of folders for the current user

- **Endpoint:** `GET /folders/`
- **Description:** Retrieves a list of folders for the current user.
- **Response:**
  - `200 OK`: Returns a list of folder objects.
  - `401 Unauthorized`: If the user is not authenticated.

#### Add a dispatch to a folder

- **Endpoint:** `POST /folders/{folder_id}/dispatches/{dispatch_id}`
- **Description:** Adds a dispatch to a folder. The user can only add dispatches they own.
- **Path Parameters:**
  - `folder_id` (integer, required): The ID of the folder.
  - `dispatch_id` (integer, required): The ID of the dispatch.
- **Response:**
  - `200 OK`: Returns the updated folder object.
  - `401 Unauthorized`: If the user is not authenticated.
  - `404 Not Found`: If the folder or dispatch does not exist, or if the user does not own the dispatch.

#### Remove a dispatch from a folder

- **Endpoint:** `DELETE /folders/{folder_id}/dispatches/{dispatch_id}`
- **Description:** Removes a dispatch from a folder.
- **Path Parameters:**
  - `folder_id` (integer, required): The ID of the folder.
  - `dispatch_id` (integer, required): The ID of the dispatch.
- **Response:**
  - `204 No Content`: If the dispatch was removed successfully.
  - `401 Unauthorized`: If the user is not authenticated.
  - `404 Not Found`: If the folder or dispatch does not exist, or if the user does not own the dispatch.

#### Delete a folder

- **Endpoint:** `DELETE /folders/{folder_id}`
- **Description:** Deletes a folder.
- **Path Parameters:**
  - `folder_id` (integer, required): The ID of the folder to delete.
- **Response:**
  - `204 No Content`: If the folder was deleted successfully.
  - `401 Unauthorized`: If the user is not authenticated.
  - `403 Forbidden`: If the user is not authorized to delete the folder.
  - `404 Not Found`: If the folder does not exist.

## FRONTEND STYLE
- Copy the same structure and css style of rollcall service
- when an user access their dispatch page. They can see all their dispatch in table form (they can change to gallery form), with a search bar with advanced filter.
- User can pressed a Send Dispatch button to open a pop up to type in information, there is a greyed out button called Save as Draft next to send button. User can tick on "Set as draft", the Save as Draft button shall changed color, the Send button get disabled. If the user choose Save as Draft now, the dispatch shall be saved as draft. If the Set as Draft is not ticked, User can send, to assignees, using assignee's username.
- If the dispatch was saved as draft, later, user can choose it from their disaptch list and send.
- User can accept or reject a disaptch that was sent to them by choosing dispatch from their list then accept (dispatchs status to accepted) or reject them (dispatch status to rejected)
