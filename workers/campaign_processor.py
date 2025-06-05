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
from datetime import datetime, timezone
from app.services.queue_service import QueueService, QueueServiceError
from app.services.azure_sql_service import AzureSQLService
from app.schemas.manychat import ManyChatCampaignAssignmentEvent
from app.core.logging import logger

def _log_start():
    logger.info("Worker de campaña iniciado. Esperando mensajes...")

async def process_campaign_messages():
    """
    Worker para procesar eventos de campañas desde la cola manychat-campaign-queue.
    - Procesa mensajes en lotes.
    - Llama a AzureSQLService.process_campaign_event().
    - Maneja errores y envía a DLQ.
    """
    queue_service = QueueService()
    azure_sql_service = AzureSQLService()
    await queue_service._ensure_queues_exist()
    _log_start()
    while True:
        try:
            queue_client = queue_service._get_queue_client(queue_service.campaign_queue_name)
            messages = queue_client.receive_messages(messages_per_page=10, visibility_timeout=30)
            async for msg_batch in messages.by_page():
                async for msg in msg_batch:
                    try:
                        event_data = json.loads(msg.content)
                        event = ManyChatCampaignAssignmentEvent(**event_data)
                        await azure_sql_service.process_campaign_event(event)
                        await queue_client.delete_message(msg)
                        logger.info(f"Mensaje de campaña procesado y eliminado", extra={"manychat_id": event.manychat_id})
                    except json.JSONDecodeError as e:
                        logger.error(f"Error al decodificar JSON del mensaje: {e}. Contenido: {msg.content}")
                        error_payload = {
                            "error_type": "JSONDecodeError",
                            "error_message": str(e),
                            "original_message": msg.content,
                            "timestamp": str(datetime.now(timezone.utc))
                        }
                        await queue_service.send_message(error_payload, queue_service.dlq_name)
                        logger.warning(f"Mensaje inválido movido a DLQ.")
                        await queue_client.delete_message(msg)
                    except Exception as e:
                        logger.error(f"Error procesando mensaje de campaña: {str(e)}", exc_info=True)
                        error_payload = {
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "original_message": msg.content,
                            "timestamp": str(datetime.now(timezone.utc))
                        }
                        await queue_service.send_message(error_payload, queue_service.dlq_name)
                        logger.warning(f"Mensaje movido a DLQ por error de procesamiento.")
                        await queue_client.delete_message(msg)
            await asyncio.sleep(2)
        except QueueServiceError as e:
            logger.error(f"Error de QueueService en el worker: {str(e)}", exc_info=True)
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Error inesperado en el loop principal del worker: {str(e)}", exc_info=True)
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(process_campaign_messages())
