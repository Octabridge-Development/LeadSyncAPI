from azure.storage.queue import QueueServiceClient
import json
from app.core.config import get_settings

class QueueService:
    """
    Servicio para enviar eventos ManyChat a la cola de Azure Storage Queue.
    """
    def __init__(self):
        # Inicializa el cliente de Azure Storage Queue usando la cadena de conexión del entorno
        self.client = QueueServiceClient.from_connection_string(
            get_settings().AZURE_STORAGE_CONNECTION_STRING
        )
        self.queue_name = "manychat-events-queue"

    async def send_event_to_queue(self, event_data: dict):
        """
        Envía un evento ManyChat a la cola para procesamiento asíncrono.
        Args:
            event_data (dict): Diccionario con los datos del evento ManyChat.
        """
        message = json.dumps(event_data)
        queue_client = self.client.get_queue_client(self.queue_name)
        queue_client.send_message(message)
        # Puedes agregar logging aquí si lo deseas