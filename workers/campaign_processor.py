"""
Worker: campaign_processor.py

Este worker consume mensajes de la cola de campañas de ManyChat en Azure Storage Queue y procesa eventos de asignación de campaña.

- Desacopla el flujo de asignación de campañas para escalabilidad y resiliencia.
- Procesa mensajes en lotes, respeta la visibilidad y elimina los mensajes procesados.
- Llama a AzureSQLService para registrar la asignación en la base de datos.
- Maneja errores y registra logs estructurados.

Uso:
    python -m workers.campaign_processor

Ejemplo de mensaje esperado en la cola:
    {
        "manychat_id": "123456",
        "campaign_id": "camp-789",
        "comercial_id": "advisor-001",
        "datetime_actual": "2024-05-27T12:34:56Z",
        "ultimo_estado": "asignado",
        "tipo_asignacion": "manual"
    }
"""
import asyncio
import json
from app.services.queue_service import QueueService, QueueServiceError
from app.services.azure_sql_service import AzureSQLService
from app.schemas.manychat import ManyChatCampaignAssignmentEvent
from app.core.logging import logger

def _log_start():
    logger.info("Worker de campaña iniciado. Esperando mensajes...")

async def process_campaign_messages():
    """
    Consume mensajes de la cola de campañas y procesa eventos de asignación de campaña.

    - Lee mensajes en lotes de la cola 'manychat-campaign-queue'.
    - Convierte el contenido a ManyChatCampaignAssignmentEvent.
    - Llama a AzureSQLService para procesar el evento.
    - Elimina el mensaje de la cola si se procesa correctamente.
    - Registra errores y continúa el procesamiento.

    Corre en bucle infinito con un pequeño delay entre iteraciones.
    """
    queue_service = QueueService()
    azure_sql_service = AzureSQLService()
    queue_client = queue_service.client.get_queue_client(queue_service.campaign_queue_name)
    _log_start()
    while True:
        messages = queue_client.receive_messages(messages_per_page=10, visibility_timeout=30)
        for msg_batch in messages.by_page():
            for msg in msg_batch:
                try:
                    event_data = json.loads(msg.content)
                    event = ManyChatCampaignAssignmentEvent(**event_data)
                    await azure_sql_service.process_campaign_event(event)
                    queue_client.delete_message(msg)
                    logger.info("Mensaje de campaña procesado y eliminado", manychat_id=event.manychat_id)
                except Exception as e:
                    logger.error("Error procesando mensaje de campaña", error=str(e), raw=msg.content)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(process_campaign_messages())
