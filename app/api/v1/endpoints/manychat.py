# app/api/v1/endpoints/manychat.py (VERSIÓN CORREGIDA)

from fastapi import APIRouter, status, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.schemas.manychat import ManyChatContactEvent, ManyChatCampaignAssignmentEvent
from pydantic import BaseModel, Field

from app.services.queue_service import QueueService, QueueServiceError
from app.api.deps import get_queue_service, verify_api_key
from app.core.logging import logger
from app.db.session import get_db

router = APIRouter(
    tags=["ManyChat Webhooks"],
    responses={
        401: {
            "description": "No autorizado - API Key inválido o faltante",
            "content": {
                "application/json": {
                    "example": {"detail": "X-API-KEY header requerido"}
                }
            }
        },
        500: {
            "description": "Error interno del servidor",
            "content": {
                "application/json": {
                    "example": {"error": "Error al procesar el evento"}
                }
            }
        }
    }
)


@router.post(
    "/webhook/contact",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Recibe eventos de contacto de ManyChat",
    response_description="Evento recibido y encolado para procesamiento asíncrono",
    responses={
        202: {
            "description": "Evento aceptado y encolado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "status": "accepted",
                        "message": "Evento de contacto encolado exitosamente",
                        "manychat_id": "123456789",
                        "queue": "manychat-contact-queue"
                    }
                }
            }
        },
        400: {
            "description": "Datos inválidos en el evento",
            "content": {
                "application/json": {
                    "example": {"detail": "Formato de evento inválido"}
                }
            }
        }
    }
)
async def receive_contact_event(
        event: ManyChatContactEvent,
        request: Request,
        api_key: str = Depends(verify_api_key),
        queue_service: QueueService = Depends(get_queue_service)
) -> Dict[str, Any]:
    """
    Recibe un evento de contacto desde ManyChat y lo encola para procesamiento asíncrono.

    Este endpoint es llamado por ManyChat cuando:
    - Un nuevo usuario se suscribe al bot
    - Se actualiza información de un contacto existente
    - Un usuario interactúa por primera vez

    **Flujo del proceso:**
    1. ManyChat envía el evento a este endpoint
    2. El evento se valida y se coloca en la cola `manychat-contact-queue`
    3. Un worker procesa el evento de forma asíncrona
    4. Los datos se sincronizan con Azure SQL y Odoo

    **Campos del evento:**
    - `manychat_id`: ID único del usuario en ManyChat
    - `nombre_lead`: Nombre del contacto
    - `apellido_lead`: Apellido del contacto (opcional)
    - `whatsapp`: Número de WhatsApp (se mapea a phone en la BD)
    - `datetime_suscripcion`: Fecha/hora de suscripción inicial
    - `datetime_actual`: Fecha/hora del evento actual
    - `canal_entrada`: Canal de origen (Facebook, WhatsApp, etc.)
    - `estado_inicial`: Estado inicial del contacto

    **Nota:** El campo `whatsapp` se mapea internamente al campo `phone` en la base de datos.
    """
    # Solo encolar el evento en la cola de contactos
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



from app.db.session import get_db
from sqlalchemy.orm import Session
from app.db.models import Contact, CampaignContact
from app.db.models import ContactState


# Nuevo esquema para el endpoint de campaign-assignment, alineado con ContactState y CRM
class CampaignAssignmentEvent(BaseModel):
    manychat_id: str = Field(...)
    campaign_id: int = Field(...)
    comercial_id: str | None = None
    medico_id: str | None = None
    datetime_actual: str | None = None
    ultimo_estado: str = Field(...)
    tipo_asignacion: str = Field(...)
    summary: str | None = None


# Nuevo endpoint unificado para asignación de campaña y asesores
from app.schemas.campaign_contact import CampaignContactUpsert
from app.api.v1.endpoints.campaign_contact import assign_campaign_and_state
from fastapi import Request
from sqlalchemy.orm import Session

# Nueva función para respuesta personalizada
async def assign_campaign_and_state_response(
    data: CampaignContactUpsert,
    request: Request,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    result = await assign_campaign_and_state(data, request, db)
    return {
        "status": "accepted",
        "message": "Asignación encolada correctamente",
        "manychat_id": data.manychat_id,
        "queue": "manychat-campaign-queue"
    }

# Registrar el endpoint en el router de ManyChat Webhooks
router.add_api_route(
    "/webhook/campaign-contact-assign",
    assign_campaign_and_state_response,
    methods=["POST"],
    summary="Asignar campaña y asesores (ManyChat → API → Cola → Worker → Odoo)",
    response_model=None,
    tags=["ManyChat Webhooks"]
)

# Endpoint de verificación para ManyChat
@router.get(
    "/webhook/verify",
    summary="Verificación del webhook",
    description="Endpoint usado por ManyChat para verificar que el webhook está activo",
    responses={
        200: {
            "description": "Webhook activo y funcionando",
            "content": {
                "application/json": {
                    "example": {
                        "status": "active",
                        "service": "MiaSalud Integration API",
                        "endpoints": [
                            "/api/v1/manychat/webhook/contact",
                            "/api/v1/manychat/webhook/campaign-assignment"
                        ]
                    }
                }
            }
        }
    }
)
async def verify_webhook(
        api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Endpoint de verificación para confirmar que el webhook está activo.

    ManyChat puede usar este endpoint para verificar que la integración está funcionando
    antes de enviar eventos reales.
    """
    return {
        "status": "active",
        "service": "MiaSalud Integration API",
        "endpoints": [
            "/api/v1/manychat/webhook/contact",
            "/api/v1/manychat/webhook/campaign-assignment"
        ]
    }


# --- ¡INICIA EL NUEVO ENDPOINT PUT AQUÍ! ---
@router.put(
    "/campaign-contacts/update-by-manychat-id",
    summary="Actualizar Campaign_Contact por ManyChat ID",
    description="""
    Actualiza un registro de Campaign_Contact asociado a un Contacto
    usando su ManyChat ID. Permite actualizar el ID del asesor médico,
    la fecha de asignación del médico y el último estado.
    Este endpoint se ejecuta de manera SÍNCRONA con la base de datos.
    """,
    # response_model eliminado: CampaignContactUpdate,
    status_code=status.HTTP_200_OK,
    tags=["ManyChat"],
)

def _build_update_kwargs(campaign_contact_data) -> dict:
    """
    Construye el diccionario de campos a actualizar para CampaignContact a partir de los datos recibidos.
    """
    fields_set = getattr(campaign_contact_data, 'model_fields_set', set())
    update_kwargs = {}
    for field in ["campaign_id", "medical_advisor_id", "medical_assignment_date", "last_state", "summary"]:
        if field in fields_set and hasattr(campaign_contact_data, field):
            value = getattr(campaign_contact_data, field, None)
            if value is not None:
                update_kwargs[field] = value
    update_kwargs["manychat_id"] = campaign_contact_data.manychat_id
    return update_kwargs

def update_campaign_contact_endpoint(
    campaign_contact_data,
    db: 'Session' = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Endpoint para actualizar campos específicos de un registro de Campaign_Contact.
    """
    logger.info(f"Recibida solicitud PUT para actualizar CampaignContact. Data: {campaign_contact_data.model_dump_json()}")
    try:
        update_kwargs = _build_update_kwargs(campaign_contact_data)
        # updated_campaign_contact_obj = service.update_campaign_contact_by_manychat_id(**update_kwargs)  # Eliminado: servicio no disponible
        logger.warning(f"Funcionalidad de actualización de CampaignContact no disponible para ManyChat ID: {campaign_contact_data.manychat_id}")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Funcionalidad de actualización de CampaignContact no disponible."
        )
    except ValueError as ve:
        logger.error(f"Error de validación en la solicitud PUT: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Error inesperado en el endpoint PUT /campaign-contacts/update-by-manychat-id: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al procesar la solicitud de actualización."
        )

