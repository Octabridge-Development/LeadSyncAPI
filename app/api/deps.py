# app/api/deps.py
"""
Dependencias compartidas para los endpoints de la API.
"""

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.queue_service import QueueService
from app.services.azure_sql_service import AzureSQLService
from app.core.config import get_settings # Mantener esta importación
from app.core.logging import logger

# REMOVIDA: settings = get_settings() # Esta línea se ha eliminado del nivel global

# Instancias singleton de servicios
_queue_service_instance = None
_azure_sql_service_instance = None


def get_queue_service() -> QueueService:
    """
    Proporciona una instancia singleton de QueueService.

    Returns:
        QueueService: Instancia del servicio de colas
    """
    global _queue_service_instance
    if _queue_service_instance is None:
        _queue_service_instance = QueueService()
    return _queue_service_instance


def get_azure_sql_service() -> AzureSQLService:
    """
    Proporciona una instancia singleton de AzureSQLService.

    Returns:
        AzureSQLService: Instancia del servicio de Azure SQL
    """
    global _azure_sql_service_instance
    if _azure_sql_service_instance is None:
        _azure_sql_service_instance = AzureSQLService()
    return _azure_sql_service_instance


async def verify_api_key(x_api_key: str = Header(None)) -> str:
    """
    Verifica que el API Key en el header sea válido.

    Args:
        x_api_key: API Key desde el header X-API-KEY

    Returns:
        str: API Key validado

    Raises:
        HTTPException: Si el API Key es inválido o falta
    """
    # AHORA OBTENEMOS LAS CONFIGURACIONES AQUI DENTRO DE LA FUNCION
    current_settings = get_settings() 

    if x_api_key is None:
        logger.warning("Intento de acceso sin API Key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-KEY header requerido",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # --- LINEAS DE DEPURACIÓN PARA CONFIRMAR (puedes eliminarlas después) ---
    print(f"DEBUG (deps.py): x_api_key recibido: '{x_api_key}'")
    print(f"DEBUG (deps.py): current_settings.API_KEY: '{current_settings.API_KEY}'")
    # ----------------------------------------------------------------------

    if x_api_key != current_settings.API_KEY: # Usamos current_settings
        logger.warning(f"Intento de acceso con API Key inválido: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválido",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


def get_db_session() -> Session:
    """
    Alias para get_db para consistencia.

    Returns:
        Session: Sesión de base de datos
    """
    return get_db()
