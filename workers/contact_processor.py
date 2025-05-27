# workers/contact_processor.py
# Este worker se encarga de procesar los eventos de contacto desde la cola.

import asyncio
import json
import logging
from app.services.queue_service import QueueService
from app.services.azure_sql_service import AzureSQLService
from app.schemas.manychat import ManyChatContactEvent
# Asume que tienes un logger configurado en app/core/logging.py
from app.core.logging import logger

# Configuración del logger para este worker
# logger = logging.getLogger(__name__) # Si no se usa el logger centralizado

async def process_contact_events():
    """
    Función principal del worker para procesar eventos de contacto.
    Escucha la cola 'manychat-contact-queue', procesa los mensajes
    y los envía al servicio AzureSQLService.
    """
    queue_service = QueueService()
    sql_service = AzureSQLService()

    logger.info("Worker de contactos iniciado. Escuchando 'manychat-contact-queue'...")

    while True:
        try:
            # Intenta recibir un mensaje de la cola de contactos
            message = await queue_service.receive_message("manychat-contact-queue")
            if message:
                logger.info(f"Mensaje recibido de la cola de contactos. ID: {message.id}")
                event_data = json.loads(message.content)

                # Valida los datos del evento contra el schema de Pydantic
                event = ManyChatContactEvent(**event_data)

                # Procesa el evento usando el servicio SQL
                result = await sql_service.process_contact_event(event)
                logger.info(f"Evento de contacto procesado exitosamente: {result}")

                # Elimina el mensaje de la cola una vez procesado
                await queue_service.delete_message(message)
                logger.info(f"Mensaje de contacto eliminado de la cola. ID: {message.id}")
            else:
                # Si no hay mensajes, espera un corto período antes de volver a intentar
                await asyncio.sleep(5) # Espera 5 segundos
        except Exception as e:
            logger.error(f"Error crítico en el worker de contactos: {str(e)}", exc_info=True)
            # En caso de error, espera antes de reintentar para evitar un bucle de errores rápido
            await asyncio.sleep(10) # Espera más tiempo en caso de error

# Para ejecutar el worker directamente (ej. python -m workers.contact_processor)
if __name__ == "__main__":
    # Asegúrate de que el loop de asyncio esté corriendo
    asyncio.run(process_contact_events())