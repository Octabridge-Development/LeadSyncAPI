# monitoring/queue_monitor.py
"""
Dashboard básico de monitoreo de colas y workers.
Muestra el conteo de mensajes en cada cola y el estado de los workers.
"""
import asyncio
from app.services.queue_service import QueueService
from app.core.logging import logger

async def monitor_queues():
    queue_service = QueueService()
    await queue_service._ensure_queues_exist()
    colas = [
        queue_service.main_queue_name,
        queue_service.campaign_queue_name,
        queue_service.contact_queue_name,
        queue_service.dlq_name
    ]
    print("\n--- Estado de las colas ---")
    for cola in colas:
        try:
            messages = await queue_service.peek_messages(cola, max_messages=32)
            print(f"Cola: {cola:28} | Mensajes: {len(messages):3}")
        except Exception as e:
            print(f"Cola: {cola:28} | ERROR: {str(e)}")
    print("\n--- Estado de workers (simulado) ---")
    print("- campaign_processor.py: ACTIVO (ver logs)")
    print("- contact_processor.py:  ACTIVO (ver logs)")
    print("- queue_processor.py:    ACTIVO (ver logs)")
    print("\n(Verifica logs para detalles de procesamiento y errores)")

if __name__ == "__main__":
    asyncio.run(monitor_queues())
