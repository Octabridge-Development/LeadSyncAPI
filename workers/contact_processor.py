# workers/contact_processor.py
import asyncio
import json
import logging
from datetime import datetime, timezone

from app.services.queue_service import QueueService, QueueServiceError
from app.services.azure_sql_service import AzureSQLService
from app.schemas.manychat import ManyChatContactEvent
from app.core.logging import logger

async def process_contact_events():
    """
    Worker para procesar eventos de contacto desde la cola.
    Escucha 'manychat-contact-queue' y procesa usando AzureSQLService.
    """
    queue_service = QueueService()
    sql_service = AzureSQLService()

    # CAMBIO: Llamar a _ensure_queues_exist de forma asíncrona aquí
    await queue_service._ensure_queues_exist() # AGREGAR ESTA LÍNEA

    logger.info("Worker de contactos iniciado. Escuchando 'manychat-contact-queue'...")

    while True:
        try:
            message = await queue_service.receive_message(queue_service.contact_queue_name)

            if message:
                message_id = message.id
                pop_receipt = message.pop_receipt
                message_content = message.content

                logger.info(f"Mensaje recibido de la cola de contactos. ID: {message_id}")

                try:
                    event_data = json.loads(message_content)
                    event = ManyChatContactEvent(**event_data)

                    result = await sql_service.process_contact_event(event)
                    logger.info(f"Evento de contacto procesado exitosamente: {result}")

                    await queue_service.delete_message(queue_service.contact_queue_name, message_id, pop_receipt)
                    logger.info(f"Mensaje eliminado de la cola. ID: {message_id}")

                except json.JSONDecodeError as e:
                    logger.error(f"Error al decodificar JSON del mensaje (ID: {message_id}): {e}. Contenido: {message_content}")
                    error_payload = {
                        "error_type": "JSONDecodeError",
                        "error_message": str(e),
                        "original_message": message_content,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await queue_service.send_message(error_payload, queue_service.dlq_name)
                    logger.warning(f"Mensaje inválido (ID: {message_id}) movido a DLQ.")
                    await queue_service.delete_message(queue_service.contact_queue_name, message_id, pop_receipt)

                except Exception as e:
                    logger.error(f"Error al procesar evento de contacto (ID: {message_id}): {str(e)}", exc_info=True)
                    error_payload = {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "original_message": message_content,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await queue_service.send_message(error_payload, queue_service.dlq_name)
                    logger.warning(f"Mensaje (ID: {message_id}) movido a DLQ por error de procesamiento.")
                    await queue_service.delete_message(queue_service.contact_queue_name, message_id, pop_receipt)

            else:
                await asyncio.sleep(5)

        except QueueServiceError as e:
            logger.error(f"Error de QueueService en el worker: {str(e)}", exc_info=True)
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Error inesperado en el loop principal del worker: {str(e)}", exc_info=True)
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(process_contact_events())