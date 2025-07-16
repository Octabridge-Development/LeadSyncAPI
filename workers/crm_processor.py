
import asyncio
import json
import logging
import os
from app.services.queue_service import QueueService
from app.services.azure_sql_service import AzureSQLService
from app.schemas.crm_opportunity import CRMOpportunityEvent

# Configuración de logging robusta
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("crm_opportunity_worker")

class CRMProcessor:
    def __init__(self):
        self.queue_service = QueueService()
        self.azure_sql_service = AzureSQLService()
        self.queue_name = self.queue_service.crm_queue_name
        self.sync_interval = int(os.getenv("SYNC_INTERVAL", 10))

    async def process(self):
        logger.info("Iniciando worker de oportunidades CRM → Odoo...")
        while True:
            try:
                message = await self.queue_service.receive_message(self.queue_name)
                if not message:
                    logger.info(f"No hay mensajes en la cola '{self.queue_name}'. Esperando {self.sync_interval} segundos...")
                    await asyncio.sleep(self.sync_interval)
                    continue
                data = json.loads(message.content)
                try:
                    event = CRMOpportunityEvent(**data)
                except Exception as e:
                    logger.error(f"Error de validación de datos: {e} | Datos: {data}")
                    await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                    continue
                # Obtener Contact y último ContactState
                from app.db.session import SessionLocal
                from app.db.repositories import ContactRepository, ContactStateRepository
                db = SessionLocal()
                try:
                    contact_repo = ContactRepository(db)
                    state_repo = ContactStateRepository(db)
                    contact = contact_repo.get_by_manychat_id(event.manychat_id)
                    if not contact:
                        logger.error(f"No se encontró el contacto con manychat_id={event.manychat_id} en la BD. Se elimina el mensaje de la cola.")
                        await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                        return
                    if contact.odoo_sync_status != "pending":
                        logger.info(f"Contacto manychat_id={event.manychat_id} ya sincronizado (odoo_sync_status={contact.odoo_sync_status}). Se elimina el mensaje de la cola.")
                        await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                        return
                    # Obtener el último estado
                    contact_state = state_repo.get_latest_by_contact(contact.id)
                    # Preparar datos para Odoo
                    full_name = f"{contact.first_name} {contact.last_name or ''}".strip()
                    stage_manychat = contact_state.state if contact_state else event.stage_manychat
                    # Lógica de integración con Odoo
                    logger.info(f"Creando oportunidad en Odoo para contacto: {full_name}, manychat_id: {contact.manychat_id}, stage: {stage_manychat}")
                    # Aquí deberías llamar a tu servicio real de Odoo:
                    result = await self.azure_sql_service.process_crm_opportunity_event(event)
                    logger.info(f"Resultado de sincronización Odoo: {result}")
                    # Actualizar odoo_sync_status a 'synced' si fue exitoso
                    contact_repo.update_odoo_sync_status(contact.manychat_id, "synced")
                    db.close()
                except Exception as e:
                    logger.error(f"Error al sincronizar oportunidad con Odoo: {e} | Evento: {event.dict()}")
                    db.close()
                await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                await asyncio.sleep(1)  # Rate limit Odoo
            except Exception as e:
                logger.error(f"Error en el procesamiento del worker CRM: {e}")
                await asyncio.sleep(self.sync_interval)

def main():
    """
    Punto de entrada profesional para el worker CRM.
    Inicializa el event loop y ejecuta el procesamiento asíncrono con manejo robusto de errores.
    """
    logger.info("Arrancando el worker CRM de oportunidades...")
    processor = CRMProcessor()
    try:
        asyncio.run(processor.process())
    except KeyboardInterrupt:
        logger.info("Worker CRM detenido por el usuario (KeyboardInterrupt). Cerrando...")
    except Exception as e:
        logger.error(f"Fallo crítico en el worker CRM: {e}")

if __name__ == "__main__":
    main()
