# HPC DISPATCH MANAGEMENT

## Base Configuration & Authentication
* **Base Path**: `/dispatches` (for all dispatch-related endpoints) and `/` for health check.
* **Authentication**: All `/dispatches` endpoints require a valid JWT passed in the `Authorization` header as a Bearer token (`Authorization: Bearer <token>`).
* **Authorization**: Access is restricted to users with `UserType.LECTURER` or Admins. Students (`UserType.STUDENT`) will receive a `403 Forbidden` response.

---

## Data Models / Enums

**DispatchStatus**
* `approved`
* `rejected`
* `pending`
* `in_progress`
* `draft`

**DispatchTypeSearch**
* `incoming`
* `outgoing`
* `all`

**UserInfo (Nested in responses)**
```json
{
  "id": 1,
  "full_name": "Nguyen Van A",
  "email": "nguyenvana@example.com"
}
```

**DispatchAssignmentResponse (Nested in responses)**
```json
{
  "id": 1,
  "assignee_id": 5,
  "action_required": "Please review this plan.",
  "review_comment": "Looks good to me. Approved.",
  "assigned_at": "2026-03-17T09:00:00Z"
}
```

---

## Endpoints

### 1. Health Check
Checks if the HPC Dispatch Management service is running.
* **Method & Path**: `GET /`
* **Response**: `200 OK`
```json
{
  "status": "ok",
  "service": "HPC Dispatch Management"
}
```

### 2. Create a Dispatch
Creates a new dispatch. The creator is automatically set as the author, and the dispatch starts with a `DRAFT` status.
* **Method & Path**: `POST /dispatches/`
* **Request Body** (`application/json`):
```json
{
  "title": "Kế hoạch thi học kỳ 1",
  "serial_number": "KH-002/2026",
  "description": "Kế hoạch tổ chức thi kết thúc học phần.",
  "file_url": "[http://example.com/file](http://example.com/file)" 
}
```
*(Note: `file_url` is optional, `title` max 255 chars, `serial_number` max 100 chars)*
* **Response**: `201 Created` returns the full Dispatch object.

### 3. Get Dispatches (List & Search)
Retrieves a paginated list of dispatches with advanced filtering, including all user assignments and review comments.
* **Method & Path**: `GET /dispatches/`
* **Query Parameters**:
  * `skip` (int, default: 0) - For pagination.
  * `limit` (int, default: 100) - For pagination.
  * `status` (string, optional) - Filter by `DispatchStatus` (e.g., `draft`, `pending`).
  * `dispatch_type` (string, default: `all`) - Valid values: `incoming`, `outgoing`, `all`.
  * `search` (string, optional) - Case-insensitive search applied to the `title` or `serial_number`.
* **Response**: `200 OK`
```json
[
  {
    "title": "Kế hoạch thi học kỳ 1",
    "serial_number": "KH-002/2026",
    "description": "Kế hoạch tổ chức thi...",
    "file_url": null,
    "id": 1,
    "author_id": 10,
    "status": "approved",
    "created_at": "2026-03-17T08:26:00Z",
    "updated_at": "2026-03-18T10:00:00Z",
    "author": {
      "id": 10,
      "full_name": "Admin System",
      "email": "admin@system.com"
    },
    "assignments": [
      {
        "id": 1,
        "assignee_id": 5,
        "action_required": "Please review this plan.",
        "review_comment": "Looks good to me. Approved.",
        "assigned_at": "2026-03-17T09:00:00Z"
      }
    ]
  }
]
```

### 4. Get a Single Dispatch
Retrieves a single dispatch by its ID, including all user assignments and review comments.
* **Method & Path**: `GET /dispatches/{dispatch_id}`
* **Response**: `200 OK` (Returns the Dispatch object with nested `assignments`).
* **Errors**: `404 Not Found` if the dispatch doesn't exist.

### 5. Update a Dispatch
Updates the details of a specific dispatch.
* **Method & Path**: `PUT /dispatches/{dispatch_id}`
* **Business Rules**:
  * If the status is `DRAFT`, only the original author can edit it.
  * If the status is NOT `DRAFT` (e.g., sent), only an **Admin** can edit it.
* **Request Body** (all fields are optional):
```json
{
  "title": "Updated Title",
  "serial_number": "KH-003/2026",
  "description": "Updated desc",
  "file_url": "[http://example.com/new_file](http://example.com/new_file)",
  "status": "in_progress"
}
```
* **Response**: `200 OK` (Returns the updated Dispatch object).
* **Errors**: `404 Not Found`, `403 Forbidden` (If permission rules are not met).

### 6. Delete a Dispatch
Removes a dispatch from the system.
* **Method & Path**: `DELETE /dispatches/{dispatch_id}`
* **Business Rules**: 
  * If the status is `DRAFT`, only the creator can delete it.
  * If it has been sent, only an **Admin** can delete it.
* **Response**: `204 No Content`
* **Errors**: `403 Forbidden`

### 7. Assign a Dispatch
Assigns a `DRAFT` dispatch to other users for review. This transitions the document to `PENDING` status, moves files in the drive, and triggers notifications.
* **Method & Path**: `POST /dispatches/{dispatch_id}/assign`
* **Business Rules**: Only the author can perform this action. The dispatch must currently be in `DRAFT` status.
* **Request Body**:
```json
{
  "assignee_usernames": ["lecturer1", "lecturer2"],
  "action_required": "Please review and approve this document by Friday."
}
```
* **Response**: `200 OK`
```json
{
  "message": "Dispatch assigned to 2 user(s) and notifications sent."
}
```
* **Errors**: `404 Not Found`, `403 Forbidden` (If not author), `400 Bad Request` (If dispatch is not a draft).

### 8. Update Dispatch Status (Approve/Reject)
Allows an assigned user to update the status of a dispatch they are reviewing and submit a review comment.
* **Method & Path**: `PUT /dispatches/{dispatch_id}/status`
* **Business Rules**: The current user MUST be one of the assignees. This will trigger a notification back to the document's author and save the comment to the user's assignment record.
* **Request Body**:
```json
{
  "status": "approved",  
  "review_comment": "Looks good to me. Approved."
}
```
*(Note: `status` must be either `approved` or `rejected`. `review_comment` is optional max 1000 chars)*
* **Response**: `200 OK` (Returns the updated Dispatch object. The saved comment can be viewed via the GET endpoints).
* **Errors**: `404 Not Found`, `403 Forbidden` (If the user is not an assignee).
