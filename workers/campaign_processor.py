# workers/campaign_processor.py
import asyncio
import json
from app.services.queue_service import QueueService, QueueServiceError
from app.services.azure_sql_service import AzureSQLService
from app.schemas.manychat import ManyChatCampaignAssignmentEvent
from app.core.logging import logger

async def process_campaign_messages(queue_service: QueueService, azure_sql_service: AzureSQLService):
    """
    Consume y procesa mensajes de la cola de campañas en un bucle infinito.
    """
    logger.info("Worker de campaña iniciado. Esperando mensajes...")
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
                await asyncio.sleep(0.5) # Pausa breve tras procesar
            else:
                # No hay mensajes, espera un poco más
                await asyncio.sleep(2)

        except QueueServiceError as e:
            logger.error(f"Error de servicio de colas: {e}. Reintentando en 10 segundos.", exc_info=True)
            await asyncio.sleep(10)
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
            await asyncio.sleep(5)

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