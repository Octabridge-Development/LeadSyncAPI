from app.db.session import get_db_session
from app.db.repositories import (
    ContactRepository, ContactStateRepository, ChannelRepository,
    CampaignRepository, AdvisorRepository, CampaignContactRepository 
)
# [AÑADIDO] Importa el schema de CRM para el type hinting
from app.schemas.crm import CRMLeadEvent
from app.schemas.manychat import ManyChatContactEvent, ManyChatCampaignAssignmentEvent 
from app.schemas.crm_opportunity import CRMOpportunityEvent
from app.db.models import Contact # Importa el modelo Contact, que tiene odoo_contact_id y odoo_sync_status
from typing import Optional
import logging

class AzureSQLService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def process_contact_event(self, event: ManyChatContactEvent) -> dict:
        """
        Procesa un evento de contacto recibido desde ManyChat y lo guarda en Azure SQL.
        - Crea o actualiza el contacto.
        - Registra el estado inicial en Contact_State.
        """
        try:
            with get_db_session() as db:
                contact_repo = ContactRepository(db)
                state_repo = ContactStateRepository(db)
                channel_repo = ChannelRepository(db)

                channel = None
                if event.canal_entrada:
                    channel = channel_repo.get_or_create_by_name(event.canal_entrada)

                contact_data = {
                    "manychat_id": event.manychat_id,
                    "first_name": event.nombre_lead,
                    "last_name": event.apellido_lead,
                    "phone": event.whatsapp,
                    "email": event.email_lead,
                    "subscription_date": event.datetime_suscripcion,
                    "entry_date": event.datetime_actual,
                    "channel_id": channel.id if channel else None,
                    "initial_state": event.estado_inicial
                }
                contact = contact_repo.create_or_update(contact_data)
                state = state_repo.create(
                    contact_id=contact.id,
                    state=event.ultimo_estado,
                    category="manychat"
                )
                self.logger.info(f"Contacto ManyChat procesado y guardado en Azure SQL. Contact ID: {contact.id}, State ID: {state.id}")
                return {
                    "contact_id": contact.id,
                    "state_id": state.id,
                    "status": "success",
                    "manychat_id": contact.manychat_id,
                }
        except Exception as e:
            self.logger.error(f"Error procesando evento de contacto ManyChat: {str(e)}", exc_info=True)
            raise

    async def process_campaign_event(self, event: ManyChatCampaignAssignmentEvent) -> dict:
        """
        Procesa un evento de asignación de campaña desde ManyChat y lo guarda en Azure SQL.
        - Asocia el contacto con la campaña y asesores.
        """
        try:
            with get_db_session() as db:
                contact_repo = ContactRepository(db)
                campaign_repo = CampaignRepository(db)
                advisor_repo = AdvisorRepository(db)
                campaign_contact_repo = CampaignContactRepository(db)

                contact = contact_repo.get_by_manychat_id(event.manychat_id)
                if not contact:
                    self.logger.warning(f"Contacto con manychat_id {event.manychat_id} no encontrado para evento de campaña.")
                    raise ValueError(f"Contact with manychat_id {event.manychat_id} not found for campaign assignment.")

                campaign = campaign_repo.get_by_id(event.campaign_id)
                if not campaign:
                    self.logger.warning(f"Campaña con ID {event.campaign_id} no encontrada para asignación de ManyChat ID {event.manychat_id}.")
                    raise ValueError(f"Campaign with id {event.campaign_id} not found.")

                commercial_advisor = None
                if event.comercial_id:
                    commercial_advisor = advisor_repo.get_by_id_or_email(event.comercial_id)
                    if not commercial_advisor:
                        self.logger.warning(f"Asesor comercial con ID/email {event.comercial_id} no encontrado para campaña {event.campaign_id}.")

                medical_advisor = None
                if hasattr(event, 'medico_id') and event.medico_id:
                    medical_advisor = advisor_repo.get_by_id_or_email(event.medico_id)
                    if not medical_advisor:
                        self.logger.warning(f"Asesor médico con ID/email {event.medico_id} no encontrado para campaña {event.campaign_id}.")

                campaign_contact_data = {
                    "contact_id": contact.id,
                    "campaign_id": campaign.id,
                    "commercial_advisor_id": commercial_advisor.id if commercial_advisor else None,
                    "medical_advisor_id": medical_advisor.id if medical_advisor else None,
                    "registration_date": event.datetime_actual,
                    "last_state": event.ultimo_estado,
                    "lead_state": event.tipo_asignacion
                }
                if hasattr(event, "summary") and event.summary is not None:
                    campaign_contact_data["summary"] = event.summary
                campaign_contact = campaign_contact_repo.create_or_update_assignment(campaign_contact_data)
                self.logger.info(f"Evento de campaña procesado y guardado en Azure SQL. Contact ID: {contact.id}, CampaignContact ID: {campaign_contact.id}")
                return {
                    "campaign_contact_id": campaign_contact.id,
                    "status": "success"
                }
        except Exception as e:
            self.logger.error(f"Error procesando evento de campaña: {str(e)}", exc_info=True)
            raise

    # --- [BLOQUE AÑADIDO] ---
    async def process_crm_lead_event(self, event: CRMLeadEvent) -> dict:
        """
        Procesa un evento de CRM para tracking en Azure SQL.
        - Registra el estado del lead en Contact_State con categoría 'crm'.
        """
        try:
            with get_db_session() as db:
                contact_repo = ContactRepository(db)
                state_repo = ContactStateRepository(db)

                contact = contact_repo.get_by_manychat_id(event.manychat_id)
                if not contact:
                    self.logger.warning(f"Contacto con manychat_id {event.manychat_id} no encontrado para evento de CRM.")
                    raise ValueError(f"Contact not found for CRM event tracking: {event.manychat_id}")

                state_summary = f"Stage {event.state.stage_id}: {event.state.summary or 'Update'}"
                state = state_repo.create(
                    contact_id=contact.id,
                    state=state_summary,
                    category="crm"
                )
                self.logger.info(f"Evento de CRM registrado en Azure SQL. Contact ID: {contact.id}, State ID: {state.id}")
                return {"status": "success", "contact_id": contact.id, "state_id": state.id}
        except Exception as e:
            self.logger.error(f"Error procesando evento de tracking CRM: {str(e)}", exc_info=True)
            raise

    async def process_crm_opportunity_event(self, event: CRMOpportunityEvent) -> dict:
        """
        Procesa un evento de oportunidad CRM:
        - Registra el estado en Contact_State (Azure SQL)
        - Actualiza el campo initial_state del contacto
        - Traduce el stage ManyChat a ID Odoo y crea/actualiza la oportunidad en Odoo
        """
        from app.services.odoo_crm_opportunity_service import odoo_crm_opportunity_service
        try:
            with get_db_session() as db:
                contact_repo = ContactRepository(db)
                state_repo = ContactStateRepository(db)
                contact = contact_repo.get_by_manychat_id(event.manychat_id)
                if not contact:
                    self.logger.warning(f"Contacto con manychat_id {event.manychat_id} no encontrado para evento de oportunidad CRM.")
                    raise ValueError(f"Contact not found for CRM opportunity event: {event.manychat_id}")
                # Actualizar el campo initial_state del contacto
                contact.initial_state = event.stage_manychat
                db.add(contact)
                db.commit()
                db.refresh(contact)
                # Guardar el estado exactamente como se recibe de ManyChat (stage_manychat)
                state = state_repo.create_or_update(
                    contact_id=contact.id,
                    state=event.stage_manychat,
                    category="crm"
                )
                self.logger.info(f"Evento de oportunidad CRM registrado en Azure SQL y estado principal actualizado. Contact ID: {contact.id}, State ID: {state.id}")

                # --- Lógica de integración con Odoo ---
                stage_odoo_id = event.stage_odoo_id
                if not stage_odoo_id:
                    self.logger.warning(f"No se encontró mapeo de stage Odoo para '{event.stage_manychat}'. No se sincroniza con Odoo.")
                    return {"status": "success", "contact_id": contact.id, "state_id": state.id, "odoo": "skipped_no_stage_mapping"}

                # Se puede usar el nombre del contacto y otros datos si están disponibles
                opportunity_name = f"{contact.first_name} {contact.last_name or ''}".strip() or f"Oportunidad {event.manychat_id}"
                advisor_odoo_id = None
                if event.advisor_id:
                    try:
                        advisor_odoo_id = int(event.advisor_id)
                    except Exception:
                        self.logger.warning(f"advisor_id '{event.advisor_id}' no es un entero válido para Odoo.")

                # Llamar a Odoo para crear/actualizar la oportunidad
                try:
                    odoo_id = await odoo_crm_opportunity_service.create_or_update_opportunity(
                        manychat_id=event.manychat_id,
                        opportunity_name=opportunity_name,
                        stage_odoo_id=stage_odoo_id,
                        advisor_odoo_id=advisor_odoo_id,
                        contact_name=opportunity_name,  # Usar el nombre completo ya construido
                        contact_email=contact.email,
                        contact_phone=contact.phone
                    )
                    self.logger.info(f"Oportunidad sincronizada con Odoo. Odoo ID: {odoo_id}")
                    return {"status": "success", "contact_id": contact.id, "state_id": state.id, "odoo_id": odoo_id}
                except Exception as e:
                    self.logger.error(f"Error al sincronizar oportunidad con Odoo: {str(e)}", exc_info=True)
                    return {"status": "success", "contact_id": contact.id, "state_id": state.id, "odoo_error": str(e)}
        except Exception as e:
            self.logger.error(f"Error procesando evento de oportunidad CRM: {str(e)}", exc_info=True)
            raise
    # --- [FIN DEL BLOQUE AÑADIDO] ---

    # Método de sincronización con Odoo eliminado. Solo lógica de Azure SQL para contactos.