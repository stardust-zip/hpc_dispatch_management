import httpx
from datetime import datetime
import logging
from pydantic import HttpUrl

from . import schemas, models
from .settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def send_new_dispatch_notification(
    dispatch: models.Dispatch,
    assigner: models.User,
    assignee: models.User,
    action_required: str,
):
    """Prepares and sends a notification for a newly assigned dispatch."""
    payload = schemas.KafkaNewDispatchPayload(
        user_id=assignee.id,
        user_type=assignee.user_type,
        documentTitle=dispatch.title,
        documentUrl=HttpUrl(str(dispatch.file_url))
        if dispatch.file_url
        else HttpUrl("http://hpc-system.com/dispatch-not-found"),
        documentSerialNumber=dispatch.serial_number,
        assignerName=assigner.full_name,
        assigneeName=assignee.full_name,
        actionRequired=action_required,
        date=datetime.now(),
        sender_id=assigner.id,
        sender_type=assigner.user_type,
    )

    message = schemas.KafkaMessage(
        topic="official.dispatch",
        payload=payload,
        key=f"dispatch_new_{dispatch.serial_number}_{assignee.id}",
    )

    await _publish_to_kafka_gateway(message)


async def send_status_update_notification(
    dispatch: models.Dispatch,
    reviewer: models.User,
    status: schemas.DispatchStatus,
    comment: str | None,
):
    """Prepares and sends a notification for a dispatch status update."""
    author = dispatch.author
    payload = schemas.KafkaDispatchStatusUpdatePayload(
        user_id=author.id,
        user_type=author.user_type,
        subject=f"Công văn '{dispatch.title}' đã được xử lý",
        authorName=author.full_name,
        documentSerialNumber=dispatch.serial_number,
        documentTitle=dispatch.title,
        reviewerName=reviewer.full_name,
        status=status.value,  # Send the Vietnamese string value
        reviewComment=comment,
        documentUrl=HttpUrl(str(dispatch.file_url))
        if dispatch.file_url
        else HttpUrl("http://hpc-system.com/dispatch-not-found"),
        year=str(dispatch.created_at.year),
    )

    message = schemas.KafkaMessage(
        topic="official.dispatch.status.update",
        payload=payload,
        key=f"dispatch_status_{dispatch.serial_number}",
    )

    await _publish_to_kafka_gateway(message)


async def _publish_to_kafka_gateway(message: schemas.KafkaMessage):
    """Sends the formatted message to the notification gateway service."""
    url = settings.NOTIFICATION_SERVICE_URL
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=message.model_dump(mode="json"))
            _ = response.raise_for_status()
            logger.info(
                f"Successfully published message with key '{message.key}' to topic '{message.topic}'."
            )
    except httpx.RequestError as e:
        logger.error(
            f"Failed to publish message to notification service at {url}. Error: {e}"
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred while publishing message: {e}")
