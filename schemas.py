from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Literal, Optional
from datetime import datetime
from enum import Enum

# 0. Enums


class DispatchStatus(str, Enum):
    """
    Enum for dispatch statuses.
    Pydantic wll validate against hese values.
    """

    APPROVED = "Đã phê duyệt"
    REJECTED = "Đã từ chối"
    PENDING = "Chờ xử lý"
    IN_PROGRESS = "Đang xử lý"
    DRAFT = "Nháp"
    # When in draft, lecturer can edit and delete dispatch,
    # when they are in other status, only admin can affect them.


class UserType(str, Enum):
    LECTURER = "lecturer"
    STUDENT = "student"  # However, student can't access dispatch pages.


# 1. User Schema (from user User Service JWT).
class User(BaseModel):
    """
    This model represents the user data decoded from
    the JWT token.
    """

    sub: int  # User's id.
    user_type: Literal["lecturer", "student"]
    username: str
    is_admin: bool
    email: EmailStr
    full_name: str
    department_id: int
    class_id: Optional[int] = None

    # Let's ignore the iat and exp in the model as they are for token validation,
    # but the user dependency will check them.

    # 2. Kafka Notification Schemas
    class KafkaNewDispatchPayload(BaseModel):
        """
        This is the payload for the 'official.dispatch' Kafka topic.
        """

        user_id: int
        user_type: Literal["lecturer", "student"]
        documentTitle: str
        documentUrl: HttpUrl
        documentSerialNumber: str
        assignerName: str
        assigneeName: str
        actionRequired: str
        date: datetime
        sender_id: int
        sender_type: Literal["lecturer", "student"]

    class KafkaDispatchStatusUpdatePayload(BaseModel):
        """
        This is the payload for the 'official.dispatch.status.update' Kafka topic.
        """

        user_id: int
        user_type: Literal["lecturer", "student"]
        subject: str
        authorName: str
        documentSerialNumber: str
        documentTitle: str
        reviewerName: str
        status: DispatchStatus
        reviewComment: Optional[str] = None
        documentUrl: HttpUrl
        year: str
        app_name: str = "HPC Corp"

    class KafkaMessage(BaseModel):
        """
        The complete message structure to be sent to the notification service.
        """

        topic: str
        payload: (
            KafkaNewDispatchPayload | KafkaDispatchStatusUpdatePayload
        )  # ruff is showing botth these name not defined
        priority: Literal["low", "medium", "high"] = "medium"
        key: str

    # 3. Dispatch Document Schemas
    class DispatchBase(BaseModel):
        title: str
        content: str

    class DispatchCreate(DispatchBase):
        pass

    class Dispatch(DispatchBase):
        id: int
        owner_id: int
        created_at: datetime
        status: DispatchStatus

        class Config:
            from_attributes = True  # Change from org_mode for Pydantic v2.
