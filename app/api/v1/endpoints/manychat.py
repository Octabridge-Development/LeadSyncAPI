# app/api/v1/endpoints/manychat.py

from fastapi import APIRouter, status, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.schemas.manychat import ManyChatContactEvent, ManyChatCampaignAssignmentEvent
from app.services.queue_service import QueueService, QueueServiceError
from app.api.deps import get_queue_service, verify_api_key
from app.core.logging import logger

router = APIRouter(
    prefix="/manychat",
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
        await queue_service.send_event_to_queue(
            event.dict(),
            queue_name="manychat-contact-queue"
        )

        # Respuesta exitosa
        return {
            "status": "accepted",
            "message": "Evento de contacto encolado exitosamente",
            "manychat_id": event.manychat_id,
            "queue": "manychat-contact-queue"
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


@router.post(
    "/webhook/campaign-assignment",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Recibe asignaciones de campaña de ManyChat",
    response_description="Evento de campaña recibido y encolado para procesamiento asíncrono",
    responses={
        202: {
            "description": "Evento de campaña aceptado y encolado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "status": "accepted",
                        "message": "Evento de campaña encolado exitosamente",
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
        event: ManyChatCampaignAssignmentEvent,
        request: Request,
        api_key: str = Depends(verify_api_key),
        queue_service: QueueService = Depends(get_queue_service)
) -> Dict[str, Any]:
    """
    Recibe un evento de asignación de campaña desde ManyChat y lo encola para procesamiento.

    Este endpoint es llamado cuando:
    - Un lead es asignado a una campaña específica
    - Se asigna un asesor comercial o médico a un lead
    - Se actualiza el estado de asignación de un lead

    **Flujo del proceso:**
    1. ManyChat envía el evento cuando se asigna un lead a una campaña
    2. El evento se valida y se coloca en la cola `manychat-campaign-queue`
    3. Un worker procesa el evento verificando que el contacto exista
    4. Se crea o actualiza el registro en Campaign_Contact con los asesores asignados

    **Campos del evento:**
    - `manychat_id`: ID del contacto en ManyChat (debe existir previamente)
    - `campaign_id`: ID o nombre de la campaña
    - `comercial_id`: ID del asesor comercial asignado (opcional)
    - `medico_id`: ID del asesor médico asignado (opcional)
    - `datetime_actual`: Fecha/hora de la asignación
    - `ultimo_estado`: Estado actual del lead en la campaña
    - `tipo_asignacion`: Tipo de asignación (comercial/medico/both)

    **Importante:** El contacto debe existir antes de poder asignarlo a una campaña.
    Use el endpoint `/webhook/contact` primero si el contacto es nuevo.
    """
    try:
        # Log del evento recibido
        logger.info(
            "Evento de asignación de campaña recibido",
            manychat_id=event.manychat_id,
            campaign_id=event.campaign_id,
            comercial_id=event.comercial_id,
            tipo=event.tipo_asignacion
        )

        # Validaciones básicas
        if not event.manychat_id or not event.manychat_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="manychat_id no puede estar vacío"
            )

        if not event.campaign_id or not event.campaign_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="campaign_id no puede estar vacío"
            )

        # Enviar evento a la cola de campañas
        await queue_service.send_campaign_event_to_queue(event.dict())

        # Respuesta exitosa
        return {
            "status": "accepted",
            "message": "Evento de campaña encolado exitosamente",
            "manychat_id": event.manychat_id,
            "campaign_id": event.campaign_id,
            "queue": "manychat-campaign-queue"
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