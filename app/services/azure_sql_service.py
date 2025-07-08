from app.db.session import get_db_session
from app.db.repositories import (
    ContactRepository, ContactStateRepository, ChannelRepository,
    CampaignRepository, AdvisorRepository, CampaignContactRepository 
)
from app.schemas.manychat import ManyChatContactEvent, ManyChatCampaignAssignmentEvent 
from app.db.models import Contact # Importa el modelo Contact, que tiene odoo_contact_id y odoo_sync_status
from typing import Optional
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

                # Prepare contact data for the Contact model
                contact_data = {
                    "manychat_id": event.manychat_id,
                    "first_name": event.nombre_lead,
                    "last_name": event.apellido_lead,
                    "phone": event.whatsapp,
                    "email": event.email_lead, # <--- CAMBIO: Mapea el email desde el evento de ManyChat
                    "subscription_date": event.datetime_suscripcion,
                    "entry_date": event.datetime_actual,
                    "channel_id": channel.id if channel else None,
                    "initial_state": event.estado_inicial
                }

                # Upsert contact
                contact = contact_repo.create_or_update(contact_data)

                # Create contact state (always log new states)
                state = state_repo.create(
                    contact_id=contact.id,
                    state=event.ultimo_estado,
                    category="manychat"
                )

                self.logger.info(f"Processed ManyChat event for contact {contact.manychat_id}. Contact ID in DB: {contact.id}")

                return {
                    "contact_id": contact.id,
                    "state_id": state.id,
                    "status": "success",
                    "manychat_id": contact.manychat_id, 
                    "odoo_contact_id": contact.odoo_contact_id, # Retorna el ID de Odoo si ya lo tenía
                    "odoo_sync_status": contact.odoo_sync_status # Retorna el estado de sincronización
                }

        except Exception as e:
            self.logger.error(f"Error processing ManyChat contact event: {str(e)}", exc_info=True)
            raise

    async def process_campaign_event(self, event: ManyChatCampaignAssignmentEvent) -> dict:
        """Procesa evento de asignación de campaña"""
        try:
            with get_db_session() as db:
                contact_repo = ContactRepository(db)
                campaign_repo = CampaignRepository(db)
                advisor_repo = AdvisorRepository(db)
                campaign_contact_repo = CampaignContactRepository(db)

                # 1. Buscar contacto existente por manychat_id
                contact = contact_repo.get_by_manychat_id(event.manychat_id)
                if not contact:
                    self.logger.warning(f"Contacto con manychat_id {event.manychat_id} no encontrado para evento de campaña. Este evento será omitido.")
                    raise ValueError(f"Contact with manychat_id {event.manychat_id} not found for campaign assignment.")

                # 2. Buscar Campaign por campaign_id (ahora se espera que event.campaign_id sea int)
                campaign = campaign_repo.get_by_id(event.campaign_id)
                if not campaign:
                    self.logger.warning(f"Campaña con ID {event.campaign_id} no encontrada para asignación de ManyChat ID {event.manychat_id}.")
                    raise ValueError(f"Campaign with id {event.campaign_id} not found.")

                # 3. Crear/buscar Advisor (comercial_id)
                commercial_advisor = None
                if event.comercial_id:
                    commercial_advisor = advisor_repo.get_by_id_or_email(event.comercial_id)
                    if not commercial_advisor:
                        self.logger.warning(f"Asesor comercial con ID/email {event.comercial_id} no encontrado para campaña {event.campaign_id}. No se asignará asesor comercial.")

                # Opcional: Crear/buscar Advisor (medico_id)
                medical_advisor = None
                if hasattr(event, 'medico_id') and event.medico_id:
                    medical_advisor = advisor_repo.get_by_id_or_email(event.medico_id)
                    if not medical_advisor:
                        self.logger.warning(f"Asesor médico con ID/email {event.medico_id} no encontrado para campaña {event.campaign_id}. No se asignará asesor médico.")

                # 4. Crear/actualizar Campaign_Contact
                campaign_contact_data = {
                    "contact_id": contact.id,
                    "campaign_id": campaign.id,
                    "commercial_advisor_id": commercial_advisor.id if commercial_advisor else None,
                    "medical_advisor_id": medical_advisor.id if medical_advisor else None,
                    "registration_date": event.datetime_actual,
                    "last_state": event.ultimo_estado,
                    "lead_state": event.tipo_asignacion # Asumiendo que 'tipo_asignacion' se mapea a 'lead_state'
                }
                # Incluir summary si viene en el evento
                if hasattr(event, "summary") and event.summary is not None:
                    campaign_contact_data["summary"] = event.summary
                campaign_contact = campaign_contact_repo.create_or_update_assignment(campaign_contact_data)

                self.logger.info(f"Evento de campaña procesado exitosamente para contacto {contact.manychat_id}, campaña {campaign.name}. CampaignContact ID: {campaign_contact.id}")

                return {
                    "campaign_contact_id": campaign_contact.id,
                    "status": "success"
                }

        except Exception as e:
            self.logger.error(f"Error procesando evento de campaña: {str(e)}", exc_info=True)
            raise

    async def process_crm_lead_event(self, event) -> dict:
        """
        Procesa un evento CRMLeadEvent y registra el tracking en Azure SQL.
        Reutiliza lógica de contacto y agrega tracking específico de CRM.
        """
        try:
            with get_db_session() as db:
                contact_repo = ContactRepository(db)
                # Buscar o crear contacto por manychat_id
                contact = contact_repo.get_by_manychat_id(event.manychat_id)
                if not contact:
                    # Si no existe, crea un nuevo contacto mínimo
                    contact_data = {
                        "manychat_id": event.manychat_id,
                        "first_name": event.first_name,
                        "last_name": event.last_name,
                        "phone": event.phone,
                        "entry_date": event.entry_date,
                        "channel": event.channel,
                        "medical_advisor_id": event.medical_advisor_id,
                        "commercial_advisor_id": event.commercial_advisor_id
                    }
                    contact = contact_repo.create(contact_data)
                # Aquí podrías agregar tracking específico de CRM (por ejemplo, guardar el estado del lead)
                # TODO: Implementar tabla/log de estados de lead CRM si es necesario
                self.logger.info(f"Processed CRM event for contact {contact.manychat_id} (CRM tracking not fully implemented)")
                return {"contact_id": contact.id, "status": "success", "manychat_id": contact.manychat_id}
        except Exception as e:
            self.logger.error(f"Error processing CRM lead event: {str(e)}", exc_info=True)
            raise

    def update_odoo_sync_status(self, manychat_id: str, status: str, odoo_contact_id: Optional[str] = None) -> Optional[Contact]:
        """
        Actualiza el estado de sincronización y el odoo_contact_id en un contacto de Azure SQL.
        Utiliza el ContactRepository.
        """
        with get_db_session() as db:
            contact_repo = ContactRepository(db)
            return contact_repo.update_odoo_sync_status(manychat_id, status, odoo_contact_id)