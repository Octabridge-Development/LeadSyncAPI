from fastapi import APIRouter, Depends, HTTPException
from app.schemas.manychat import ManyChatWebhookEvent
from app.core.security import verify_manychat_api_key
from app.services.queue_service import QueueService

router = APIRouter()

def get_queue_service():
    return QueueService()

@router.post("/webhook/manychat")
async def receive_manychat_webhook(
    event: ManyChatWebhookEvent,
    api_key: str = Depends(verify_manychat_api_key),
    queue_service: QueueService = Depends(get_queue_service)
):
    # Enviar evento a la cola de Azure
    await queue_service.send_event_to_queue(event.dict())
    return {"status": "queued", "manychat_id": event.manychat_id}