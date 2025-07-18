# start_workers.py (en la raíz del proyecto, o workers/start_workers.py)


# Asegura que la raíz del proyecto esté en sys.path para imports absolutos
import os
import sys
import asyncio
import logging

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

from app.services.queue_service import QueueService # Para asegurar las colas existen
from workers.queue_processor import start_manychat_contact_worker, start_manychat_campaign_worker

# Configuración básica del logging si no se hace globalmente en 'main.py'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("Iniciando MiaSalud Integration Workers...")

    # Opcional: Asegurarse que las colas existen al inicio de los workers
    queue_service = QueueService()
    await queue_service.ensure_queues_exist()

    # Iniciar ambos tipos de workers concurrentemente
    await asyncio.gather(
        start_manychat_contact_worker(),
        start_manychat_campaign_worker()
    )

if __name__ == "__main__":
    asyncio.run(main())