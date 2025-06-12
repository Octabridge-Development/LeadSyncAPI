# app/api/v1/endpoints/reports.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any

from app.db.session import get_db
from app.services.queue_service import QueueService
from app.api.deps import verify_api_key, get_queue_service
from app.utils.monitoring import log_dependency_health
from app.core.logging import logger

router = APIRouter(
    tags=["Reports"],
    responses={
        401: {
            "description": "No autorizado - API Key inválido o faltante",
            "content": {
                "application/json": {
                    "example": {"detail": "X-API-KEY header requerido"}
                }
            }
        }
    }
)


def check_database_health(db: Session) -> Dict[str, Any]:
    """
    Verifica la salud de la conexión a Azure SQL Database.

    Args:
        db: Sesión de base de datos

    Returns:
        Dict con status y detalles de la conexión
    """
    try:
        # Ejecutar query de prueba
        result = db.execute(text("SELECT @@VERSION as version, GETDATE() as current_time"))
        row = result.fetchone()

        # Obtener estadísticas básicas
        stats_result = db.execute(text("""
                                       SELECT (SELECT COUNT(*) FROM Contact)       as total_contacts,
                                              (SELECT COUNT(*) FROM Contact_State) as total_states,
                                              (SELECT COUNT(*) FROM Channel)       as total_channels
                                       """))
        stats = stats_result.fetchone()

        log_dependency_health("database", "ok")

        return {
            "status": "healthy",
            "connection": "active",
            "version": row.version.split('\n')[0] if row else "Unknown",
            "server_time": str(row.current_time) if row else None,
            "statistics": {
                "total_contacts": stats.total_contacts if stats else 0,
                "total_states": stats.total_states if stats else 0,
                "total_channels": stats.total_channels if stats else 0
            }
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        log_dependency_health("database", "error", str(e))
        return {
            "status": "unhealthy",
            "connection": "failed",
            "error": str(e)
        }


def check_odoo_health() -> Dict[str, Any]:
    """
    Verifica la salud de la conexión con Odoo.

    Returns:
        Dict con status de la conexión a Odoo
    """
    # TEMPORALMENTE DESHABILITADO
    return {
        "status": "disabled",
        "message": "Odoo health check temporalmente deshabilitado",
        "note": "Se habilitará cuando se complete la integración con Odoo"
    }

    # Código para cuando se habilite:
    # try:
    #     from app.services.odoo_service import odoo_service
    #     version = odoo_service.client.version
    #     log_dependency_health("odoo", "ok")
    #     return {
    #         "status": "healthy",
    #         "connection": "active",
    #         "version": version
    #     }
    # except Exception as e:
    #     logger.error(f"Odoo health check failed: {str(e)}")
    #     log_dependency_health("odoo", "error", str(e))
    #     return {
    #         "status": "unhealthy",
    #         "connection": "failed",
    #         "error": str(e)
    #     }


def check_queue_health(queue_service: QueueService) -> Dict[str, Any]:
    """
    Verifica la salud de las colas de Azure Storage.

    Args:
        queue_service: Instancia del servicio de colas

    Returns:
        Dict con status de cada cola
    """
    try:
        queue_statuses = {}

        # Lista de colas a verificar
        queues_to_check = [
            ("main_queue", queue_service.main_queue_name),
            ("contact_queue", queue_service.contact_queue_name),
            ("campaign_queue", queue_service.campaign_queue_name),
            ("dlq", queue_service.dlq_name)
        ]

        for queue_label, queue_name in queues_to_check:
            try:
                queue_client = queue_service._get_queue_client(queue_name)
                properties = queue_client.get_queue_properties()
                queue_statuses[queue_label] = {
                    "name": queue_name,
                    "status": "active",
                    "approximate_message_count": properties.approximate_message_count
                }
            except Exception as e:
                queue_statuses[queue_label] = {
                    "name": queue_name,
                    "status": "error",
                    "error": str(e)
                }

        log_dependency_health("queues", "ok")

        return {
            "status": "healthy",
            "connection": "active",
            "queues": queue_statuses
        }

    except Exception as e:
        logger.error(f"Queue health check failed: {str(e)}")
        log_dependency_health("queues", "error", str(e))
        return {
            "status": "unhealthy",
            "connection": "failed",
            "error": str(e)
        }


@router.get(
    "/health",
    summary="Health Check completo del sistema",
    description="Verifica el estado de todas las dependencias del sistema",
    response_description="Estado detallado de cada componente",
    responses={
        200: {
            "description": "Estado de salud del sistema",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "dependencies": {
                            "database": {
                                "status": "healthy",
                                "connection": "active",
                                "statistics": {
                                    "total_contacts": 150,
                                    "total_states": 450
                                }
                            },
                            "odoo": {
                                "status": "disabled",
                                "message": "Temporalmente deshabilitado"
                            },
                            "queues": {
                                "status": "healthy",
                                "queues": {
                                    "main_queue": {
                                        "status": "active",
                                        "approximate_message_count": 5
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
)
async def health_check(
        db: Session = Depends(get_db),
        queue_service: QueueService = Depends(get_queue_service),
        api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Endpoint de health check completo del sistema.

    Verifica:
    - **Base de datos**: Conexión a Azure SQL y estadísticas básicas
    - **Odoo**: Estado de la conexión (actualmente deshabilitado)
    - **Colas**: Estado de todas las colas de Azure Storage

    Este endpoint requiere autenticación con API Key para prevenir
    exposición no autorizada de información del sistema.
    """
    # Ejecutar verificaciones
    db_health = check_database_health(db)
    odoo_health = check_odoo_health()
    queue_health = check_queue_health(queue_service)

    # Determinar estado general
    overall_status = "healthy"
    if any(dep.get("status") == "unhealthy" for dep in [db_health, queue_health]):
        overall_status = "unhealthy"
    elif any(dep.get("status") == "degraded" for dep in [db_health, odoo_health, queue_health]):
        overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": db_health.get("server_time", "N/A"),
        "dependencies": {
            "database": db_health,
            "odoo": odoo_health,
            "queues": queue_health
        }
    }


@router.get(
    "/statistics",
    summary="Estadísticas del sistema",
    description="Obtiene estadísticas de uso y procesamiento del sistema",
    responses={
        200: {
            "description": "Estadísticas actuales del sistema",
            "content": {
                "application/json": {
                    "example": {
                        "contacts": {
                            "total": 150,
                            "by_channel": {
                                "Facebook": 80,
                                "WhatsApp": 70
                            },
                            "recent_24h": 25
                        },
                        "states": {
                            "total": 450,
                            "by_state": {
                                "Nuevo Lead": 50,
                                "Lead Asignado": 100
                            }
                        },
                        "queues": {
                            "pending_messages": 5,
                            "dlq_messages": 0
                        }
                    }
                }
            }
        }
    }
)
async def get_statistics(
        db: Session = Depends(get_db),
        queue_service: QueueService = Depends(get_queue_service),
        api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene estadísticas detalladas del sistema.

    Incluye:
    - Total de contactos y distribución por canal
    - Estados de contactos y su distribución
    - Mensajes pendientes en colas
    - Actividad reciente (últimas 24 horas)
    """
    try:
        # Estadísticas de contactos
        contacts_stats = db.execute(text("""
                                         SELECT COUNT(*)                                                                as total,
                                                COUNT(CASE WHEN entry_date >= DATEADD(hour, -24, GETDATE()) THEN 1 END) as recent_24h
                                         FROM Contact
                                         """)).fetchone()

        # Contactos por canal
        channel_stats = db.execute(text("""
                                        SELECT c.name as channel_name, COUNT(con.id) as count
                                        FROM Contact con
                                            LEFT JOIN Channel c
                                        ON con.channel_id = c.id
                                        GROUP BY c.name
                                        """)).fetchall()

        # Estados más comunes
        state_stats = db.execute(text("""
                                      SELECT TOP 10 state, COUNT(*) as count
                                      FROM Contact_State
                                      GROUP BY state
                                      ORDER BY count DESC
                                      """)).fetchall()

        # Obtener información de colas
        queue_info = check_queue_health(queue_service)

        return {
            "contacts": {
                "total": contacts_stats.total if contacts_stats else 0,
                "recent_24h": contacts_stats.recent_24h if contacts_stats else 0,
                "by_channel": {
                    row.channel_name or "Sin Canal": row.count
                    for row in channel_stats
                } if channel_stats else {}
            },
            "states": {
                "total": sum(row.count for row in state_stats) if state_stats else 0,
                "by_state": {
                    row.state: row.count
                    for row in state_stats
                } if state_stats else {}
            },
            "queues": {
                "status": queue_info.get("status", "unknown"),
                "details": queue_info.get("queues", {})
            }
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )