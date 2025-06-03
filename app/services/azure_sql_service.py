from app.db.session import get_db_session
from app.db.repositories import ContactRepository, ContactStateRepository, ChannelRepository, CampaignContactRepository
from app.db.models import Campaign, Advisor, CampaignContact, Contact
from app.schemas.manychat import ManyChatContactEvent, ManyChatCampaignAssignmentEvent
from datetime import datetime
import logging

class AzureSQLService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def process_contact_event(self, event: ManyChatContactEvent) -> dict: # <-- CAMBIO AQUÍ (nombre del método y tipo de evento)
        """Process ManyChat contact event and save to Azure SQL"""
        try:
            with get_db_session() as db:
                # Initialize repositories
                contact_repo = ContactRepository(db)
                state_repo = ContactStateRepository(db)
                channel_repo = ChannelRepository(db)

                # Process channel
                channel = None
                if event.canal_entrada:
                    channel = channel_repo.get_or_create_by_name(event.canal_entrada)

                # Prepare contact data
                contact_data = {
                    "manychat_id": event.manychat_id,
                    "first_name": event.nombre_lead,
                    "last_name": event.apellido_lead,
                    "phone": event.whatsapp,
                    "subscription_date": event.datetime_suscripcion,
                    "entry_date": event.datetime_actual,
                    "channel_id": channel.id if channel else None,
                    "initial_state": event.estado_inicial
                }

                # Upsert contact
                contact = contact_repo.create_or_update(contact_data)

                # Create contact state
                state = state_repo.create(
                    contact_id=contact.id,
                    state=event.ultimo_estado,
                    category="manychat"
                )

                self.logger.info(f"Processed ManyChat event for contact {contact.manychat_id}")

                return {
                    "contact_id": contact.id,
                    "state_id": state.id,
                    "status": "success"
                }

        except Exception as e:
            self.logger.error(f"Error processing ManyChat event: {str(e)}")
            raise

    async def process_campaign_event(self, event: ManyChatCampaignAssignmentEvent) -> dict:
        """Procesa un evento de asignación de campaña y guarda CampaignContact en Azure SQL"""
        try:
            self.logger.info(f"[process_campaign_event] INICIO: manychat_id={event.manychat_id}, campaign_id={event.campaign_id}, comercial_id={event.comercial_id}, medico_id={event.medico_id}")
            with get_db_session() as db:
                # Buscar Contacto por manychat_id
                contact = db.query(Contact).filter(Contact.manychat_id == event.manychat_id).first()
                self.logger.info(f"[process_campaign_event] Contacto encontrado: {contact}")
                if not contact:
                    self.logger.error(f"[process_campaign_event] No se encontró Contact con manychat_id={event.manychat_id}")
                    raise Exception(f"No se encontró Contact con manychat_id={event.manychat_id}")
                # Buscar Campaign por id
                campaign = db.query(Campaign).filter(Campaign.id == int(event.campaign_id)).first()
                self.logger.info(f"[process_campaign_event] Campaign encontrado: {campaign}")
                if not campaign:
                    self.logger.error(f"[process_campaign_event] No se encontró Campaign con id={event.campaign_id}")
                    raise Exception(f"No se encontró Campaign con id={event.campaign_id}")
                # Buscar Advisor comercial (si aplica)
                commercial_advisor = None
                if event.comercial_id:
                    commercial_advisor = db.query(Advisor).filter(Advisor.id == int(event.comercial_id)).first()
                    self.logger.info(f"[process_campaign_event] Advisor comercial encontrado: {commercial_advisor}")
                # Buscar Advisor médico (si aplica)
                medical_advisor = None
                if event.medico_id:
                    medical_advisor = db.query(Advisor).filter(Advisor.id == int(event.medico_id)).first()
                    self.logger.info(f"[process_campaign_event] Advisor médico encontrado: {medical_advisor}")
                # Usar CampaignContactRepository para upsert
                from app.db.repositories import CampaignContactRepository
                campaign_contact_repo = CampaignContactRepository(db)
                self.logger.info(f"[process_campaign_event] Intentando crear/upsert CampaignContact: campaign_id={campaign.id}, contact_id={contact.id}")
                campaign_contact = campaign_contact_repo.create_or_update(
                    campaign_id=campaign.id,
                    contact_id=contact.id,
                    commercial_advisor_id=commercial_advisor.id if commercial_advisor else None,
                    medical_advisor_id=medical_advisor.id if medical_advisor else None,
                    last_state=event.ultimo_estado,
                    lead_state=event.tipo_asignacion
                )
                self.logger.info(f"[process_campaign_event] CampaignContact creado/upserted: {campaign_contact}")
                return {
                    "campaign_contact_id": campaign_contact.id,
                    "status": "success"
                }
        except Exception as e:
            self.logger.error(f"[process_campaign_event] Error: {str(e)}", exc_info=True)
            raise