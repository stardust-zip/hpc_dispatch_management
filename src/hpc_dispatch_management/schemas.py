from pydantic import BaseModel, EmailStr, HttpUrl, Field
from typing import Literal
from datetime import datetime
from enum import Enum

# 0. Enums


class DispatchStatus(str, Enum):
    APPROVED = "Đã phê duyệt"
    REJECTED = "Đã từ chối"
    PENDING = "Chờ xử lý"
    IN_PROGRESS = "Đang xử lý"
    DRAFT = "Nháp"


class UserType(str, Enum):
    LECTURER = "lecturer"
    STUDENT = "student"


# 1. User Schema (from User Service JWT)


class User(BaseModel):
    sub: int
    user_type: Literal["lecturer", "student"]
    username: str
    is_admin: bool
    email: EmailStr
    full_name: str
    department_id: int
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
    documentTitle: str
    documentUrl: HttpUrl
    documentSerialNumber: str
    assignerName: str
    assigneeName: str
    actionRequired: str
    date: datetime
    sender_id: int
    sender_type: UserType


class KafkaDispatchStatusUpdatePayload(BaseModel):
    user_id: int
    user_type: UserType
    subject: str
    authorName: str
    documentSerialNumber: str
    documentTitle: str
    reviewerName: str
    status: str
    reviewComment: str | None = None
    documentUrl: HttpUrl
    year: str
    app_name: str = "HPC Corp"


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
    created_at: datetime
    updated_at: datetime | None = None
    author: UserInfo

    class ConfigDict:
        from_attributes: bool = True


class DispatchTypeSearch(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    ALL = "all"


# 4. API Action Schemas
class DispatchAssign(BaseModel):
    """Schema for assigning a dispatch to users."""

    assignee_usernames: list[str]
    action_required: str = Field(..., max_length=500)


class DispatchStatusUpdate(BaseModel):
    """Schema for an assignee to update the status of a dispatch."""

    status: Literal[DispatchStatus.APPROVED, DispatchStatus.REJECTED]
    review_comment: str | None = Field(None, max_length=1000)


# 5. Folder Schemas


class FolderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class FolderCreate(FolderBase):
    pass


class FolderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)


class Folder(FolderBase):
    id: int
    owner_id: int
    dispatches: list[Dispatch] = []  # Return dispatches within the folder

    class ConfigDict:
        from_attributes = True
