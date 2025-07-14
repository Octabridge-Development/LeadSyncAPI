import asyncio
import json
import logging
import os
from app.services.queue_service import QueueService
from app.services.azure_sql_service import AzureSQLService
from app.services.odoo_crm_service import OdooCRMService
from app.schemas.crm import CRMLeadEvent

# Tabla de mapeo de etapas (sequence a stage_id)
STAGE_SEQUENCE_TO_ID = {
    0: 16,  # Recién Suscrito Sin Asignar
    1: 17,  # Recién Suscrito Pendiente AC
    2: 18,  # Retornó en AC
    3: 19,  # Comienza AC
    4: 20,  # Retorno a AE
    5: 21,  # Derivado a AE
    6: 22,  # Comienza AE
    7: 23,  # Terminó AE
    8: 24,  # No Termino AE Derivado AC
    9: 25,  # Comienza Cotización
    10: 26, # Orden de Venta Confirmada (CERRADA)
}

# Lista de stage_id válidos en Odoo
VALID_STAGE_IDS = {16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26}

class CRMProcessor:
    def __init__(self):
        self.queue_service = QueueService()
        self.azure_sql_service = AzureSQLService()
        self.odoo_crm_service = OdooCRMService()
        self.queue_name = self.queue_service.crm_queue_name
        self.sync_interval = int(os.getenv("SYNC_INTERVAL", 10))  # segundos entre ciclos

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
                    event = CRMLeadEvent(**data)
                except Exception as e:
                    logging.error(f"Error de validación de datos: {e}")
                    # Aquí podrías enviar a DLQ si lo deseas
                    await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                    continue
                # Validar stage_id recibido directamente
                stage_id = getattr(event.state, 'stage_id', None)
                if stage_id is None or stage_id not in VALID_STAGE_IDS:
                    logging.error(f"stage_id inválido: {stage_id}. Mensaje descartado.")
                    await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                    continue
                # Usar stage_id directamente en la llamada a Odoo
                await self.azure_sql_service.process_crm_lead_event(event)
                self.odoo_crm_service.create_or_update_lead(event)
                # Eliminar mensaje de la cola
                await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                logging.info(f"Processed CRM event for manychat_id: {event.manychat_id}")
            except Exception as e:
                logging.error(f"Error processing CRM event: {e}")
            await asyncio.sleep(self.sync_interval)  # Espera configurable entre ciclos

def main():
    logging.basicConfig(level=logging.INFO)
    processor = CRMProcessor()
    asyncio.run(processor.process())

if __name__ == "__main__":
    main()
