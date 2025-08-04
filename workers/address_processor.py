# app/workers/address_processor.py
"""
Worker de Direcciones para ManyChat → Azure SQL
------------------------------------------------
Procesa eventos de dirección desde la cola 'manychat-address-queue'.
"""
import asyncio
import json
import os

from app.services.queue_service import QueueService, QueueServiceError
from app.schemas.manychat import ManyChatAddressEvent
from app.core.logging import logger
from app.db.session import get_db
from app.db.repositories import AddressRepository

async def process_address_events():
    """
    Worker para procesar eventos de dirección desde la cola.
    Añade la dirección a un contacto existente en Azure SQL.
    """
    queue_service = QueueService()
    # Asegurarse de que la cola de direcciones existe
    if not hasattr(queue_service, 'address_queue_name'):
        logger.critical("El nombre de la cola de direcciones no está configurado en QueueService. El worker no puede iniciar.")
        return

    await queue_service.ensure_queues_exist([queue_service.address_queue_name])
    
    sync_interval = int(os.getenv("SYNC_INTERVAL", 10))
    logger.info(f"Worker de direcciones iniciado. Escuchando '{queue_service.address_queue_name}'... Intervalo: {sync_interval}s")

    while True:
        message = None
        try:
            message = await queue_service.receive_message(queue_service.address_queue_name)
            if message:
                logger.info(f"Mensaje recibido de la cola de direcciones. ID: {message.id}")
                
                db_session_generator = get_db()
                db = next(db_session_generator)
                
                try:
                    event_data = json.loads(message.content)
                    event = ManyChatAddressEvent(**event_data)
                    logger.info(f"Procesando evento de dirección para ManyChat ID: {event.manychat_id}")

                    # Usar el repositorio para añadir la dirección
                    address_repo = AddressRepository(db)
                    address_payload = event.dict(exclude={'manychat_id'}) # Pasamos solo los datos de la dirección
                    
                    new_address = address_repo.add_address_to_contact(
                        manychat_id=event.manychat_id,
                        address_data=address_payload
                    )

                    if new_address:
                        logger.info(f"Dirección con ID {new_address.id} añadida exitosamente al contacto con manychat_id {event.manychat_id}.")
                    else:
                        logger.warning(f"No se pudo añadir la dirección para el manychat_id {event.manychat_id} porque el contacto no fue encontrado.")

                except Exception as e:
                    logger.error(f"Error al procesar el mensaje de dirección: {e}", exc_info=True)
                finally:
                    # Asegurarse de cerrar la sesión de la base de datos
                    next(db_session_generator, None)

                # Eliminar el mensaje de la cola después de procesarlo (incluso si falló, para evitar bucles infinitos)
                await queue_service.delete_message(queue_service.address_queue_name, message.id, message.pop_receipt)
            
            else:
                logger.debug(f"No hay mensajes en la cola de direcciones. Esperando {sync_interval} segundos...")
                await asyncio.sleep(sync_interval)

        except QueueServiceError as e:
            logger.error(f"Error de servicio de colas en worker de direcciones: {e}", exc_info=True)
            await asyncio.sleep(sync_interval)
        except Exception as e:
            logger.critical(f"Error inesperado en worker de direcciones: {e}", exc_info=True)
            if message:
                # Intenta eliminar el mensaje problemático para no bloquear la cola
                try:
                    await queue_service.delete_message(
                        queue_service.address_queue_name, message.id, message.pop_receipt
                    )
                    logger.warning("Mensaje de dirección potencialmente problemático eliminado.", message_id=message.id)
                except Exception as del_e:
                    logger.error(f"Fallo al intentar eliminar mensaje de dirección problemático: {del_e}", message_id=message.id)
            await asyncio.sleep(sync_interval * 2) # Esperar un poco más en caso de error crítico
