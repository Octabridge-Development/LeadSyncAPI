# Este archivo define los endpoints relacionados con reportes.
# Incluye el endpoint de salud (/health) para verificar el estado de las dependencias.

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.odoo_service import odoo_service
from app.services.queue_service import QueueService
from app.utils.monitoring import log_dependency_health
from app.core.logging import logger

router = APIRouter()

def check_database_health(db: Session):
    try:
        db.execute("SELECT 1")
        return "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        log_dependency_health("database", "error", str(e))
        return f"error: {str(e)}"

def check_odoo_health():
    try:
        odoo_service.client.version
        return "ok"
    except Exception as e:
        logger.error(f"Odoo health check failed: {str(e)}")
        log_dependency_health("odoo", "error", str(e))
        return f"error: {str(e)}"

def check_queue_health():
    try:
        queue_service = QueueService()
        queue_service._get_queue_client(queue_service.main_queue_name)
        return "ok"
    except Exception as e:
        logger.error(f"Queue health check failed: {str(e)}")
        log_dependency_health("queue", "error", str(e))
        return f"error: {str(e)}"

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Verifica el estado de las dependencias (DB, Odoo, Queue).
    """
    health_status = {
        "database": check_database_health(db),
        "odoo": check_odoo_health(),
        "queue": check_queue_health()
    }

    return health_status