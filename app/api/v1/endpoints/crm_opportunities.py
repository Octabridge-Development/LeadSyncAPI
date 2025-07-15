# app/api/v1/endpoints/crm_opportunities.py

from fastapi import APIRouter, Depends, HTTPException, status
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
    queue_service: QueueService = Depends(QueueService) # Inyecta tu servicio de colas
):
    """
    Recibe los cambios de stage desde ManyChat, valida y encola para procesamiento CRM.
    """
    print(f"Webhook de ManyChat recibido para ID: {payload.manychat_id}, Stage: {payload.stage_manychat}")

    # **Validación y Mapeo de Stage ManyChat -> Odoo ID (Parte de la Tarea B1)**
    # Este mapeo ya está definido en app/schemas/crm_opportunity.py
    # Pero para la validación previa en el endpoint, lo traemos aquí de nuevo o lo referenciamos.
    # Es más robusto que la lógica de mapeo esté en un solo lugar.
    # Para simplicidad y para resolver tu error, lo usaremos directamente de CRMOpportunityEvent.

    # Obtener el stage_odoo_id usando la propiedad del modelo
    crm_event_draft = CRMOpportunityEvent( # Creación de una instancia temporal para obtener el ID
        manychat_id=payload.manychat_id,
        stage_manychat=payload.stage_manychat,
        datetime_stage_change=datetime.now(), # Se asigna aquí temporalmente, se sobrescribirá si se encola
        advisor_id=payload.advisor_id
    )

    stage_odoo_id = crm_event_draft.stage_odoo_id

    if stage_odoo_id is None:
        print(f"Advertencia: Stage de ManyChat '{payload.stage_manychat}' no tiene mapeo a Odoo. Lanzando error 400.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stage de ManyChat '{payload.stage_manychat}' no reconocido. Por favor, asegúrese de que el stage tenga un mapeo válido a Odoo CRM."
        )

    # Crear el evento de oportunidad CRM final
    crm_opportunity_event = CRMOpportunityEvent(
        manychat_id=payload.manychat_id,
        stage_manychat=payload.stage_manychat,
        # stage_odoo_id ya no se pasa directamente, se calcula internamente por la propiedad.
        datetime_stage_change=datetime.now(),
        advisor_id=payload.advisor_id
    )

    # **Encolado en nueva cola manychat-crm-opportunities-queue (Parte de la Tarea B1)**
    # Asegúrate de que 'crm_opportunities_queue_name' sea la constante correcta que definirás en el servicio de colas.
    try:
        # Usamos .model_dump_json() para Pydantic v2. Si usas Pydantic v1, sería .json()
        await queue_service.send_message(
            queue_name=queue_service.CRM_OPPORTUNITIES_QUEUE_NAME, # Usar la constante definida en QueueService
            message_body=crm_opportunity_event.model_dump_json()
        )
        print(f"Evento de CRM para ManyChat ID {payload.manychat_id} encolado con éxito en '{queue_service.CRM_OPPORTUNITIES_QUEUE_NAME}'.")
    except Exception as e:
        print(f"Error al encolar el evento CRM: {e}")
        # Loguear el error completo para depuración, pero no exponerlo al cliente.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al procesar el cambio de stage."
        )

    return {"message": "Webhook recibido y procesado para encolar.", "manychat_id": payload.manychat_id}