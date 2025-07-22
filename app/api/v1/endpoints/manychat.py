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
    - `ultimo_estado`: Estado actual del lead
    - `canal_entrada`: Canal de origen (Facebook, WhatsApp, etc.)
    - `estado_inicial`: Estado inicial del contacto

    **Nota:** El campo `whatsapp` se mapea internamente al campo `phone` en la base de datos.
    """
    try:
        # Log del evento recibido
        logger.info(
            "Evento de contacto recibido",
            manychat_id=event.manychat_id,
            nombre=event.nombre_lead,
            estado=event.ultimo_estado,
            canal=event.canal_entrada
        )

        # Validar que el manychat_id no esté vacío
        if not event.manychat_id or not event.manychat_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="manychat_id no puede estar vacío"
            )

        # Enviar evento a la cola de contactos
        await queue_service.send_message(
            queue_name=queue_service.contact_queue_name,
            event_data=event.dict()
        )

        # Respuesta exitosa
        return {
            "status": "accepted",
            "message": "Evento de contacto encolado exitosamente",
            "manychat_id": event.manychat_id,
            "queue": queue_service.contact_queue_name
        }

    except QueueServiceError as e:
        logger.error(
            "Error al encolar evento de contacto",
            error=str(e),
            manychat_id=event.manychat_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el evento: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error inesperado procesando evento de contacto",
            error=str(e),
            manychat_id=event.manychat_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error inesperado al procesar el evento"
        )



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

@router.post(
    "/webhook/campaign-assignment",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Recibe asignaciones de campaña de ManyChat",
    response_description="Evento de campaña recibido, actualiza CampaignContact y ContactState, y encola para procesamiento asíncrono",
    responses={
        202: {
            "description": "Evento de campaña aceptado, CampaignContact actualizado y evento encolado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "status": "accepted",
                        "message": "CampaignContact actualizado y evento encolado exitosamente",
                        "manychat_id": "123456789",
                        "campaign_id": "campaign_verano_2024",
                        "queue": "manychat-campaign-queue"
                    }
                }
            }
        },
        400: {
            "description": "Datos inválidos en el evento",
            "content": {
                "application/json": {
                    "example": {"detail": "El contacto debe existir antes de asignar una campaña"}
                }
            }
        }
    }
)
async def receive_campaign_assignment(
    event: CampaignAssignmentEvent,
    request: Request,
    api_key: str = Depends(verify_api_key),
    queue_service: QueueService = Depends(get_queue_service),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Recibe un evento de asignación de campaña desde ManyChat, actualiza CampaignContact y ContactState, y encola el evento para procesamiento.
    """
    try:
        logger.info(
            "Evento de asignación de campaña recibido",
            manychat_id=event.manychat_id,
            campaign_id=event.campaign_id,
            comercial_id=event.comercial_id,
            tipo=event.tipo_asignacion,
            ultimo_estado=event.ultimo_estado,
            summary=event.summary
        )

        # Validaciones básicas
        if not event.manychat_id or not event.manychat_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="manychat_id no puede estar vacío"
            )
        if not event.campaign_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="campaign_id no puede estar vacío"
            )

        # Buscar contacto
        contact = db.query(Contact).filter(Contact.manychat_id == event.manychat_id).first()
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El contacto no existe, debe crearse primero"
            )

        # Buscar o crear CampaignContact
        campaign_contact = db.query(CampaignContact).filter(
            CampaignContact.contact_id == contact.id,
            CampaignContact.campaign_id == event.campaign_id
        ).first()
        if campaign_contact:
            # Actualizar campos relevantes
            if event.comercial_id:
                campaign_contact.commercial_advisor_id = event.comercial_id
            if event.medico_id:
                campaign_contact.medical_advisor_id = event.medico_id
            if event.ultimo_estado:
                campaign_contact.last_state = event.ultimo_estado
            if event.summary:
                campaign_contact.summary = event.summary
            campaign_contact.sync_status = "updated"
        else:
            campaign_contact = CampaignContact(
                contact_id=contact.id,
                campaign_id=event.campaign_id,
                commercial_advisor_id=event.comercial_id,
                medical_advisor_id=event.medico_id,
                last_state=event.ultimo_estado,
                summary=event.summary,
                sync_status="new"
            )
            db.add(campaign_contact)
        db.commit()

        # Actualizar ContactState
        if event.ultimo_estado:
            contact_state = ContactState(
                contact_id=contact.id,
                state=event.ultimo_estado,
                category="manychat"
            )
            db.add(contact_state)
            db.commit()

        # Encolar el evento para el worker
        await queue_service.send_message(
            queue_name=queue_service.campaign_queue_name,
            event_data=event.dict()
        )

        return {
            "status": "accepted",
            "message": "CampaignContact actualizado y evento encolado exitosamente",
            "manychat_id": event.manychat_id,
            "campaign_id": event.campaign_id,
            "queue": queue_service.campaign_queue_name
        }

    except QueueServiceError as e:
        logger.error(
            "Error al encolar evento de campaña",
            error=str(e),
            manychat_id=event.manychat_id,
            campaign_id=event.campaign_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el evento: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error inesperado procesando evento de campaña",
            error=str(e),
            manychat_id=event.manychat_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error inesperado al procesar el evento"
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

