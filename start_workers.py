# start_workers.py

import os
import sys
import asyncio
import logging

# Asegura que la raíz del proyecto esté en sys.path para imports absolutos
# Esto es crucial para que los workers encuentren los módulos de la app
ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

from app.services.queue_service import QueueService
# --- ✅ CAMBIO: Importamos los workers existentes y el nuevo ---
from workers.contact_processor import process_contact_events
# Suponiendo que tienes un campaign_processor.py similar
# from workers.campaign_processor import process_campaign_events 
from workers.address_processor import process_address_events

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("Iniciando MiaSalud Integration Workers...")

    # Opcional: Asegurarse de que las colas existen al inicio.
    # El propio worker ya lo hace, pero es una buena práctica centralizarlo.
    try:
        queue_service = QueueService()
        await queue_service.ensure_queues_exist()
        logger.info("Todas las colas necesarias han sido verificadas/creadas.")
    except Exception as e:
        logger.critical(f"No se pudieron inicializar las colas. Error: {e}. Abortando workers.")
        return

    # --- ✅ CAMBIO: Añadimos el nuevo worker al `gather` ---
    # Iniciar todos los workers para que se ejecuten al mismo tiempo.
    # Nota: He asumido que tienes un 'process_campaign_events'. Si no, puedes quitar esa línea.
    
    # Para el contact_processor que necesita argumentos
    from app.services.azure_sql_service import AzureSQLService
    sql_service = AzureSQLService()

    await asyncio.gather(
        process_contact_events(queue_service, sql_service),
        # process_campaign_events(), # Descomenta si tienes este worker
        process_address_events()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Workers detenidos manualmente.")
    except Exception as e:
        logger.critical(f"Error crítico al ejecutar los workers: {e}", exc_info=True)