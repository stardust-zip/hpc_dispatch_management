from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas
from ..database import get_db
from ..security import get_current_user

router = APIRouter(
    prefix="/dispatches",
    tags=["Dispatches"],
    # All endpoints in this router will require a valid user
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=schemas.Dispatch, status_code=status.HTTP_201_CREATED)
def create_dispatch(
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
    crud.sync_user_from_jwt(db=db, user_jwt_data=current_user)
    return crud.create_dispatch(db=db, dispatch=dispatch, author_id=current_user.sub)


@router.get("/", response_model=List[schemas.Dispatch])
def read_dispatches(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Retrieve a list of all dispatches.
    """
    dispatches = crud.get_dispatches(db, skip=skip, limit=limit)
    return dispatches


@router.get("/{dispatch_id}", response_model=schemas.Dispatch)
def read_dispatch(dispatch_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single dispatch by its ID.
    """
    db_dispatch = crud.get_dispatch(db, dispatch_id=dispatch_id)
    if db_dispatch is None:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return db_dispatch


@router.put("/{dispatch_id}", response_model=schemas.Dispatch)
def update_dispatch(
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
def delete_dispatch(
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

    crud.delete_dispatch(db=db, dispatch_id=dispatch_id)
    return
