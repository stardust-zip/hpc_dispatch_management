from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import UniqueConstraint

from .database import Base
from .schemas import DispatchStatus, UserType


class User(Base):
    """
    Represents a User in our database (SQLAlchemy 2.0 syntax).
    This stores a *cache* of the user info from the JWT.
    """

    __tablename__: str = "users"

    # This is the 'sub' from the JWT
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    user_type: Mapped[UserType] = mapped_column(SAEnum(UserType))
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_admin: Mapped[bool] = mapped_column(default=False)

    # Relationship: A user can create many dispatches
    dispatches: Mapped[list["Dispatch"]] = relationship(back_populates="author")
    # Relationship: A user can be assigned to many dispatches
    assigned_dispatches: Mapped[list["DispatchAssignment"]] = relationship(
        back_populates="assignee"
    )


class Dispatch(Base):
    """
    Represents an official dispatch document (SQLAlchemy 2.0 syntax).
    """

    __tablename__: str = "dispatches"

    id: Mapped[int] = mapped_column(primary_key=True)
    serial_number: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(255))

    # User's insight: This is the description, not the full content
    description: Mapped[str] = mapped_column(Text)

    # New field for the file link
    file_url: Mapped[str | None] = mapped_column(String(1024))

    status: Mapped[DispatchStatus] = mapped_column(
        SAEnum(DispatchStatus, native_enum=False, length=50),
        default=DispatchStatus.PENDING,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_onupdate=func.now()
    )

    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    author: Mapped["User"] = relationship(back_populates="dispatches", lazy="selectin")

    # Relationship: A dispatch can be assigned to many users
    assignments: Mapped[list["DispatchAssignment"]] = relationship(
        back_populates="dispatch"
    )


class DispatchAssignment(Base):
    """
    Association table linking Dispatches to assigned Users (SQLAlchemy 2.0 syntax).
    This handles the many-to-many relationship.
    """

    __tablename__: str = "dispatch_assignments"
    __table_args__ = (
        UniqueConstraint("dispatch_id", "assignee_id", name="uix_dispatch_assignee"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dispatch_id: Mapped[int] = mapped_column(
        ForeignKey("dispatches.id", ondelete="CASCADE")
    )

    # The user (lecturer/admin) it's assigned to
    assignee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    # Optional: Add info about the assignment itself
    action_required: Mapped[str | None] = mapped_column(Text)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    dispatch: Mapped["Dispatch"] = relationship(back_populates="assignments")
    assignee: Mapped["User"] = relationship(back_populates="assigned_dispatches")
