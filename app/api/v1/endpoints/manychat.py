from fastapi import APIRouter, status, Depends, Request
from fastapi.responses import JSONResponse
from app.schemas.manychat import ManyChatContactEvent, ManyChatCampaignAssignmentEvent
from app.services.queue_service import QueueService, QueueServiceError
from app.utils.idempotency import check_idempotency
from app.utils.monitoring import monitor_event

router = APIRouter()

@router.post(
    "/webhook/manychat/contact-event",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Recibe eventos de contacto de ManyChat",
    response_description="Evento recibido y encolado para procesamiento asíncrono",
    tags=["ManyChat"],
)
async def manychat_contact_event(
    event: ManyChatContactEvent,
    request: Request,
    queue_service: QueueService = Depends(QueueService),
):
    """
    Recibe un evento de contacto desde ManyChat y lo encola para procesamiento asíncrono.

    Args:
        event (ManyChatContactEvent): Objeto con los datos del evento de contacto.
        request (Request): Objeto de la petición HTTP.
        queue_service (QueueService): Servicio de colas inyectado por FastAPI.

    Returns:
        JSONResponse: Mensaje de éxito o error.

    Respuestas:
        202: Evento recibido y encolado exitosamente
        400: Error de validación o idempotencia
        500: Error interno al encolar
    """
    # Ejemplo de request body (solo para documentación, no incluir en OpenAPI):
    # {
    #     "manychat_id": "123456",
    #     "contact": {
    #         "id": "abc-123",
    #         "name": "Juan Perez",
    #         "email": "juan@example.com"
    #     },
    #     "event_type": "contact_created",
    #     "timestamp": "2024-05-27T12:34:56Z"
    # }
    try:
        # Enviar evento a la cola de Azure
        await queue_service.send_event_to_queue(event.dict())
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"message": "Evento recibido y encolado exitosamente"}
        )
    except QueueServiceError as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )

@router.post(
    "/webhook/manychat/campaign-assignment",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Recibe asignaciones de campaña de ManyChat",
    response_description="Evento de campaña recibido y encolado para procesamiento asíncrono",
    tags=["ManyChat"],
)
async def manychat_campaign_assignment(
    event: ManyChatCampaignAssignmentEvent,
    request: Request,
    queue_service: QueueService = Depends(QueueService),
):
    """
    Recibe un evento de asignación de campaña desde ManyChat y lo encola en la cola de campañas.

    Args:
        event (ManyChatCampaignAssignmentEvent): Objeto con los datos del evento de campaña.
        request (Request): Objeto de la petición HTTP.
        queue_service (QueueService): Servicio de colas inyectado por FastAPI.

    Returns:
        JSONResponse: Mensaje de éxito o error.

    Respuestas:
        202: Evento de campaña recibido y encolado exitosamente
        400: Error de validación o idempotencia
        500: Error interno al encolar
    """
    # Ejemplo de request body (solo para documentación, no incluir en OpenAPI):
    # {
    #     "manychat_id": "123456",
    #     "campaign_id": "camp-789",
    #     "assigned_to": "advisor-001",
    #     "timestamp": "2024-05-27T12:34:56Z"
    # }
    try:
        # Enviar evento a la cola de campañas
        await queue_service.send_campaign_event_to_queue(event.dict())
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"message": "Evento de campaña recibido y encolado exitosamente"}
        )
    except QueueServiceError as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )