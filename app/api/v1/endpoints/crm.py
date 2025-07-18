# app/api/v1/endpoints/crm.py

from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from typing import Annotated


from app.schemas.crm import CRMLeadEvent, CRMLeadResponse # Importamos los esquemas que creaste
from app.services.queue_service import queue_service # Importamos el servicio de colas de Felipe
from app.core.config import get_settings

# Router específico para CRM
router = APIRouter(
    prefix="/crm", #
    tags=["CRM"] #
)


# Obtener la API Key desde la configuración
settings = get_settings()
EXPECTED_API_KEY = settings.API_KEY

# Dependencia para verificar la API Key
async def verify_api_key(x_api_key: Annotated[str, Header()]):
    if x_api_key != EXPECTED_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

@router.post(
    "/webhook/lead", #
    response_model=CRMLeadResponse,
    summary="Recibe y encola eventos de leads desde ManyChat"
)
async def receive_lead_event(
    event: CRMLeadEvent, # FastAPI valida el body usando tu esquema
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key) # Seguridad de API Key
):
    """
    Endpoint para recibir un evento de CRM, validarlo y encolarlo para procesamiento asíncrono.
    """
    # La validación de 'sequence' entre 0-10 ya la hace Pydantic en el schema.
    
    # 1. Encolado asíncrono del evento
    background_tasks.add_task(
        queue_service.send_message,
        queue_name="manychat-crm-queue", #
        event_data=event.model_dump()  # <-- ahora pasa un dict, no un string
    )

    # 2. Responder inmediatamente al cliente
    return {
        "status": "enqueued", #
        "message": "Lead event received and queued for processing.",
        "manychat_id": event.manychat_id
    }

@router.get(
    "/lead/{manychat_id}", #
    summary="Consulta un lead por su ManyChat ID"
)
async def get_lead(manychat_id: str, api_key: str = Depends(verify_api_key)):
    """
    Consulta la información de un lead directamente en Odoo. (Ejemplo de uso)
    """
    # Esta es una función de ejemplo, la lógica real de Odoo fue eliminada
    lead_info = None
    if not lead_info:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead_info