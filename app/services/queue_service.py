# app/services/queue_service.py
from azure.storage.queue.aio import QueueServiceClient, QueueClient # CAMBIO AQUÍ
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
import json
from datetime import datetime, timezone
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import get_settings
from app.core.logging import logger


class QueueServiceError(Exception):
    """Excepción base para errores del QueueService."""
    pass

class QueueNotFoundError(QueueServiceError):
    """Excepción cuando no existe la cola."""
    pass

def datetime_handler(obj):
    """Maneja la serialización de objetos datetime a JSON."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

class QueueService:
    """
    Servicio para enviar eventos ManyChat a la cola de Azure Storage Queue.
    Implementa manejo de errores, retries y Dead Letter Queue.
    """
    def __init__(self):
        settings = get_settings()
        # CAMBIO: Inicializar el cliente de servicio asíncrono
        self.client: QueueServiceClient = QueueServiceClient.from_connection_string( # CAMBIO AQUÍ
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        self.main_queue_name = "manychat-events-queue"
        self.campaign_queue_name = "manychat-campaign-queue"
        self.dlq_name = "manychat-events-dlq"
        self.contact_queue_name = "manychat-contact-queue"
        # Llamar a ensure_queues_exist de forma asíncrona (esto se arreglará al llamar a esta clase)
        # self._ensure_queues_exist() # COMENTA o BORRA esta línea, la manejaremos en el worker

    # CAMBIO: Hacer este método asíncrono
    async def _ensure_queues_exist(self) -> None: # CAMBIO AQUÍ
        """
        Verifica y crea las colas necesarias si no existen.
        Raises:
            QueueServiceError: Si hay un error al crear las colas.
        """
        logger.info("Iniciando verificación/creación de colas de Azure Storage...")

        queues_to_ensure = [
            self.main_queue_name,
            self.campaign_queue_name,
            self.contact_queue_name,
            self.dlq_name
        ]

        for queue_name in queues_to_ensure:
            try:
                logger.info(f"Intentando crear/verificar cola: {queue_name}")
                # CAMBIO: usar await para create_queue
                await self.client.create_queue(queue_name) # CAMBIO AQUÍ
                logger.info(f"Cola {queue_name} creada o verificada exitosamente.")
            except ResourceExistsError:
                logger.info(f"Cola {queue_name} ya existe. Continuando.")
            except Exception as e:
                logger.error(f"Error CRÍTICO al crear/verificar la cola {queue_name}: {str(e)}", exc_info=True)
                raise QueueServiceError(f"Error al inicializar la cola {queue_name}: {str(e)}")

        logger.info("Verificación/creación de todas las colas finalizada.")

    def _get_queue_client(self, queue_name: str) -> QueueClient:
        """
        Obtiene un cliente para una cola específica (ahora asíncrono).
        Args:
            queue_name: Nombre de la cola
        Returns:
            QueueClient para la cola especificada
        Raises:
            QueueNotFoundError: Si la cola no existe
        """
        try:
            # CAMBIO: get_queue_client del cliente de servicio asíncrono devuelve un QueueClient asíncrono
            return self.client.get_queue_client(queue_name) # ESTO YA DEVUELVE EL CLIENTE ASÍNCRONO
        except ResourceNotFoundError:
            logger.error(f"Cola {queue_name} no encontrada")
            raise QueueNotFoundError(f"La cola {queue_name} no existe")
        except Exception as e:
            logger.error(f"Error al obtener cola {queue_name}", error=str(e))
            raise QueueServiceError(f"Error al obtener cola {queue_name}: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(QueueServiceError),
        before_sleep=lambda retry_state: logger.warning(
            "Reintentando envío a cola",
            attempt=retry_state.attempt_number,
            wait=retry_state.idle_for
        )
    )
    async def send_campaign_event_to_queue(self, event_data: dict) -> None:
        """
        Envía un evento de asignación de campaña a la cola de campañas.
        ...
        """
        manychat_id = event_data.get('manychat_id', 'unknown')

        try:
            message = json.dumps(event_data, default=datetime_handler)
            queue_client = self._get_queue_client(self.campaign_queue_name)
            await queue_client.send_message(message) # Mantener await
            logger.info("Evento de campaña encolado exitosamente",
                        queue=self.campaign_queue_name,
                        manychat_id=manychat_id,
                        campaign_id=event_data.get('campaign_id', 'unknown'))

        except Exception as e:
            logger.error("Error inesperado al encolar evento de campaña",
                         error=str(e),
                         manychat_id=manychat_id)
            raise QueueServiceError(f"Error inesperado al encolar evento de campaña: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(QueueServiceError),
        before_sleep=lambda retry_state: logger.warning(
            "Reintentando envío a cola",
            attempt=retry_state.attempt_number,
            wait=retry_state.idle_for
        )
    )
    async def send_message(self, event_data: dict, queue_name: str) -> None:
        """
        Envía un mensaje a la cola especificada.
        ...
        """
        manychat_id = event_data.get('manychat_id', 'unknown')

        try:
            message_content = json.dumps(event_data, default=datetime_handler)
            queue_client = self._get_queue_client(queue_name)
            await queue_client.send_message(message_content) # Mantener await

            logger.info("Mensaje encolado exitosamente",
                        queue=queue_name,
                        manychat_id=manychat_id)

        except QueueServiceError as e:
            logger.error(f"Error al enviar a cola principal ({queue_name}): {str(e)}. Intentando DLQ.", exc_info=True)
            try:
                dlq_client = self._get_queue_client(self.dlq_name)
                dlq_message = {
                    "original_queue": queue_name,
                    "error_time": datetime.now(timezone.utc).isoformat(),
                    "event_data": event_data,
                    "error_message": str(e)
                }
                await dlq_client.send_message(json.dumps(dlq_message, default=datetime_handler)) # Mantener await
                logger.warning("Evento enviado a DLQ",
                               original_queue=queue_name,
                               manychat_id=manychat_id)
            except Exception as dlq_error:
                logger.error("Error al enviar a DLQ",
                             error=str(dlq_error),
                             manychat_id=manychat_id,
                             exc_info=True)
                raise QueueServiceError("Error al enviar tanto a cola principal como a DLQ")

        except Exception as e:
            logger.error("Error inesperado al encolar evento",
                            error=str(e),
                            manychat_id=manychat_id,
                            queue=queue_name,
                            exc_info=True)
            raise QueueServiceError(f"Error inesperado al encolar evento: {str(e)}")

    async def peek_messages(self, queue_name: Optional[str] = None, max_messages: int = 32) -> list:
        """
        Inspecciona mensajes en una cola sin eliminarlos.
        ...
        """
        queue_name = queue_name or self.main_queue_name
        try:
            queue_client = self._get_queue_client(queue_name)
            messages = await queue_client.peek_messages(max_messages=max_messages) # Mantener await
            return [json.loads(msg.content) for msg in messages]
        except Exception as e:
            logger.error(f"Error al inspeccionar cola {queue_name}", error=str(e))
            raise QueueServiceError(f"Error al inspeccionar cola: {str(e)}")

    async def receive_message(self, queue_name: str):
        """
        Recibe un mensaje de la cola especificada.
        Retorna el mensaje si lo hay, o None.
        """
        try:
            queue_client: QueueClient = self._get_queue_client(queue_name)
            # await queue_client.receive_messages devuelve un AsyncItemPaged, que SÍ es awaitable.
            # Necesitamos iterar sobre él de forma asíncrona.
            async for message in queue_client.receive_messages(max_messages=1, visibility_timeout=300): # CAMBIO CLAVE AQUÍ
                return message # Retorna el primer mensaje que reciba
            return None # No hay mensajes
        except Exception as e:
            logger.error(f"Error recibiendo mensaje de {queue_name}", error=str(e), exc_info=True)
            raise QueueServiceError(f"Error al recibir mensaje: {str(e)}")

    async def delete_message(self, queue_name: str, message_id: str, pop_receipt: str):
        """
        Elimina un mensaje procesado de la cola.
        ...
        """
        try:
            queue_client = self._get_queue_client(queue_name)
            await queue_client.delete_message(message_id, pop_receipt) # Mantener await
            logger.info(f"Mensaje '{message_id}' eliminado exitosamente de la cola '{queue_name}'.")
        except Exception as e:
            logger.error(f"Error eliminando mensaje '{message_id}' de la cola '{queue_name}'", error=str(e), exc_info=True)
            raise QueueServiceError(f"Error al eliminar mensaje: {str(e)}")