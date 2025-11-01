from sqlalchemy.orm import Session, joinedload
from . import models, schemas
from sqlalchemy import or_

# region User Cache Management


def get_user(db: Session, user_id: int) -> models.User | None:
    """
    FIX: Retrieves a single user from the local database cache by their ID.
    This function was missing.
    """
    return db.query(models.User).filter(models.User.id == user_id).first()


def sync_user_from_jwt(db: Session, user_jwt_data: schemas.User) -> models.User:
    """
    Synchronizes user data from a trusted JWT into our local database.
    """
    db_user = get_user(db, user_id=user_jwt_data.sub)  # Now uses the new function
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
            user_type=schemas.UserType(user_jwt_data.user_type),
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
    return (
        db.query(models.Dispatch)
        .options(joinedload(models.Dispatch.author))
        .filter(models.Dispatch.id == dispatch_id)
        .first()
    )


def get_dispatches(
    db: Session, skip: int = 0, limit: int = 100
) -> list[models.Dispatch]:
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
    update_data = dispatch_update.model_dump(exclude_unset=True)
    if update_data.get("file_url"):
        update_data["file_url"] = str(update_data["file_url"])

    for key, value in update_data.items():
        setattr(db_dispatch, key, value)

    db.add(db_dispatch)
    db.commit()
    db.refresh(db_dispatch)
    return db_dispatch


def delete_dispatch(db: Session, dispatch_id: int) -> models.Dispatch | None:
    db_dispatch = get_dispatch(db, dispatch_id)
    if db_dispatch:
        db.delete(db_dispatch)
        db.commit()
    return db_dispatch


def assign_dispatch_to_users(
    db: Session, db_dispatch: models.Dispatch, assignment_data: schemas.DispatchAssign
) -> list[models.User]:
    """
    Creates DispatchAssignment records and updates dispatch status.
    Returns the list of assignee user objects.
    """
    assignee_ids = assignment_data.assignee_ids
    # Using set for efficiency and to handle duplicate IDs in input
    unique_assignee_ids = set(assignee_ids)
    assignees = (
        db.query(models.User).filter(models.User.id.in_(unique_assignee_ids)).all()
    )

    if len(assignees) != len(unique_assignee_ids):
        raise ValueError("One or more assignee IDs are invalid.")

    for assignee in assignees:
        assignment = models.DispatchAssignment(
            dispatch_id=db_dispatch.id,
            assignee_id=assignee.id,
            action_required=assignment_data.action_required,
        )
        db.add(assignment)

    # Transition the dispatch from DRAFT to PENDING
    db_dispatch.status = schemas.DispatchStatus.PENDING
    db.add(db_dispatch)

    # A commit expires the state of all instances.
    db.commit()

    # After a commit, refresh the objects that will be used
    # outside this session. This loads their fresh state so they no longer
    # need the session to be accessed.
    db.refresh(db_dispatch)
    for assignee in assignees:
        db.refresh(assignee)

    return assignees


def get_dispatches_with_filters(
    db: Session,
    user_id: int,
    dispatch_type: schemas.DispatchTypeSearch,
    status: schemas.DispatchStatus | None,
    search: str | None,
    skip: int,
    limit: int,
) -> list[models.Dispatch]:
    """
    Retrieves dispatches with advanced filtering based on the user's perspective.
    """
    # Start with a base query and eager load author info to prevent N+1 queries
    query = db.query(models.Dispatch).options(joinedload(models.Dispatch.author))

    # 1. Filter by User Perspective (INCOMING/OUTGOING)
    if dispatch_type == schemas.DispatchTypeSearch.INCOMING:
        # An incoming dispatch is one where the user is an assignee
        query = query.join(models.DispatchAssignment).filter(
            models.DispatchAssignment.assignee_id == user_id
        )
    elif dispatch_type == schemas.DispatchTypeSearch.OUTGOING:
        # An outgoing dispatch is one where the user is the author
        query = query.filter(models.Dispatch.author_id == user_id)
    else:  # 'ALL'
        # A dispatch is related to the user if they are the author OR an assignee
        query = query.join(models.DispatchAssignment, isouter=True).filter(
            or_(
                models.Dispatch.author_id == user_id,
                models.DispatchAssignment.assignee_id == user_id,
            )
        )

    # 2. Filter by Status (if provided)
    if status:
        query = query.filter(models.Dispatch.status == status)

    # 3. Filter by Search Term (if provided)
    if search:
        search_term = f"%{search}%"
        # Case-insensitive search on title or serial number
        query = query.filter(
            or_(
                models.Dispatch.title.ilike(search_term),
                models.Dispatch.serial_number.ilike(search_term),
            )
        )

    # Apply ordering and pagination before executing the query
    dispatches = (
        query.order_by(models.Dispatch.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return dispatches


# endregion

# region Folder CRUD


def get_folder(db: Session, folder_id: int) -> models.Folder | None:
    """Retrieves a single folder by its ID, with its dispatches."""
    return (
        db.query(models.Folder)
        .options(joinedload(models.Folder.dispatches))
        .filter(models.Folder.id == folder_id)
        .first()
    )


def get_folders_by_owner(db: Session, owner_id: int) -> list[models.Folder]:
    """Retrieves all folders for a specific user."""
    return db.query(models.Folder).filter(models.Folder.owner_id == owner_id).all()


def create_folder(
    db: Session, folder: schemas.FolderCreate, owner_id: int
) -> models.Folder:
    """Creates a new folder for a user."""
    db_folder = models.Folder(**folder.model_dump(), owner_id=owner_id)
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    return db_folder


def delete_folder(db: Session, db_folder: models.Folder) -> models.Folder:
    """Deletes a folder."""
    db.delete(db_folder)
    db.commit()
    return db_folder


def add_dispatch_to_folder(
    db: Session, db_dispatch: models.Dispatch, db_folder: models.Folder
) -> models.Folder:
    """Adds a dispatch to a folder's collection."""
    if db_dispatch not in db_folder.dispatches:
        db_folder.dispatches.append(db_dispatch)
        db.commit()
        db.refresh(db_folder)
    return db_folder


def remove_dispatch_from_folder(
    db: Session, db_dispatch: models.Dispatch, db_folder: models.Folder
) -> models.Folder:
    """Removes a dispatch from a folder's collection."""
    if db_dispatch in db_folder.dispatches:
        db_folder.dispatches.remove(db_dispatch)
        db.commit()
        db.refresh(db_folder)
    return db_folder


# endregion
