import asyncio
import json
import logging # Aunque usas app.core.logging, mantengo esta importación como en tu código original

from app.services.queue_service import QueueService, QueueServiceError # Importa QueueServiceError también
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

    logger.info("Worker de contactos iniciado. Escuchando 'manychat-contact-queue'...")

    while True:
        try:
            # Recibir un mensaje de la cola de contactos
            # Usamos queue_service.contact_queue_name para asegurar consistencia
            message = await queue_service.receive_message(queue_service.contact_queue_name)
            
            if message:
                logger.info(f"Mensaje recibido de la cola de contactos. ID: {message.id}")

                event_data = json.loads(message.content)
                event = ManyChatContactEvent(**event_data)

                logger.info(f"Procesando evento de contacto para ManyChat ID: {event.manychat_id}")

                result = await sql_service.process_contact_event(event)

                logger.info(f"Evento de contacto procesado exitosamente: {result}")

                # --- LÍNEA CORREGIDA ---
                # Debemos pasar el nombre de la cola, el ID del mensaje y el pop_receipt
                queue_service.delete_message(
                    queue_name=queue_service.contact_queue_name, 
                    message_id=message.id, 
                    pop_receipt=message.pop_receipt
                )
                logger.info(f"Mensaje eliminado de la cola. ID: {message.id}")

            else:
                await asyncio.sleep(5) # Espera si no hay mensajes

        except QueueServiceError as e: # Captura errores específicos de QueueService
            logger.error(f"Error relacionado con la cola en el worker de contactos: {str(e)}", exc_info=True)
            # En caso de error de cola, puedes decidir si esperar más o enviar a DLQ si aplica
            await asyncio.sleep(60) # Espera un minuto antes de reintentar para evitar spam de errores
        except Exception as e:
            logger.error(f"Error inesperado en el worker de contactos: {str(e)}", exc_info=True)
            await asyncio.sleep(10) # Espera más tiempo en caso de error

if __name__ == "__main__":
    asyncio.run(process_contact_events())