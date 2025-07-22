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
                    logger.info(f"Procesando evento de contacto para ManyChat ID: {event.manychat_id}")
                    result = await sql_service.process_contact_event(event)
                    # --- Actualizar last_state en CampaignContact ---
                    # Buscar el CampaignContact por contact_id y campaign_id (si existe)
                    from app.db.session import get_db
                    from app.db.repositories import CampaignContactRepository
                    async def update_campaign_contact_and_contact_last_state():
                        with get_db() as db:
                            from app.db.repositories import ContactRepository
                            repo_cc = CampaignContactRepository(db)
                            repo_contact = ContactRepository(db)
                            campaign_contact = db.query(repo_cc.model).filter_by(contact_id=result['contact_id']).order_by(repo_cc.model.registration_date.desc()).first()
                            if campaign_contact:
                                campaign_contact.last_state = event.estado_inicial
                                db.add(campaign_contact)
                                db.commit()
                                db.refresh(campaign_contact)
                                logger.info(f"CampaignContact actualizado: last_state={campaign_contact.last_state}")
                                # Sincronizar campo en Contact
                                contact = db.query(repo_contact.model).filter_by(id=result['contact_id']).first()
                                if contact:
                                    contact.initial_state = campaign_contact.last_state
                                    db.add(contact)
                                    db.commit()
                                    db.refresh(contact)
                                    logger.info(f"Contact actualizado: initial_state={contact.initial_state}")
                    await update_campaign_contact_and_contact_last_state()
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