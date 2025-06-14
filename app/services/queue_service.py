# app/services/queue_service.py
from azure.storage.queue.aio import QueueServiceClient, QueueClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
import json
from datetime import datetime, timezone
from typing import Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import get_settings
from app.core.logging import logger

class QueueServiceError(Exception):
    """Excepción personalizada para errores en QueueService."""
    pass

def datetime_handler(obj: Any) -> str:
    """Maneja la serialización de objetos datetime a formato ISO para JSON."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

class QueueService:
    """
    Servicio completo y robusto para interactuar de forma asíncrona con Azure Storage Queue.
    Implementa reintentos, DLQ, y no duplica código.
    """
    def __init__(self):
        settings = get_settings()
        self.client: QueueServiceClient = QueueServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        self.campaign_queue_name = "manychat-campaign-queue"
        self.contact_queue_name = "manychat-contact-queue"
        self.dlq_name = "manychat-events-dlq"

    async def ensure_queues_exist(self) -> None:
        """Verifica y crea las colas necesarias de forma asíncrona si no existen."""
        logger.info("Verificando/creando colas de Azure...")
        queues_to_ensure = [self.campaign_queue_name, self.contact_queue_name, self.dlq_name]
        for queue_name in queues_to_ensure:
            try:
                await self.client.create_queue(queue_name)
                logger.info(f"Cola '{queue_name}' lista.")
            except ResourceExistsError:
                logger.info(f"Cola '{queue_name}' ya existe.")
            except Exception as e:
                logger.error(f"Error CRÍTICO al inicializar la cola {queue_name}: {e}", exc_info=True)
                raise QueueServiceError(f"No se pudo inicializar la cola {queue_name}: {e}")

    def _get_queue_client(self, queue_name: str) -> QueueClient:
        """Obtiene un cliente asíncrono para una cola específica."""
        return self.client.get_queue_client(queue_name)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(QueueServiceError)
    )
    async def send_message(self, queue_name: str, event_data: dict, is_dlq_retry: bool = False) -> None:
        """
        Envía un mensaje a una cola. Si falla, intenta enviarlo a la DLQ.
        """
        manychat_id = event_data.get('manychat_id', 'unknown')
        try:
            message_content = json.dumps(event_data, default=datetime_handler)
            queue_client = self._get_queue_client(queue_name)
            await queue_client.send_message(message_content)
            logger.info("Mensaje encolado exitosamente.", queue=queue_name, manychat_id=manychat_id)

        except Exception as e:
            logger.error(f"Fallo al enviar a la cola '{queue_name}'", error=str(e), manychat_id=manychat_id, exc_info=True)
            
            # LÓGICA DE DLQ RECUPERADA: No intentar enviar a DLQ si ya es un reintento de DLQ.
            if not is_dlq_retry:
                logger.warning(f"Intentando enviar mensaje a la Dead Letter Queue (DLQ)...", manychat_id=manychat_id)
                dlq_message = {
                    "original_queue": queue_name,
                    "error_time": datetime.now(timezone.utc).isoformat(),
                    "error_message": str(e),
                    "original_event": event_data
                }
                # Llamada recursiva para enviar a la DLQ, marcando que es un reintento.
                await self.send_message(self.dlq_name, dlq_message, is_dlq_retry=True)
            else:
                # Si incluso el envío a la DLQ falla, se lanza la excepción final.
                logger.critical("FALLO CRÍTICO: No se pudo enviar el mensaje ni a la cola principal ni a la DLQ.", manychat_id=manychat_id)
                raise QueueServiceError(f"Fallo al enviar a '{queue_name}' y también a la DLQ.")

    async def receive_message(self, queue_name: str, visibility_timeout: int = 300) -> Optional[Any]:
        """Recibe un único mensaje de la cola de forma asíncrona."""
        try:
            queue_client = self._get_queue_client(queue_name)
            async for message in queue_client.receive_messages(max_messages=1, visibility_timeout=visibility_timeout):
                return message
            return None
        except Exception as e:
            logger.error(f"Error al recibir mensaje de '{queue_name}'", error=str(e), exc_info=True)
            raise QueueServiceError(f"Error al recibir mensaje: {e}")

    async def delete_message(self, queue_name: str, message_id: str, pop_receipt: str) -> None:
        """Elimina un mensaje de la cola de forma asíncrona."""
        try:
            queue_client = self._get_queue_client(queue_name)
            await queue_client.delete_message(message_id, pop_receipt)
            logger.info(f"Mensaje '{message_id}' eliminado de '{queue_name}'.")
        except Exception as e:
            logger.error(f"Error al eliminar mensaje '{message_id}' de '{queue_name}'", error=str(e), exc_info=True)
            raise QueueServiceError(f"Error al eliminar mensaje: {e}")