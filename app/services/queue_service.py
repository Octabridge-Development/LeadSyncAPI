# Este archivo implementa la lógica para interactuar con servicios de colas.
# Incluye manejo de errores, reintentos, y validación de colas.

from azure.storage.queue import QueueServiceClient, QueueClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
import json
from datetime import datetime
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
        self.client = QueueServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        self.main_queue_name = "manychat-events-queue"
        self.dlq_name = "manychat-events-dlq"
        self._ensure_queues_exist()

    def _ensure_queues_exist(self) -> None:
        """
        Verifica y crea las colas necesarias si no existen.
        Raises:
            QueueServiceError: Si hay un error al crear las colas.
        """
        try:
            # Crear cola principal si no existe
            self.client.create_queue(self.main_queue_name)
            logger.info(f"Cola principal {self.main_queue_name} creada o verificada")
            
            # Crear DLQ si no existe
            self.client.create_queue(self.dlq_name)
            logger.info(f"Cola DLQ {self.dlq_name} creada o verificada")
        except ResourceExistsError:
            # Es normal si las colas ya existen
            pass
        except Exception as e:
            logger.error("Error al crear colas", error=str(e))
            raise QueueServiceError(f"Error al inicializar las colas: {str(e)}")

    def _get_queue_client(self, queue_name: str) -> QueueClient:
        """
        Obtiene un cliente para una cola específica.
        Args:
            queue_name: Nombre de la cola
        Returns:
            QueueClient para la cola especificada
        Raises:
            QueueNotFoundError: Si la cola no existe
        """
        try:
            return self.client.get_queue_client(queue_name)
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
    async def send_event_to_queue(self, event_data: dict) -> None:
        """
        Envía un evento ManyChat a la cola para procesamiento asíncrono.
        Implementa retry logic y manejo de errores.
        
        Args:
            event_data: Diccionario con los datos del evento ManyChat
            
        Raises:
            QueueServiceError: Si hay un error al enviar el mensaje después de los reintentos
        """
        manychat_id = event_data.get('manychat_id', 'unknown')
        
        try:
            # Serializar el mensaje con manejo de fechas
            message = json.dumps(event_data, default=datetime_handler)
            
            # Obtener cliente de cola principal
            queue_client = self._get_queue_client(self.main_queue_name)
            
            # Enviar mensaje
            queue_client.send_message(message)
            
            logger.info("Evento encolado exitosamente",
                       queue=self.main_queue_name,
                       manychat_id=manychat_id)

        except QueueServiceError:
            # Si es un error de la cola, intentar enviar a DLQ
            try:
                dlq_client = self._get_queue_client(self.dlq_name)
                dlq_client.send_message(message)
                logger.warning("Evento enviado a DLQ",
                             original_queue=self.main_queue_name,
                             manychat_id=manychat_id)
            except Exception as dlq_error:
                logger.error("Error al enviar a DLQ",
                           error=str(dlq_error),
                           manychat_id=manychat_id)
                raise QueueServiceError("Error al enviar tanto a cola principal como a DLQ")
            
        except Exception as e:
            logger.error("Error inesperado al encolar evento",
                        error=str(e),
                        manychat_id=manychat_id)
            raise QueueServiceError(f"Error inesperado al encolar evento: {str(e)}")
            
    async def peek_messages(self, queue_name: Optional[str] = None, max_messages: int = 32) -> list:
        """
        Inspecciona mensajes en una cola sin eliminarlos.
        Útil para monitoreo y debugging.
        
        Args:
            queue_name: Nombre de la cola a inspeccionar (default: cola principal)
            max_messages: Máximo número de mensajes a retornar
            
        Returns:
            Lista de mensajes en la cola
        """
        queue_name = queue_name or self.main_queue_name
        try:
            queue_client = self._get_queue_client(queue_name)
            messages = queue_client.peek_messages(max_messages=max_messages)
            return [json.loads(msg.content) for msg in messages]
        except Exception as e:
            logger.error(f"Error al inspeccionar cola {queue_name}", error=str(e))
            raise QueueServiceError(f"Error al inspeccionar cola: {str(e)}")