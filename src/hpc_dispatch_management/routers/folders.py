from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas
from ..database import get_db
from ..security import get_current_user

router = APIRouter(
    prefix="/folders",
    tags=["Folders"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=schemas.Folder, status_code=status.HTTP_201_CREATED)
def create_folder_for_user(
    folder: schemas.FolderCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    return crud.create_folder(db=db, folder=folder, owner_id=current_user.sub)


@router.get("/", response_model=List[schemas.Folder])
def read_user_folders(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    return crud.get_folders_by_owner(db=db, owner_id=current_user.sub)


@router.post("/{folder_id}/dispatches/{dispatch_id}", response_model=schemas.Folder)
def add_dispatch_to_folder(
    folder_id: int,
    dispatch_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_folder = crud.get_folder(db, folder_id)
    if not db_folder or db_folder.owner_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Folder not found")

    db_dispatch = crud.get_dispatch(db, dispatch_id)
    # Security check: User can only add dispatches they own.
    if not db_dispatch or db_dispatch.author_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    return crud.add_dispatch_to_folder(db, db_dispatch, db_folder)


@router.delete(
    "/{folder_id}/dispatches/{dispatch_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_dispatch_from_folder(
    folder_id: int,
    dispatch_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_folder = crud.get_folder(db, folder_id)
    if not db_folder or db_folder.owner_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Folder not found")

    db_dispatch = crud.get_dispatch(db, dispatch_id)
    if not db_dispatch or db_dispatch.author_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    crud.remove_dispatch_from_folder(db, db_dispatch, db_folder)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_folder = crud.get_folder(db, folder_id)
    if not db_folder or db_folder.owner_id != current_user.sub:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this folder"
        )
    crud.delete_folder(db, db_folder)
