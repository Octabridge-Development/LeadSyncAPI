# app/api/v1/endpoints/crm_opportunities.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.repositories import ContactRepository, ContactStateRepository
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# Asume que tendrás un servicio de colas y un mapeo de stages.
# Reemplaza 'your_queue_service' con el nombre real de tu módulo de servicio de colas.
from app.services.queue_service import QueueService # <-- Importación corregida del servicio de colas
from app.schemas.crm_opportunity import CRMOpportunityEvent # <-- Esta importación es la del esquema que acabas de revisar

router = APIRouter()

# Define el schema para el payload del webhook de ManyChat
class ManyChatStageChangeWebhook(BaseModel):
    manychat_id: str = Field(..., description="ID del contacto de ManyChat")
    stage_manychat: str = Field(..., description="Stage actual de ManyChat")
    advisor_id: Optional[str] = Field(None, description="ID del asesor (opcional)")
    # Puedes añadir más campos si el webhook de ManyChat los envía y son relevantes


@router.post("/crm/webhook/stage-change", status_code=status.HTTP_202_ACCEPTED)
async def handle_manychat_stage_change(
    payload: ManyChatStageChangeWebhook,
):
    """
    Recibe los cambios de stage desde ManyChat y guarda el estado en Contact_State y encola el evento para el worker CRM.
    """
    print(f"Webhook de ManyChat recibido para ID: {payload.manychat_id}, Stage: {payload.stage_manychat}")
    db: Session = SessionLocal()
    contact_repo = ContactRepository(db)
    contact_state_repo = ContactStateRepository(db)
    queue_service = QueueService()
    try:
        contact = contact_repo.get_by_manychat_id(payload.manychat_id)
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró un contacto con manychat_id={payload.manychat_id}"
            )
        # Guardar el nuevo estado en Contact_State
        contact_state = contact_state_repo.create_or_update(
            contact_id=contact.id,
            state=payload.stage_manychat,
            category="manychat"
        )
        # Actualizar odoo_sync_status a 'pending' para que el worker procese la sincronización
        contact_repo.update_odoo_sync_status(payload.manychat_id, "pending")
        # Enviar evento a la cola para el worker CRM
        event = {
            "manychat_id": payload.manychat_id,
            "stage_manychat": payload.stage_manychat,
            "advisor_id": payload.advisor_id,
            "contact_id": contact.id,
            "contact_state_id": contact_state.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await queue_service.send_message("manychat-crm-opportunities-queue", event)
        print(f"Evento encolado en manychat-crm-opportunities-queue: {event}")
        return {"message": "Stage guardado/actualizado en Contact_State y evento encolado para CRM", "contact_state_id": contact_state.id, "manychat_id": payload.manychat_id}
    finally:
        db.close()