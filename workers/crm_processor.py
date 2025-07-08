import asyncio
import json
import logging
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

class CRMProcessor:
    def __init__(self):
        self.queue_service = QueueService()
        self.azure_sql_service = AzureSQLService()
        self.odoo_crm_service = OdooCRMService()
        self.queue_name = self.queue_service.crm_queue_name

    async def process(self):
        while True:
            try:
                message = await self.queue_service.receive_message(self.queue_name)
                if not message:
                    await asyncio.sleep(1)
                    continue
                data = json.loads(message.content)
                try:
                    event = CRMLeadEvent(**data)
                except Exception as e:
                    logging.error(f"Error de validación de datos: {e}")
                    # Aquí podrías enviar a DLQ si lo deseas
                    await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                    continue
                # Validar sequence
                sequence = getattr(event.state, 'sequence', None)
                if sequence is None or not (0 <= sequence <= 10):
                    logging.error(f"Sequence inválido: {sequence}. Mensaje descartado.")
                    await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                    continue
                # Guardar summary en Azure SQL (debe estar en event.state.summary)
                # Se asume que process_crm_lead_event lo maneja correctamente
                await self.azure_sql_service.process_crm_lead_event(event)
                # Sincronizar con Odoo CRM (el mapeo de etapas se hará en el servicio Odoo)
                await self.odoo_crm_service.create_or_update_lead(event)
                # Eliminar mensaje de la cola
                await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                logging.info(f"Processed CRM event for manychat_id: {event.manychat_id}")
            except Exception as e:
                logging.error(f"Error processing CRM event: {e}")
            await asyncio.sleep(1)  # Rate limiting

def main():
    logging.basicConfig(level=logging.INFO)
    processor = CRMProcessor()
    asyncio.run(processor.process())

if __name__ == "__main__":
    main()
