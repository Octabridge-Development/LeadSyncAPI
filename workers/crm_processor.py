
import asyncio
import json
import logging
import os
from app.services.queue_service import QueueService
from app.services.odoo_crm_opportunity_service import odoo_crm_opportunity_service
from app.schemas.crm_opportunity import CRMOpportunityEvent
from app.db.models import Channel, CampaignContact

# Configuración de logging robusta
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("crm_opportunity_worker")

class CRMProcessor:
    def __init__(self):
        self.queue_service = QueueService()
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
                    # El payload ya viene con los campos unificados, separar para cada tabla
                    manychat_id = data.get("manychat_id")
                    campaign_id = data.get("campaign_id")
                    state = data.get("state")
                    summary = data.get("summary")
                    assignment_type = data.get("assignment_type")
                    advisor_id = data.get("advisor_id")
                    assignment_datetime = data.get("assignment_datetime")

                    from app.db.session import SessionLocal
                    from app.db.repositories import ContactRepository, ContactStateRepository, CampaignContactRepository, AdvisorRepository, ChannelRepository
                    db = SessionLocal()
                    contact_repo = ContactRepository(db)
                    state_repo = ContactStateRepository(db)
                    campaign_contact_repo = CampaignContactRepository(db)
                    advisor_repo = AdvisorRepository(db)
                    channel_repo = ChannelRepository(db)
                    contact = contact_repo.get_by_manychat_id(manychat_id)
                    if not contact:
                        logger.error(f"No se encontró el contacto con manychat_id={manychat_id} en la BD. Se elimina el mensaje de la cola.")
                        await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                        continue

                    # Upsert ContactState
                    contact_state = state_repo.create_or_update(
                        contact_id=contact.id,
                        state=state,
                        category="manychat"
                    )

                    # Buscar nombre del asesor comercial o médico si corresponde
                    advisor_comercial_name = None
                    advisor_medico_name = None
                    # Buscar ambos asesores por sus IDs si existen en CampaignContact
                    campaign_contact_obj = db.query(CampaignContact).filter_by(contact_id=contact.id, campaign_id=campaign_id).first()
                    if campaign_contact_obj:
                        if campaign_contact_obj.commercial_advisor_id:
                            advisor_obj = advisor_repo.get_by_id_or_email(campaign_contact_obj.commercial_advisor_id)
                            advisor_comercial_name = advisor_obj.name if advisor_obj else None
                        if campaign_contact_obj.medical_advisor_id:
                            advisor_obj = advisor_repo.get_by_id_or_email(campaign_contact_obj.medical_advisor_id)
                            advisor_medico_name = advisor_obj.name if advisor_obj else None

                    # Buscar nombre del canal correctamente por ID
                    channel_name = None
                    if contact.channel_id:
                        channel_obj = db.query(Channel).filter_by(id=contact.channel_id).first()
                        channel_name = channel_obj.name if channel_obj else None

                    # Upsert CampaignContact
                    cc_data = {
                        "contact_id": contact.id,
                        "campaign_id": campaign_id,
                        "last_state": state,
                        "summary": summary,
                        "sync_status": "updated",
                    }
                    if assignment_type == "comercial":
                        cc_data["commercial_advisor_id"] = advisor_id
                        cc_data["commercial_assignment_date"] = assignment_datetime
                    elif assignment_type == "medico":
                        cc_data["medical_advisor_id"] = advisor_id
                        cc_data["medical_assignment_date"] = assignment_datetime
                    campaign_contact = campaign_contact_repo.create_or_update_assignment(cc_data)


                    # Lógica real de integración con Odoo
                    full_name = f"{contact.first_name} {contact.last_name or ''}".strip()
                    # Consultar el último estado real desde Contact_State
                    latest_state = state_repo.get_latest_by_contact(contact.id)
                    stage_manychat = latest_state.state if latest_state else state

                    # Mapeo de estado ManyChat a stage_id de Odoo
                    MANYCHAT_TO_ODOO_STAGE = {
                        "Recién Suscrito (Sin Asignar)": 16,
                        "Recién suscrito Pendiente de AC": 17,
                        "Retornó en AC": 18,
                        "Comienza Atención Comercial": 19,
                        "Retornó a Asesoría especializada": 20,
                        "Derivado Asesoría Médica": 21,
                        "Comienza Asesoría Médica": 22,
                        "Terminó Asesoría Médica": 23,
                        "No terminó Asesoría especializada Derivado a Comercial": 24,
                        "Comienza Cotización": 25,
                        "Orden de venta Confirmada": 26,
                    }
                    stage_odoo_id = MANYCHAT_TO_ODOO_STAGE.get(stage_manychat)
                    if not stage_odoo_id:
                        logger.error(f"No se pudo mapear el estado '{stage_manychat}' a un stage_id de Odoo. Se elimina el mensaje de la cola.")
                        db.close()
                        await self.queue_service.delete_message(self.queue_name, message.id, message.pop_receipt)
                        continue

                    logger.info(f"Creando/actualizando oportunidad en Odoo para contacto: {full_name}, manychat_id: {manychat_id}, stage: {stage_manychat}, stage_odoo_id: {stage_odoo_id}")
                    if odoo_crm_opportunity_service and stage_odoo_id:
                        try:
                            payload_odoo = {
                                "manychat_id": contact.manychat_id,
                                "contact_name": full_name,
                                "stage_odoo_id": stage_odoo_id,
                                "advisor_comercial_id": advisor_comercial_name,
                                "advisor_medico_id": advisor_medico_name,
                                "contact_email": contact.email,
                                "contact_phone": contact.phone,
                                "source_id": contact.channel_id,
                                "channel_name": channel_name,
                                "fecha_entrada": contact.entry_date,
                                "fecha_ultimo_estado": latest_state.created_at if latest_state else None
                            }
                            logger.info(f"Payload enviado a Odoo: {payload_odoo}")
                            opportunity_id = await odoo_crm_opportunity_service.create_or_update_opportunity(**payload_odoo)
                            logger.info(f"Oportunidad Odoo creada/actualizada con ID: {opportunity_id} para contacto {contact.id}")
                        except Exception as e:
                            logger.error(f"Error al crear/actualizar oportunidad Odoo para contacto {contact.id}: {e}")
                    else:
                        logger.error(f"No se pudo crear/actualizar oportunidad Odoo: servicio no disponible o stage no mapeado para contacto {contact.id}")

                    db.close()
                except Exception as e:
                    logger.error(f"Error al procesar evento unificado: {e} | Evento: {data}")
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
