from sqlalchemy.orm import Session, joinedload
from . import models, schemas
from typing import List

# region User Cache Management


def sync_user_from_jwt(db: Session, user_jwt_data: schemas.User) -> models.User:
    """
    Synchronizes user data from a trusted JWT into our local database.

    This function checks if a user exists in our local cache.
    - If they do, it updates their details from the JWT.
    - If they don't, it creates a new record in our local cache.

    This is NOT creating a new system-wide user. It's creating a local
    replica required for database foreign key relationships.
    """
    db_user = db.query(models.User).filter(models.User.id == user_jwt_data.sub).first()

    if db_user:
        # User exists, update their cached info in case it changed
        db_user.username = user_jwt_data.username
        db_user.email = user_jwt_data.email
        db_user.full_name = user_jwt_data.full_name
        db_user.user_type = schemas.UserType(user_jwt_data.user_type)
        db_user.department_id = user_jwt_data.department_id
        db_user.is_admin = user_jwt_data.is_admin
    else:
        # User does not exist in our local cache, create the record
        db_user = models.User(
            id=user_jwt_data.sub,
            username=user_jwt_data.username,
            email=user_jwt_data.email,
            full_name=user_jwt_data.full_name,
            user_type=user_jwt_data.user_type,
            department_id=user_jwt_data.department_id,
            is_admin=user_jwt_data.is_admin,
        )
        db.add(db_user)

    db.commit()
    db.refresh(db_user)
    return db_user


# endregion

# region Dispatch CRUD


def get_dispatch(db: Session, dispatch_id: int) -> models.Dispatch | None:
    """
    Retrieves a single dispatch by its ID, eager-loading the author info.
    """
    return (
        db.query(models.Dispatch)
        .options(joinedload(models.Dispatch.author))
        .filter(models.Dispatch.id == dispatch_id)
        .first()
    )


def get_dispatches(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Dispatch]:
    """
    Retrieves a list of dispatches with pagination.
    """
    return (
        db.query(models.Dispatch)
        .options(joinedload(models.Dispatch.author))
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_dispatch(
    db: Session, dispatch: schemas.DispatchCreate, author_id: int
) -> models.Dispatch:
    """
    Creates a new dispatch record in the database.
    """
    dispatch_data = dispatch.model_dump()

    if dispatch_data.get("file_url"):
        dispatch_data["file_url"] = str(dispatch_data["file_url"])

    db_dispatch = models.Dispatch(
        **dispatch_data, author_id=author_id, status=schemas.DispatchStatus.DRAFT
    )

    db.add(db_dispatch)
    db.commit()
    db.refresh(db_dispatch)
    return db_dispatch


def update_dispatch(
    db: Session, db_dispatch: models.Dispatch, dispatch_update: schemas.DispatchUpdate
) -> models.Dispatch:
    """
    Updates an existing dispatch record.
    """
    update_data = dispatch_update.model_dump(exclude_unset=True)

    if update_data.get("file_url"):
        update_data["file_url"] = str(update_data["file_url"])

    for key, value in update_data.items():
        setattr(db_dispatch, key, value)

    for key, value in update_data.items():
        setattr(db_dispatch, key, value)
    db.add(db_dispatch)
    db.commit()
    db.refresh(db_dispatch)
    return db_dispatch


def delete_dispatch(db: Session, dispatch_id: int) -> models.Dispatch | None:
    """
    Deletes a dispatch from the database.
    """
    db_dispatch = get_dispatch(db, dispatch_id)
    if db_dispatch:
        db.delete(db_dispatch)
        db.commit()
    return db_dispatch


# endregion
