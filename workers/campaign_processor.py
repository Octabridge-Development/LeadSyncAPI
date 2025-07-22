# workers/campaign_processor.py
"""
Worker de Campañas para ManyChat → Azure SQL/Odoo
--------------------------------------------------
Procesa eventos de asignación de campaña desde la cola 'manychat-campaign-queue'.

- Lee mensajes de la cola de Azure Storage.
- Procesa eventos de asignación de campaña de ManyChat.
- Actualiza la relación de campaña en Azure SQL.
- Elimina el mensaje de la cola tras procesar.

Este worker implementa el patrón recomendado de desacoplamiento por colas, permitiendo:
- Controlar la concurrencia hacia Odoo (evitar superar 1 req/s si se sincroniza con Odoo).
- Reintentos automáticos y tolerancia a fallos.
- Escalabilidad y resiliencia ante picos de tráfico.

Recomendaciones:
- Ejecutar solo una instancia de este worker para evitar saturar Odoo.
- Monitorear métricas y errores para detectar cuellos de botella.
- Mantener la lógica idempotente para evitar duplicados en reintentos.
"""



import asyncio
import os
from app.db.session import get_db_session_worker
from app.db.models import CampaignContact, ContactState

from app.core.logging import logger

# Mapeo ManyChat Stage → Odoo Stage ID
MANYCHAT_TO_ODOO_STAGE = {
    "Recién Suscrito (Sin Asignar)": 16,
    "Recién suscrito Pendiente de AC": 17,
    "Retornó en AC": 18,
    "Comienza Atención Comercial": 19,
    "Retornó a Asesoría especializada": 20,
    "Derivado Asesoría Médica": 21,
    "Comienza Asesoría Médica": 22,
    "Terminó Asesoría Médica": 23,
    "No terminó Asesoria especializada Derivado a Comercial": 24,
    "Comienza Cotización": 25,
    "Orden de venta Confirmada": 26,
}

# Constante para el intervalo de sincronización por defecto
DEFAULT_SYNC_INTERVAL = 10

async def process_campaign_contacts():
    """
    Worker que procesa CampaignContact con sync_status 'new', 'updated' o 'error'.
    """
    sync_interval = int(os.getenv("SYNC_INTERVAL", DEFAULT_SYNC_INTERVAL))
    logger.info(f"Worker de campaña iniciado. Procesando CampaignContact con sync_status relevante. Intervalo: {sync_interval}s")
    while True:
        try:
            for db in get_db_session_worker():
                contacts = db.query(CampaignContact).filter(CampaignContact.sync_status.in_(["new", "updated", "error"])).all()
                if not contacts:
                    logger.info(f"No hay CampaignContact pendientes. Esperando {sync_interval} segundos...")
                    await asyncio.sleep(sync_interval)
                    continue
                for cc in contacts:
                    try:
                        # Obtener el último estado relevante de ContactState para este contacto
                        contact_state = db.query(ContactState).filter(
                            ContactState.contact_id == cc.contact_id
                        ).order_by(ContactState.created_at.desc()).first()

                        if contact_state:
                            # Actualizamos el last_state en CampaignContact con el último estado
                            cc.last_state = contact_state.state
                            logger.info(f"Procesando CampaignContact {cc.id} (contact_id={cc.contact_id}, campaign_id={cc.campaign_id}). Actualizando last_state a: '{contact_state.state}'")

                            # Aseguramos que el Contact tenga el estado más reciente
                            contact = cc.contact
                            if contact:
                                contact.last_state_id = contact_state.id
                                db.add(contact)
                                db.commit()
                                logger.info(f"Contact {contact.id} actualizado con último estado ID: {contact_state.id}")

                        cc.sync_status = "synced"
                        db.add(cc)
                        db.commit()
                        logger.info(f"CampaignContact {cc.id} actualizado correctamente en Azure SQL.")
                    except Exception as e:
                        db.rollback()
                        cc.sync_status = "error"
                        db.add(cc)
                        db.commit()
                        logger.error(f"Error al sincronizar CampaignContact {cc.id}: {e}")
            await asyncio.sleep(sync_interval)
        except Exception as e:
            logger.error(f"Error inesperado en el worker de CampaignContact: {e}", exc_info=True)
            await asyncio.sleep(sync_interval)


async def main():
    await process_campaign_contacts()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker de campaña detenido manualmente.")