from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session


from .. import crud, schemas, services
from ..database import get_db
from ..security import get_current_user

router = APIRouter(
    prefix="/dispatches",
    tags=["Dispatches"],
    # All endpoints in this router will require a valid user
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=schemas.Dispatch, status_code=status.HTTP_201_CREATED)
async def create_dispatch(
    dispatch: schemas.DispatchCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
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
    skip: int = 0,
    limit: int = 100,
    status: schemas.DispatchStatus | None = None,
    dispatch_type: schemas.DispatchTypeSearch = schemas.DispatchTypeSearch.ALL,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
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
async def read_dispatch(dispatch_id: int, db: Session = Depends(get_db)):
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
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
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
):
    """
    Delete a dispatch.
    - Business Rule: If in DRAFT, only the creator can delete.
    - Business Rule: If sent (not DRAFT), only an admin can delete.
    """
    db_dispatch = crud.get_dispatch(db, dispatch_id=dispatch_id)
    if db_dispatch is None:
        # We don't raise 404 on delete to prevent leaking information
        # Simply return success. This is an idempotent operation.
        return

    # Check permissions based on dispatch status
    is_owner = db_dispatch.author_id == current_user.sub
    is_draft = db_dispatch.status == schemas.DispatchStatus.DRAFT

    if (is_draft and not is_owner) or (not is_draft and not current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this dispatch.",
        )

    _ = crud.delete_dispatch(db=db, dispatch_id=dispatch_id)
    return


@router.post("/{dispatch_id}/assign", status_code=status.HTTP_200_OK)
async def assign_dispatch(
    dispatch_id: int,
    assignment: schemas.DispatchAssign,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """
    Assign a DRAFT dispatch to users.
    - Only the author can assign a dispatch.
    - This changes the status from DRAFT to PENDING.
    - This sends a notification to each assignee.
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

    # Sync assignees' user data from JWT if they don't exist in cache (hypothetically)
    # In a real scenario, you'd probably need to fetch user details from the User service.
    # For now, we assume they have interacted with the service before.

    try:
        assignees = crud.assign_dispatch_to_users(db, db_dispatch, assignment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Send notifications to all assignees
    for assignee in assignees:
        await services.send_new_dispatch_notification(
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
    - Sends a notification back to the original author.
    """
    db_dispatch = crud.get_dispatch(db, dispatch_id=dispatch_id)
    if not db_dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    # Verify if the current user is an assignee of this dispatch
    is_assignee = any(
        assign.assignee_id == current_user.sub for assign in db_dispatch.assignments
    )
    if not is_assignee:
        raise HTTPException(
            status_code=403, detail="You are not an assignee of this dispatch"
        )

    # Update the dispatch status
    db_dispatch.status = status_update.status
    db.commit()
    db.refresh(db_dispatch)

    reviewer = crud.get_user(db, current_user.sub)
    if not reviewer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reviewer user not found.",
        )

    # Send notification back to the author
    await services.send_status_update_notification(
        dispatch=db_dispatch,
        reviewer=reviewer,  # Pass the validated reviewer
        status=status_update.status,
        comment=status_update.review_comment,
    )

    return db_dispatch
