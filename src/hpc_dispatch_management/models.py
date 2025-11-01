from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    Text,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from .database import Base
from .schemas import DispatchStatus, UserType
from datetime import datetime

dispatch_folder_association = Table(
    "dispatch_folder_association",
    Base.metadata,
    Column("dispatch_id", Integer, ForeignKey("dispatches.id"), primary_key=True),
    Column("folder_id", Integer, ForeignKey("folders.id"), primary_key=True),
)


class User(Base):
    """
    Represents a User in our database (SQLAlchemy 2.0 syntax).
    This stores a *cache* of the user info from the JWT.
    """

    __tablename__: str = "users"

    # This is the 'sub' from the JWT
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    user_type: Mapped[UserType] = mapped_column(SAEnum(UserType))
    department_id: Mapped[int] = mapped_column(Integer)
    is_admin: Mapped[bool] = mapped_column(default=False)

    folders: Mapped[list["Folder"]] = relationship(back_populates="owner")

    # Relationship: A user can create many dispatches
    dispatches: Mapped[list["Dispatch"]] = relationship(back_populates="author")
    # Relationship: A user can be assigned to many dispatches
    assigned_dispatches: Mapped[list["DispatchAssignment"]] = relationship(
        back_populates="assignee"
    )


class Folder(Base):
    __tablename__ = "folders"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    owner: Mapped["User"] = relationship(back_populates="folders")

    # The many-to-many relationship to Dispatch
    dispatches: Mapped[list["Dispatch"]] = relationship(
        secondary=dispatch_folder_association, back_populates="folders"
    )


class Dispatch(Base):
    """
    Represents an official dispatch document (SQLAlchemy 2.0 syntax).
    """

    __tablename__: str = "dispatches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    serial_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)

    # User's insight: This is the description, not the full content
    description: Mapped[str] = mapped_column(Text)

    # New field for the file link
    file_url: Mapped[str | None] = mapped_column(String(1024))

    status: Mapped[DispatchStatus] = mapped_column(
        SAEnum(DispatchStatus), default=DispatchStatus.PENDING
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["User"] = relationship(back_populates="dispatches")

    # Relationship: A dispatch can be assigned to many users
    assignments: Mapped[list["DispatchAssignment"]] = relationship(
        back_populates="dispatch"
    )

    folders: Mapped[list["Folder"]] = relationship(
        secondary=dispatch_folder_association, back_populates="dispatches"
    )


class DispatchAssignment(Base):
    """
    Association table linking Dispatches to assigned Users (SQLAlchemy 2.0 syntax).
    This handles the many-to-many relationship.
    """

    __tablename__: str = "dispatch_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    dispatch_id: Mapped[int] = mapped_column(ForeignKey("dispatches.id"))

    # The user (lecturer/admin) it's assigned to
    assignee_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Optional: Add info about the assignment itself
    action_required: Mapped[str | None] = mapped_column(Text)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    dispatch: Mapped["Dispatch"] = relationship(back_populates="assignments")
    assignee: Mapped["User"] = relationship(back_populates="assigned_dispatches")
