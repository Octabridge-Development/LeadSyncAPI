# workers/contact_processor.py
import asyncio
import json
import logging

from app.services.queue_service import QueueService
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
            message = await queue_service.receive_message("manychat-contact-queue")
            if message:
                logger.info(f"Mensaje recibido de la cola de contactos. ID: {message.id}")

                event_data = json.loads(message.content)
                event = ManyChatContactEvent(**event_data)

                result = await sql_service.process_contact_event(event)

                logger.info(f"Evento de contacto procesado exitosamente: {result}")

                await queue_service.delete_message(message)
                logger.info(f"Mensaje eliminado de la cola. ID: {message.id}")

            else:
                await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Error critico en el worker de contactos: {str(e)}", exc_info=True)
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(process_contact_events())