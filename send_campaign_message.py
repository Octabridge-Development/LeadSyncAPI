import os
import json
from azure.storage.queue import QueueClient
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# Obtén la cadena de conexión de Azure Storage
# Asegúrate de que AZURE_STORAGE_CONNECTION_STRING esté definido en tu .env
# o en tus variables de entorno del sistema.
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
queue_name = "manychat-campaign-queue"

if not connection_string:
    print("Error: AZURE_STORAGE_CONNECTION_STRING no está configurado en .env o en el entorno.")
    exit(1)

# El mensaje JSON que quieres enviar
# !!! IMPORTANTE: Cambia 'TU_MANYCHAT_ID_EXISTENTE' por un manychat_id que SÍ exista en tu tabla Contact
#                 y 'NOMBRE_DE_CAMPAÑA_QUE_SE_CREARA_O_BUSCARA' por el nombre deseado de la campaña.
campaign_message = {
    "manychat_id": "test_contact_456", # <--- CAMBIA ESTO por un ID existente en tu DB Contact
    "campaign_id": "CAMPAIGN_VERANO_2025", # <--- CAMBIA ESTO por un nombre de campaña para probar
    "comercial_id": "COM-007", # ID de comercial (puedes ajustar según tus necesidades)
    "medico_id": None,
    "datetime_actual": "2025-06-05T12:45:23+00:00",
    "ultimo_estado": "Asignado",
    "tipo_asignacion": "Automatica"
}

print(f"Intentando enviar mensaje a la cola '{queue_name}'...")
try:
    # Crear un cliente de cola
    queue_client = QueueClient.from_connection_string(connection_string, queue_name)

    # Encolar el mensaje
    queue_client.send_message(json.dumps(campaign_message)) # Convierte el dict a JSON string
    print("Mensaje enviado exitosamente a la cola.")
    print(f"Contenido del mensaje: {json.dumps(campaign_message, indent=2)}")

except Exception as e:
    print(f"Error al enviar mensaje: {e}")