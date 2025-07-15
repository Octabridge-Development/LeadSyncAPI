import asyncio
import json
import logging
import os
from app.services.queue_service import QueueService
from app.services.azure_sql_service import AzureSQLService
from app.services.odoo_crm_service import OdooCRMService
from app.schemas.crm_opportunity import CRMOpportunityEvent, MANYCHAT_TO_ODOO_STAGE_ID

class CRMProcessor:
    def __init__(self):
        self.queue_service = QueueService()
        self.azure_sql_service = AzureSQLService()
        self.odoo_crm_service = OdooCRMService()
        self.queue_name = self.queue_service.crm_queue_name
        self.sync_interval = int(os.getenv("SYNC_INTERVAL", 10))

    async def process(self):
        while True:
            try:
                message = await self.queue_service.receive_message(self.queue_name)
                if not message:
                    logging.info(f"No hay mensajes en la cola '{self.queue_name}'. Esperando {self.sync_interval} segundos...")
                    await asyncio.sleep(self.sync_interval)
                    continue
                data = json.loads(message.content)
                try:
                    event = CRMOpportunityEvent(**data)
                except Exception as e:
                    logging.error(f"Error de validación de datos: {e}")
                    await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                    continue
                # Mapeo de stage ManyChat → Odoo stage_id
                stage_id = event.get_odoo_stage_id()
                if stage_id is None:
                    logging.error(f"Stage ManyChat '{event.stage_manychat}' no tiene mapeo a Odoo stage_id. Evento registrado para auditoría.")
                    await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                    continue
                event.stage_odoo_id = stage_id
                # Registrar en Azure SQL para auditoría
                await self.azure_sql_service.process_crm_opportunity_event(event)
                # Crear/actualizar oportunidad en Odoo CRM
                self.odoo_crm_service.create_or_update_opportunity(event)
                await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
            except Exception as e:
                logging.error(f"Error en el procesamiento del worker CRM: {e}")
                await asyncio.sleep(self.sync_interval)
