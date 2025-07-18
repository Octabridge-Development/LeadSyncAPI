# workers/campaign_processor.py
"""
Worker de Campañas para ManyChat → Azure SQL/Odoo
--------------------------------------------------
Procesa eventos de asignación de campaña desde la cola 'manychat-campaign-queue'.

- Lee mensajes de la cola de Azure Storage.
- Procesa eventos de asignación de campaña de ManyChat.
- Actualiza la relación de campaña en Azure SQL.
- Elimina el mensaje de la cola tras procesar.

Este worker implementa el patrón recomendado de desacoplamiento por colas, permitiendo:
- Controlar la concurrencia hacia Odoo (evitar superar 1 req/s si se sincroniza con Odoo).
- Reintentos automáticos y tolerancia a fallos.
- Escalabilidad y resiliencia ante picos de tráfico.

Recomendaciones:
- Ejecutar solo una instancia de este worker para evitar saturar Odoo.
- Monitorear métricas y errores para detectar cuellos de botella.
- Mantener la lógica idempotente para evitar duplicados en reintentos.
"""


import asyncio
import json
import os
from app.services.queue_service import QueueService, QueueServiceError
from app.services.azure_sql_service import AzureSQLService
from app.schemas.manychat import ManyChatCampaignAssignmentEvent
from app.core.logging import logger

# Constante para el intervalo de sincronización por defecto
DEFAULT_SYNC_INTERVAL = 10

async def process_campaign_messages(queue_service: QueueService, azure_sql_service: AzureSQLService):
    """
    Consume y procesa mensajes de la cola de campañas en un bucle infinito.
    """
    sync_interval = int(os.getenv("SYNC_INTERVAL", DEFAULT_SYNC_INTERVAL))  # segundos entre ciclos
    logger.info(f"Worker de campaña iniciado. Esperando mensajes de 'manychat-campaign-queue'... Intervalo: {sync_interval}s")
    while True:
        message = None
        try:
            message = await queue_service.receive_message(queue_service.campaign_queue_name)
            
            if message:
                event_data = json.loads(message.content)
                
                # Valida y convierte campaign_id a int
                if "campaign_id" in event_data and isinstance(event_data["campaign_id"], str):
                    try:
                        event_data["campaign_id"] = int(event_data["campaign_id"])
                    except (ValueError, TypeError):
                        logger.error("El 'campaign_id' no es un entero válido.", raw_value=event_data["campaign_id"])
                        raise ValueError("campaign_id debe ser un entero.")
                
                event = ManyChatCampaignAssignmentEvent(**event_data)
                
                # Procesa el evento en la base de datos
                await azure_sql_service.process_campaign_event(event)
                
                # CORRECCIÓN: Elimina el mensaje de forma ASÍNCRONA
                await queue_service.delete_message(
                    queue_name=queue_service.campaign_queue_name,
                    message_id=message.id,
                    pop_receipt=message.pop_receipt
                )
                logger.info(
                    "Mensaje de campaña procesado y eliminado.", 
                    manychat_id=event.manychat_id, 
                    message_id=message.id
                )
                await asyncio.sleep(sync_interval) # Espera configurable
            else:
                logger.info(f"No hay mensajes en la cola de campañas. Esperando {sync_interval} segundos...")
                await asyncio.sleep(sync_interval)

        except QueueServiceError as e:
            logger.error(f"Error de servicio de colas: {e}. Reintentando en {sync_interval} segundos.", exc_info=True)
            await asyncio.sleep(sync_interval)
        except json.JSONDecodeError:
            logger.error("Error al decodificar JSON. Mensaje malformado.", raw_content=message.content if message else "N/A")
            if message:
                # Intenta eliminar el mensaje malformado para no bloquear la cola
                await queue_service.delete_message(
                    queue_name=queue_service.campaign_queue_name,
                    message_id=message.id,
                    pop_receipt=message.pop_receipt
                )
                logger.warning("Mensaje malformado eliminado.", message_id=message.id)
        except Exception as e:
            logger.error(f"Error inesperado procesando mensaje de campaña: {e}", exc_info=True)
            await asyncio.sleep(sync_interval)

async def main():
    """
    Función principal que inicializa los servicios y ejecuta el worker.
    """
    queue_service = QueueService()
    await queue_service.ensure_queues_exist() # Inicializa las colas de forma asíncrona
    
    azure_sql_service = AzureSQLService()
    
    await process_campaign_messages(queue_service, azure_sql_service)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker de campaña detenido manualmente.")