from app.db.session import get_db_session
from app.db.repositories import ContactRepository, ContactStateRepository, ChannelRepository
from app.schemas.manychat import ManyChatWebhookEvent
from datetime import datetime
import logging

class AzureSQLService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def process_manychat_event(self, event: ManyChatWebhookEvent) -> dict:
        """Process ManyChat event and save to Azure SQL"""
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