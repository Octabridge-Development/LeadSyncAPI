# app/utils/monitoring.py
"""
Utilidad para monitoreo y logging de dependencias y workers.
"""

def log_dependency_health(dep_name: str, status: str, details: str = ""):
    from app.core.logging import logger
    logger.info(f"Health check: {dep_name} - {status}", details=details)

def monitor_event(event_type: str, event_data: dict):
    """
    Monitorea eventos para métricas y observabilidad.
    """
    from app.core.logging import logger
    manychat_id = event_data.get('manychat_id', 'unknown')
    logger.info(f"Event monitored: {event_type}", manychat_id=manychat_id)
# app/utils/monitoring.py
"""
Utilidad para monitoreo y logging de dependencias y workers.
"""

def log_dependency_health(dep_name: str, status: str, details: str = ""):
    from app.core.logging import logger
    logger.info(f"Health check: {dep_name} - {status}", details=details)

def monitor_event(event_type: str, event_data: dict):
    """
    Monitorea eventos para métricas y observabilidad.
    """
    from app.core.logging import logger
    manychat_id = event_data.get('manychat_id', 'unknown')
    logger.info(f"Event monitored: {event_type}", manychat_id=manychat_id)