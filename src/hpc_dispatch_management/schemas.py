from datetime import datetime, timezone
from enum import Enum
from typing import Generic, Literal, TypeVar

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, HttpUrl
from pydantic.alias_generators import to_camel
from pydantic.functional_validators import field_validator

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


# 0. Enums


class DispatchStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DRAFT = "draft"


class UserType(str, Enum):
    LECTURER = "lecturer"
    STUDENT = "student"


# 1. User Schema (from User Service JWT)


class User(BaseModel):
    sub: int
    user_type: UserType
    username: str
    is_admin: bool
    email: EmailStr
    full_name: str
    department_id: int | None = None
    class_id: int | None = None


class UserInfo(BaseModel):
    id: int
    full_name: str
    email: EmailStr

    class ConfigDict:
        from_attributes: bool = True


# 2. Kafka Notification Schemas


class KafkaNewDispatchPayload(BaseModel):
    user_id: int
    user_type: UserType
    document_title: str
    document_url: HttpUrl
    document_serial_number: str
    assigner_name: str
    assignee_name: str
    action_required: str
    date: AwareDatetime
    sender_id: int
    sender_type: UserType

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class KafkaDispatchStatusUpdatePayload(BaseModel):
    user_id: int
    user_type: UserType
    subject: str
    author_name: str
    document_serial_number: str
    document_title: str
    reviewer_name: str
    status: str
    review_comment: str | None = None
    document_url: HttpUrl
    year: str
    app_name: str = "HPC Corp"

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class KafkaMessage(BaseModel):
    topic: str
    payload: (
        KafkaNewDispatchPayload | KafkaDispatchStatusUpdatePayload
    )  # Corrected Union
    priority: Literal["low", "medium", "high"] = "medium"
    key: str


# 3. Dispatch Document Schemas


class DispatchBase(BaseModel):
    title: str = Field(..., max_length=255)
    serial_number: str = Field(..., max_length=100)
    description: str
    file_url: HttpUrl | None = None


class DispatchCreate(DispatchBase):
    pass


class DispatchUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    serial_number: str | None = Field(None, max_length=100)
    description: str | None = None
    file_url: HttpUrl | None = None
    status: DispatchStatus | None = None


class Dispatch(DispatchBase):
    id: int
    author_id: int
    status: DispatchStatus
    created_at: AwareDatetime
    updated_at: AwareDatetime | None = None
    author: UserInfo

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def ensure_timezone_aware(cls, v: datetime | None) -> datetime | None:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    class ConfigDict:
        from_attributes: bool = True


class DispatchTypeSearch(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    ALL = "all"


# 4. API Action Schemas
class DispatchAssign(BaseModel):
    """Schema for assigning a dispatch to users."""

    assignee_usernames: list[str] = Field(..., min_length=1)
    action_required: str = Field(..., max_length=500)


class DispatchStatusUpdate(BaseModel):
    """Schema for an assignee to update the status of a dispatch."""

    status: Literal[DispatchStatus.APPROVED, DispatchStatus.REJECTED]
    review_comment: str | None = Field(None, max_length=1000)
