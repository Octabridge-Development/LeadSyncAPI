"""
Worker: campaign_processor.py

Este worker consume mensajes de la cola de campañas de ManyChat en Azure Storage Queue y procesa eventos de asignación de campaña.

- Desacopla el flujo de asignación de campañas para escalabilidad y resiliencia.
- Procesa mensajes de uno en uno, respeta la visibilidad y elimina los mensajes procesados.
- Llama a AzureSQLService para registrar la asignación en la base de datos.
- Maneja errores y registra logs estructurados.

Uso:
    python -m workers.campaign_processor

Ejemplo de mensaje esperado en la cola:
    {
        "manychat_id": "123456",
        "campaign_id": "camp-789",
        "comercial_id": "advisor-001",
        "datetime_actual": "2024-05-27T12:34:56Z",
        "ultimo_estado": "asignado",
        "tipo_asignacion": "manual"
    }
"""
import asyncio
import json
from app.services.queue_service import QueueService, QueueServiceError, QueueNotFoundError # Importa QueueNotFoundError también
from app.services.azure_sql_service import AzureSQLService
from app.schemas.manychat import ManyChatCampaignAssignmentEvent # Asegúrate de que esta clase exista y sea correcta
from app.core.logging import logger

def _log_start():
    logger.info("Worker de campaña iniciado. Esperando mensajes...")

async def process_campaign_messages():
    """
    Consume mensajes de la cola de campañas y procesa eventos de asignación de campaña.

    - Lee mensajes de la cola 'manychat-campaign-queue'.
    - Convierte el contenido a ManyChatCampaignAssignmentEvent.
    - Llama a AzureSQLService para procesar el evento.
    - Elimina el mensaje de la cola si se procesa correctamente.
    - Registra errores y continúa el procesamiento.

    Corre en bucle infinito con un pequeño delay entre iteraciones.
    """
    queue_service = QueueService()
    azure_sql_service = AzureSQLService()
    
    _log_start()

    while True:
        message = None # Inicializa message a None en cada iteración
        try:
            # Usar receive_message de QueueService que ya maneja errores y timeout
            message = await queue_service.receive_message(queue_service.campaign_queue_name)
            
            if message:
                event_data = json.loads(message.content)
                # Crea la instancia del evento Pydantic
                event = ManyChatCampaignAssignmentEvent(**event_data) 
                
                # Procesa el evento en Azure SQL
                await azure_sql_service.process_campaign_event(event)
                
                # === CORRECCIÓN CLAVE AQUÍ ===
                # Llama a delete_message de QueueService, pasando los atributos correctos
                queue_service.delete_message(
                    queue_name=queue_service.campaign_queue_name,
                    message_id=message.id,
                    pop_receipt=message.pop_receipt
                )
                logger.info(
                    "Mensaje de campaña procesado y eliminado", 
                    manychat_id=event.manychat_id, 
                    message_id=message.id
                )
            else:
                # No hay mensajes, espera un poco antes de volver a consultar
                await asyncio.sleep(2)
                continue # Continúa al siguiente ciclo del bucle
                
        except QueueNotFoundError as e:
            logger.error(f"La cola de campañas no fue encontrada: {e}. Reintentando...", queue_name=queue_service.campaign_queue_name)
            await asyncio.sleep(5) # Espera un poco más si la cola no se encuentra
        except QueueServiceError as e:
            logger.error(f"Error en el servicio de colas al recibir/eliminar mensaje de campaña: {e}", 
                         queue_name=queue_service.campaign_queue_name, 
                         message_id=message.id if message else "N/A", 
                         pop_receipt=message.pop_receipt if message else "N/A")
            await asyncio.sleep(5) # Espera antes de reintentar si hay un error de cola
        except json.JSONDecodeError as e:
            logger.error("Error al decodificar JSON del mensaje de campaña", 
                         error=str(e), 
                         raw_content=message.content if message else "N/A",
                         message_id=message.id if message else "N/A")
            if message: # Intenta eliminar el mensaje malformado si es posible para no bloquear la cola
                try:
                    queue_service.delete_message(
                        queue_name=queue_service.campaign_queue_name,
                        message_id=message.id,
                        pop_receipt=message.pop_receipt
                    )
                    logger.warning("Mensaje de campaña malformado eliminado para evitar re-procesamiento", message_id=message.id)
                except Exception as del_e:
                    logger.error(f"Error al intentar eliminar mensaje de campaña malformado: {del_e}", message_id=message.id)
            await asyncio.sleep(2) # Espera un poco antes de continuar
        except Exception as e:
            # Captura cualquier otra excepción durante el procesamiento del evento
            logger.error("Error inesperado procesando mensaje de campaña", 
                         error=str(e), 
                         message_id=message.id if message else "N/A", 
                         raw_content=message.content if message else "N/A")
            # Considera aquí si quieres mover el mensaje a la DLQ para inspección
            # o simplemente dejarlo fallar hasta que se vaya a la DLQ automáticamente
            # por el contador de reintentos de Azure Queue.
            await asyncio.sleep(2) # Pequeña pausa antes de la siguiente iteración

        # Pequeña pausa antes de la siguiente consulta a la cola si hubo un mensaje
        if message:
            await asyncio.sleep(0.5) 
        
if __name__ == "__main__":
    asyncio.run(process_campaign_messages())