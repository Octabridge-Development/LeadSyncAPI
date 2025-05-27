# utils/idempotency.py
"""
Utilidad para garantizar idempotencia en el procesamiento de mensajes.
Puedes implementar una función que use Redis, base de datos o memoria para evitar procesar dos veces el mismo evento.
"""
def is_duplicate_event(event_id: str) -> bool:
    # TODO: Implementar lógica real (por ejemplo, usando Redis o base de datos)
    return False

# utils/monitoring.py
"""
Utilidad para monitoreo y logging de dependencias y workers.
"""
def log_dependency_health(dep_name: str, status: str, details: str = ""):
    from app.core.logging import logger
    logger.info(f"Health check: {dep_name} - {status}", details=details)

# utils/retry.py
"""
Utilidad para lógica de reintentos personalizada.
Puedes usar tenacity o implementar lógica propia aquí.
"""
from tenacity import retry, stop_after_attempt, wait_exponential

def retry_on_exception():
    return retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))