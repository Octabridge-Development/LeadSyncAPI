"""
Utilidad para monitoreo y logging de dependencias y workers.
"""

def log_dependency_health(dep_name: str, status: str, details: str = ""):
    from app.core.logging import logger
    logger.info(f"Health check: {dep_name} - {status}", details=details)