# app/api/v1/endpoints/manychat.py

from fastapi import APIRouter, status, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
from sqlalchemy.orm import Session

# --- Importaciones de Esquemas ---
# Se importan todos los esquemas necesarios, incluido el nuevo para direcciones.
from app.schemas.manychat import ManyChatContactEvent, ManyChatCampaignAssignmentEvent, ManyChatAddressEvent
from app.schemas.campaign_contact import CampaignContactUpsert

# --- Importaciones de Servicios y Dependencias ---
from app.services.queue_service import QueueService
from app.api.deps import get_queue_service, verify_api_key, get_db
from app.core.logging import logger

# --- Importación de otros endpoints si es necesario (ejemplo) ---
# Si la lógica está en otro archivo, como parece ser tu caso con 'assign_campaign_and_state'.
from app.api.v1.endpoints.campaign_contact import assign_campaign_and_state

# --- Definición del Router ---
router = APIRouter(
    tags=["ManyChat Webhooks"],
    responses={
        401: {"description": "No autorizado - API Key inválido o faltante"},
        500: {"description": "Error interno del servidor"},
    }
)

# --- Endpoint para Eventos de Contacto ---
@router.post(
    "/webhook/contact",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Recibe eventos de contacto de ManyChat",
    response_description="Evento recibido y encolado para procesamiento asíncrono",
)
async def receive_contact_event(
        event: ManyChatContactEvent,
        request: Request,
        api_key: str = Depends(verify_api_key),
        queue_service: QueueService = Depends(get_queue_service)
) -> Dict[str, Any]:
    """
    Recibe un evento de contacto desde ManyChat y lo encola para procesamiento asíncrono.
    """
    logger.info(
        "Evento de contacto recibido",
        manychat_id=event.manychat_id,
        nombre=event.nombre_lead,
        estado=event.estado_inicial,
        canal=event.canal_entrada
    )
    if not event.manychat_id or not event.manychat_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="manychat_id no puede estar vacío"
        )
    
    event_data = event.dict()
    await queue_service.send_message(
        queue_name=queue_service.contact_queue_name,
        event_data=event_data
    )
    
    return {
        "status": "accepted",
        "message": "Evento de contacto encolado exitosamente",
        "manychat_id": event.manychat_id,
        "queue": queue_service.contact_queue_name
    }

# --- 🚀 NUEVO ENDPOINT PARA DIRECCIONES 🚀 ---
@router.post(
    "/webhook/address",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Recibe una dirección de contacto de ManyChat",
    response_description="Evento de dirección recibido y encolado para procesamiento."
)
async def receive_address_event(
    event: ManyChatAddressEvent,
    request: Request,
    api_key: str = Depends(verify_api_key),
    queue_service: QueueService = Depends(get_queue_service)
) -> Dict[str, Any]:
    """
    Recibe un evento con la dirección de un contacto desde ManyChat y lo encola 
    para ser añadido al contacto correspondiente en la base de datos.

    **Flujo del proceso:**
    1. ManyChat envía los datos de la dirección a este endpoint.
    2. El evento se valida con el esquema `ManyChatAddressEvent`.
    3. Se coloca en la cola `manychat-address-queue`.
    4. Un worker procesará el evento de forma asíncrona.
    """
    logger.info(
        "Evento de dirección recibido",
        manychat_id=event.manychat_id,
        street=event.street,
        district=event.district,
        city=event.city,
        state=event.state,
        country=event.country
    )
    if not event.manychat_id or not event.manychat_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="manychat_id no puede estar vacío"
        )
    # Validar que al menos uno de los campos de dirección esté presente
    if not any([
        event.street, event.district, event.city, event.state, event.country
    ]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe enviarse al menos un campo de dirección (street, district, city, state o country)"
        )

    # Asegúrate de que tu QueueService tenga definido 'address_queue_name'.
    # Por ejemplo, en app/services/queue_service.py:
    # self.address_queue_name = "manychat-address-queue"
    if not hasattr(queue_service, 'address_queue_name'):
         raise HTTPException(
            status_code=500, 
            detail="La cola para direcciones no está configurada en QueueService."
        )

    event_data = event.dict()
    await queue_service.send_message(
        queue_name=queue_service.address_queue_name,
        event_data=event_data
    )
    
    return {
        "status": "accepted",
        "message": "Evento de dirección encolado exitosamente",
        "manychat_id": event.manychat_id,
        "queue": queue_service.address_queue_name
    }

# --- Endpoint para Asignación de Campaña ---
# Esta es una forma de registrar una ruta que llama a una función de otro módulo.
router.add_api_route(
    "/webhook/campaign-contact-assign",
    assign_campaign_and_state, # Llama a la función importada
    methods=["POST"],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Asignar campaña y asesores (ManyChat → API → Cola)",
    tags=["ManyChat Webhooks"]
)

# --- Endpoint de Verificación para ManyChat ---
@router.get(
    "/webhook/verify",
    summary="Verificación del webhook",
    description="Endpoint usado por ManyChat para verificar que el webhook está activo",
)
async def verify_webhook(
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Endpoint de verificación para confirmar que el webhook está activo.
    """
    return {
        "status": "active",
        "service": "MiaSalud Integration API",
        "endpoints": [
            "/api/v1/manychat/webhook/contact",
            "/api/v1/manychat/webhook/address", # Añadido el nuevo endpoint
            "/api/v1/manychat/webhook/campaign-contact-assign"
        ]
    }

# --- Endpoint PUT para Actualizaciones Síncronas (Existente) ---
# Mantengo este endpoint como lo tenías, aunque parece que no estaba completamente implementado.
@router.put(
    "/campaign-contacts/update-by-manychat-id",
    summary="Actualizar Campaign_Contact por ManyChat ID (Síncrono)",
    status_code=status.HTTP_501_NOT_IMPLEMENTED, # Marcado como no implementado
    tags=["ManyChat"],
)
def update_campaign_contact_endpoint(
    # La firma de esta función puede necesitar un esquema Pydantic en el body
    # campaign_contact_data: CampaignContactUpdate, 
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Endpoint para actualizar campos específicos de un registro de Campaign_Contact.
    NOTA: La lógica de servicio para esta operación no está implementada.
    """
    # logger.info(f"Recibida solicitud PUT. Data: {campaign_contact_data.model_dump_json()}")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Funcionalidad de actualización síncrona de CampaignContact no disponible."
    )
