# workers/contact_processor.py
"""
Worker de Contactos para ManyChat → Azure SQL
----------------------------------------------
Procesa eventos de contacto desde la cola 'manychat-contact-queue'.

- Lee mensajes de la cola de Azure Storage.
- Procesa eventos de contacto de ManyChat.
- Guarda/actualiza el contacto en Azure SQL.
- Elimina el mensaje de la cola tras procesar.

Este worker implementa el patrón recomendado de desacoplamiento por colas, permitiendo:
- Reintentos automáticos y tolerancia a fallos.
- Escalabilidad y resiliencia ante picos de tráfico.

Recomendaciones:
- Ejecutar solo una instancia de este worker para evitar duplicados.
- Monitorear métricas y errores para detectar cuellos de botella.
- Mantener la lógica idempotente para evitar duplicados en reintentos.
"""
import asyncio
import json
import os
from app.services.queue_service import QueueService, QueueServiceError
## Eliminado import de Odoo
from app.services.azure_sql_service import AzureSQLService
from app.schemas.manychat import ManyChatContactEvent
from app.core.logging import logger
from app.db.models import Contact

async def process_contact_events(queue_service: QueueService, sql_service: AzureSQLService):
    """
    Worker para procesar eventos de contacto desde la cola.
    Guarda/actualiza el contacto en Azure SQL.
    """
    sync_interval = int(os.getenv("SYNC_INTERVAL", 10))  # segundos entre ciclos
    logger.info(f"Worker de contactos iniciado. Escuchando 'manychat-contact-queue'... Intervalo: {sync_interval}s")
    while True:
        message = None
        try:
            message = await queue_service.receive_message(queue_service.contact_queue_name)
            if message:
                logger.info(f"Mensaje recibido de la cola de contactos. ID: {message.id}")
                logger.info(f"Contenido bruto del mensaje recibido: {message.content}")
                try:
                    event_data = json.loads(message.content)
                    logger.info(f"Payload parseado: {event_data}")
                    event = ManyChatContactEvent(**event_data)
                    logger.info(f"Evento ManyChatContactEvent parseado: {event}")
                    result = await sql_service.process_contact_event(event)
                    logger.info(f"Evento de contacto procesado: {result}")
                except Exception as e:
                    logger.error(f"Error al parsear o procesar el mensaje: {e}")
                # ...lógica de sincronización con Odoo eliminada...
                # Elimina el mensaje de la cola tras procesar
                await queue_service.delete_message(queue_service.contact_queue_name, message.id, message.pop_receipt)
                await asyncio.sleep(sync_interval) # Espera configurable
            else:
                logger.info(f"No hay mensajes en la cola de contactos. Esperando {sync_interval} segundos...")
                await asyncio.sleep(sync_interval)
        except QueueServiceError as e:
            logger.error(f"Error de servicio de colas en worker de contactos: {e}", exc_info=True)
            await asyncio.sleep(sync_interval)
        except Exception as e:
            logger.error(f"Error inesperado en worker de contactos: {e}", exc_info=True)
            if message:
                try:
                    await queue_service.delete_message(
                        queue_service.contact_queue_name,
                        message.id,
                        message.pop_receipt
                    )
                    logger.warning("Mensaje potencialmente problemático eliminado.", message_id=message.id)
                except Exception as del_e:
                    logger.error(f"Fallo al intentar eliminar mensaje problemático: {del_e}", message_id=message.id)
            await asyncio.sleep(sync_interval)

async def main():
    """
    Función principal que inicializa los servicios y ejecuta el worker.
    """
    queue_service = QueueService()
    await queue_service.ensure_queues_exist() # Inicializa las colas de forma asíncrona
    
    sql_service = AzureSQLService()
    
    await process_contact_events(queue_service, sql_service)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker de contactos detenido manualmente.")