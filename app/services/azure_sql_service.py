from app.db.session import get_db_session
from app.db.repositories import (
    ContactRepository, ContactStateRepository, ChannelRepository,
    CampaignRepository, AdvisorRepository, CampaignContactRepository # Agregado [cite: 5]
)
from app.schemas.manychat import ManyChatContactEvent, ManyChatCampaignAssignmentEvent # Agregado [cite: 3]
from datetime import datetime
import logging

class AzureSQLService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def process_contact_event(self, event: ManyChatContactEvent) -> dict:
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

    async def process_campaign_event(self, event: ManyChatCampaignAssignmentEvent) -> dict: # Agregado [cite: 3]
        """Procesa evento de asignación de campaña"""
        try:
            with get_db_session() as db:
                contact_repo = ContactRepository(db)
                campaign_repo = CampaignRepository(db)
                advisor_repo = AdvisorRepository(db)
                campaign_contact_repo = CampaignContactRepository(db)

                # 1. Buscar contacto existente por manychat_id [cite: 3]
                contact = contact_repo.get_by_manychat_id(event.manychat_id)
                if not contact:
                    self.logger.warning(f"Contacto con manychat_id {event.manychat_id} no encontrado para evento de campaña. Este evento será omitido.")
                    # Dependiendo de la lógica de negocio, se podría lanzar una excepción o crear un contacto mínimo.
                    # Por ahora, simplemente se informa y se levanta un error para un manejo explícito.
                    raise ValueError(f"Contact with manychat_id {event.manychat_id} not found for campaign assignment.")

                # 2. Buscar Campaign por campaign_id (ahora se espera que event.campaign_id sea int)
                campaign = campaign_repo.get_by_id(event.campaign_id)
                if not campaign:
                    raise ValueError(f"Campaign with id {event.campaign_id} not found.")

                # 3. Crear/buscar Advisor (comercial_id) [cite: 3]
                commercial_advisor = None
                if event.comercial_id:
                    commercial_advisor = advisor_repo.get_by_id_or_email(event.comercial_id)
                    if not commercial_advisor:
                        self.logger.warning(f"Asesor comercial con ID/email {event.comercial_id} no encontrado para campaña {event.campaign_id}. No se asignará asesor comercial.")
                        # Puedes decidir si esto es un error crítico o si se puede omitir la asignación del asesor.

                # Opcional: Crear/buscar Advisor (medico_id) [cite: 3]
                medical_advisor = None
                # Asegúrate de que ManyChatCampaignAssignmentEvent tenga 'medico_id'
                if hasattr(event, 'medico_id') and event.medico_id:
                    medical_advisor = advisor_repo.get_by_id_or_email(event.medico_id)
                    if not medical_advisor:
                        self.logger.warning(f"Asesor médico con ID/email {event.medico_id} no encontrado para campaña {event.campaign_id}. No se asignará asesor médico.")

                # 4. Crear/actualizar Campaign_Contact [cite: 3]
                campaign_contact_data = {
                    "contact_id": contact.id,
                    "campaign_id": campaign.id,
                    "commercial_advisor_id": commercial_advisor.id if commercial_advisor else None,
                    "medical_advisor_id": medical_advisor.id if medical_advisor else None,
                    "registration_date": event.datetime_actual,
                    "last_state": event.ultimo_estado,
                    "lead_state": event.tipo_asignacion # Asumiendo que 'tipo_asignacion' se mapea a 'lead_state'
                }
                campaign_contact = campaign_contact_repo.create_or_update_assignment(campaign_contact_data)

                self.logger.info(f"Evento de campaña procesado exitosamente para contacto {contact.manychat_id}, campaña {campaign.name}")

                return {
                    "campaign_contact_id": campaign_contact.id,
                    "status": "success"
                }

        except Exception as e:
            self.logger.error(f"Error procesando evento de campaña: {str(e)}", exc_info=True)
            raise