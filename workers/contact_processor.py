# workers/contact_processor.py
"""
Worker de Contactos para ManyChat → Azure SQL/Odoo
--------------------------------------------------
Procesa eventos de contacto desde la cola 'manychat-contact-queue'.

- Lee mensajes de la cola de Azure Storage.
- Procesa eventos de contacto de ManyChat.
- Guarda/actualiza el contacto en Azure SQL y sincroniza con Odoo.
- Elimina el mensaje de la cola tras procesar.

Este worker implementa el patrón recomendado de desacoplamiento por colas, permitiendo:
- Controlar la concurrencia hacia Odoo (evitar superar 1 req/s).
- Reintentos automáticos y tolerancia a fallos.
- Escalabilidad y resiliencia ante picos de tráfico.

Recomendaciones:
- Ejecutar solo una instancia de este worker para evitar saturar Odoo.
- Monitorear métricas y errores para detectar cuellos de botella.
- Mantener la lógica idempotente para evitar duplicados en reintentos.
"""
import asyncio
import json
from app.services.queue_service import QueueService, QueueServiceError
from app.services.azure_sql_service import AzureSQLService
from app.schemas.manychat import ManyChatContactEvent
from app.core.logging import logger

async def process_contact_events(queue_service: QueueService, sql_service: AzureSQLService):
    """
    Worker para procesar eventos de contacto desde la cola.
    """
    logger.info("Worker de contactos iniciado. Escuchando 'manychat-contact-queue'...")
    while True:
        message = None
        try:
            message = await queue_service.receive_message(queue_service.contact_queue_name)
            
            if message:
                logger.info(f"Mensaje recibido de la cola de contactos. ID: {message.id}")
                event_data = json.loads(message.content)
                event = ManyChatContactEvent(**event_data)

                logger.info(f"Procesando evento de contacto para ManyChat ID: {event.manychat_id}")
                result = await sql_service.process_contact_event(event)
                logger.info(f"Evento de contacto procesado: {result}")

                # CORRECCIÓN: Elimina el mensaje de forma ASÍNCRONA
                await queue_service.delete_message(
                    queue_name=queue_service.contact_queue_name, 
                    message_id=message.id, 
                    pop_receipt=message.pop_receipt
                )
                await asyncio.sleep(1) # Pausa para evitar saturar Odoo
            else:
                await asyncio.sleep(10) # Espera más si no hay mensajes

        except QueueServiceError as e:
            logger.error(f"Error de servicio de colas en worker de contactos: {e}", exc_info=True)
            await asyncio.sleep(60) # Espera un minuto antes de reintentar
        except Exception as e:
            logger.error(f"Error inesperado en worker de contactos: {e}", exc_info=True)
            if message: # Si el error ocurrió después de recibir un mensaje, intenta eliminarlo
                try:
                    await queue_service.delete_message(
                        queue_name=queue_service.contact_queue_name,
                        message_id=message.id,
                        pop_receipt=message.pop_receipt
                    )
                    logger.warning("Mensaje potencialmente problemático eliminado.", message_id=message.id)
                except Exception as del_e:
                    logger.error(f"Fallo al intentar eliminar mensaje problemático: {del_e}", message_id=message.id)
            await asyncio.sleep(10)

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