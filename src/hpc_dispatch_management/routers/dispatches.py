import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security.http import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .. import schemas
from ..core.security import bearer_scheme, get_current_user
from ..db import crud, models
from ..db.database import get_db, get_http_client
from ..external_services import drive_service, notification_service, user_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/dispatches",
    tags=["Dispatches"],
    # All endpoints in this router will require a valid user
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=schemas.Dispatch, status_code=status.HTTP_201_CREATED)
async def create_dispatch(
    dispatch: schemas.DispatchCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[schemas.User, Depends(get_current_user)],
):
    """
    Create a new dispatch.
    - The creator is automatically assigned as the author.
    - New dispatches always start with 'DRAFT' status.
    """
    # Sync user from JWT to local DB to ensure foreign key constraint is met
    _ = crud.sync_user_from_jwt(db=db, user_jwt_data=current_user)
    return crud.create_dispatch(db=db, dispatch=dispatch, author_id=current_user.sub)


@router.get("/", response_model=list[schemas.Dispatch])
async def read_dispatches(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
    status: schemas.DispatchStatus | None = None,
    dispatch_type: schemas.DispatchTypeSearch = schemas.DispatchTypeSearch.ALL,
    search: str | None = None,
):
    """
    Retrieve a list of dispatches with advanced filtering:
    - **status**: Filter by dispatch status (e.g., 'PENDING').
    - **dispatch_type**: Filter by user perspective ('incoming', 'outgoing', or 'all').
    - **search**: Search term for title or serial number.
    """
    dispatches = crud.get_dispatches_with_filters(
        db=db,
        user_id=current_user.sub,
        dispatch_type=dispatch_type,
        status=status,
        search=search,
        skip=skip,
        limit=limit,
    )
    return dispatches


@router.get("/{dispatch_id}", response_model=schemas.Dispatch)
async def read_dispatch(dispatch_id: int, db: Annotated[Session, Depends(get_db)]):
    """
    Retrieve a single dispatch by its ID.
    """
    db_dispatch = crud.get_dispatch(db, dispatch_id=dispatch_id)
    if db_dispatch is None:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return db_dispatch


@router.put("/{dispatch_id}", response_model=schemas.Dispatch)
async def update_dispatch(
    dispatch_id: int,
    dispatch_update: schemas.DispatchUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[schemas.User, Depends(get_current_user)],
):
    """
    Update a dispatch.
    - Business Rule: If in DRAFT, only the creator can edit.
    - Business Rule: If sent (not DRAFT), only an admin can edit.
    """
    db_dispatch = crud.get_dispatch(db, dispatch_id=dispatch_id)
    if db_dispatch is None:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    # Check permissions based on dispatch status
    is_owner = db_dispatch.author_id == current_user.sub
    is_draft = db_dispatch.status == schemas.DispatchStatus.DRAFT

    if is_draft and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this draft.",
        )

    if not is_draft and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can edit a sent dispatch.",
        )

    return crud.update_dispatch(
        db=db, db_dispatch=db_dispatch, dispatch_update=dispatch_update
    )


@router.delete("/{dispatch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dispatch(
    dispatch_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """
    Delete a dispatch and move its associated file to the trash in Drive.
    - Business Rule: If in DRAFT, only the creator can delete.
    - Business Rule: If sent (not DRAFT), only an admin can delete.
    """
    db_dispatch = crud.get_dispatch(db, dispatch_id=dispatch_id)
    if db_dispatch is None:
        # We don't raise 404 on delete to prevent leaking information
        return

    # Check permissions based on dispatch status
    is_owner = db_dispatch.author_id == current_user.sub
    is_draft = db_dispatch.status == schemas.DispatchStatus.DRAFT

    if (is_draft and not is_owner) or (not is_draft and not current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this dispatch.",
        )

    # 1. Capture the file URL before deleting the DB record
    file_url = db_dispatch.file_url

    # 2. Delete the dispatch from the SQL database
    _ = crud.delete_dispatch(db=db, dispatch_id=dispatch_id)

    # 3. Clean up the physical file in the user's Drive
    if file_url:
        try:
            # We must use credentials.credentials to get the raw token string
            await drive_service.trash_dispatch_file(
                file_url=file_url, token=credentials.credentials, client=client
            )
        except Exception as e:
            logger.exception(
                f"Failed to move file to trash for dispatch {dispatch_id}: {e}"
            )

    return


@router.post("/{dispatch_id}/assign", status_code=status.HTTP_200_OK)
async def assign_dispatch(
    dispatch_id: int,
    assignment: schemas.DispatchAssign,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
    token: str = Depends(bearer_scheme),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """
    Assign a DRAFT dispatch to users.
    """
    db_dispatch = crud.get_dispatch(db, dispatch_id=dispatch_id)
    if not db_dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    if db_dispatch.author_id != current_user.sub:
        raise HTTPException(
            status_code=403, detail="Only the author can assign this dispatch"
        )
    if db_dispatch.status != schemas.DispatchStatus.DRAFT:
        raise HTTPException(
            status_code=400, detail="Only draft dispatches can be assigned"
        )

    unique_usernames = set(assignment.assignee_usernames)

    # 1. Check which users already exist in the local database
    existing_users = (
        db.query(models.User).filter(models.User.username.in_(unique_usernames)).all()
    )
    existing_usernames = {u.username for u in existing_users}

    # 2. Identify who is missing
    missing_usernames = unique_usernames - existing_usernames

    # 3. Fetch and save missing lecturers from the System Management service
    if missing_usernames:
        for username in missing_usernames:
            lecturer_data = await user_service.fetch_lecturer_by_username(
                username, token.credentials, client
            )

            if not lecturer_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"User '{username}' is invalid or does not exist in the system.",
                )

            # Cache the new user locally
            new_user = models.User(
                id=lecturer_data["id"],
                username=lecturer_data["username"],
                email=lecturer_data["email"],
                full_name=lecturer_data.get(
                    "full_name", lecturer_data.get("name", username)
                ),
                user_type=schemas.UserType.LECTURER,
                department_id=lecturer_data.get("department_id"),
                is_admin=lecturer_data.get("is_admin", False),
            )
            db.add(new_user)

        db.commit()  # Save all newly fetched users to the DB

    # Now the original CRUD function will succeed because all users are guaranteed to be in the local DB
    try:
        assignees = crud.assign_dispatch_to_users(db, db_dispatch, assignment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        await drive_service.organize_dispatch_in_drive(
            dispatch=db_dispatch,
            assignees=assignees,
            token=token.credentials,
            client=client,
        )
    except Exception as e:
        logger.exception(f"Failed to organize dispatch in drive: {e}")

    for assignee in assignees:
        await notification_service.send_new_dispatch_notification(
            dispatch=db_dispatch,
            assigner=db_dispatch.author,
            assignee=assignee,
            action_required=assignment.action_required,
        )

    return {
        "message": f"Dispatch assigned to {len(assignees)} user(s) and notifications sent."
    }


@router.put("/{dispatch_id}/status", response_model=schemas.Dispatch)
async def update_dispatch_status(
    dispatch_id: int,
    status_update: schemas.DispatchStatusUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """
    Update the status of a dispatch (Approve/Reject).
    - Only an assignee can perform this action.
    - Saves the review comment.
    - Sends a notification back to the original author.
    """
    db_dispatch = crud.get_dispatch(db, dispatch_id=dispatch_id)
    if not db_dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    # 1. Verify if the current user is an assignee and get their assignment record
    user_assignment = next(
        (
            assign
            for assign in db_dispatch.assignments
            if assign.assignee_id == current_user.sub
        ),
        None,
    )

    if not user_assignment:
        raise HTTPException(
            status_code=403, detail="You are not an assignee of this dispatch"
        )

    # 2. Update the dispatch status
    db_dispatch.status = status_update.status

    # 3. Save the review comment to the user's assignment record
    if status_update.review_comment is not None:
        user_assignment.review_comment = status_update.review_comment

    db.commit()
    db.refresh(db_dispatch)

    reviewer = crud.get_user(db, current_user.sub)
    if not reviewer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reviewer user not found.",
        )

    # Send notification back to the author
    await notification_service.send_status_update_notification(
        dispatch=db_dispatch,
        reviewer=reviewer,
        status=status_update.status,
        comment=status_update.review_comment,
    )

    return db_dispatch
