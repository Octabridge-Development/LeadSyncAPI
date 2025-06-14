# tests/test_campaign_flow.py
from datetime import datetime, date
"""
Test de flujo completo para campañas: inserción, procesamiento y verificación de CampaignContact.
"""
import pytest
from unittest.mock import patch, AsyncMock
from app.services.queue_service import QueueService
from app.services.azure_sql_service import AzureSQLService
from app.db.session import get_db_session
from app.db.models import CampaignContact, Campaign, Contact, Advisor, Channel, ContactState
from app.schemas.manychat import ManyChatCampaignAssignmentEvent
from sqlalchemy import select

@pytest.mark.asyncio
async def test_campaign_assignment_flow():
    # Patch send_campaign_event_to_queue on QueueService globally, using create=True
    with patch.object(QueueService, 'send_campaign_event_to_queue', new_callable=AsyncMock, create=True) as mock_send_event:
        mock_send_event.return_value = None
        queue_service = QueueService(skip_queue_init=True)
        # --- LIMPIEZA: eliminar datos previos para idempotencia y evitar errores de FK ---
        with get_db_session() as db:
            db.query(CampaignContact).delete()
            db.query(Campaign).delete()  # Borra todos los Campaigns primero para evitar FK
            # Eliminar todos los ContactState de los Contact que referencian el Channel de prueba
            channel_ids = [c.id for c in db.query(Channel).filter(Channel.name == "Test Channel").all()]
            if channel_ids:
                contact_ids = [c.id for c in db.query(Contact).filter(Contact.channel_id.in_(channel_ids)).all()]
                if contact_ids:
                    db.query(ContactState).filter(ContactState.contact_id.in_(contact_ids)).delete(synchronize_session=False)
                db.query(Contact).filter(Contact.channel_id.in_(channel_ids)).delete(synchronize_session=False)
            db.query(Contact).filter(Contact.manychat_id == "test-lead-001").delete()
            db.query(Advisor).filter(Advisor.name == "Test Advisor").delete()
            db.query(Channel).filter(Channel.name == "Test Channel").delete()
            db.commit()
        # --- PREPARACIÓN: crear registros dummy válidos ---
        with get_db_session() as db:
            # Crear Channel dummy
            channel = Channel(name="Test Channel", description="Canal de prueba")
            db.add(channel)
            db.commit()
            db.refresh(channel)
            # Crear Contacto dummy
            contact = Contact(manychat_id="test-lead-001", first_name="Test", last_name="Lead", channel_id=channel.id)
            db.add(contact)
            db.commit()
            db.refresh(contact)
            # Crear Campaign dummy con nombre único
            campaign = Campaign(name="test-campaign-001", date_start=datetime(2025,6,1), date_end=datetime(2025,6,30), status="active", channel_id=channel.id)
            db.add(campaign)
            db.commit()
            db.refresh(campaign)
            # Crear Advisor dummy
            advisor = Advisor(name="Test Advisor", email="test@advisor.com", role="comercial")
            db.add(advisor)
            db.commit()
            db.refresh(advisor)
            contact_id = contact.id
            campaign_id = campaign.id
            advisor_id = advisor.id
        # --- ESPERA PARA VISIBILIDAD EN DB ---
        import asyncio
        await asyncio.sleep(2)
        # --- ENVÍO EVENTO ---
        event = {
            "manychat_id": "test-lead-001",
            "campaign_id": campaign.id,  # Usar el ID, no el nombre
            "comercial_id": str(advisor_id),
            "datetime_actual": "2025-06-03T12:00:00Z",
            "ultimo_estado": "asignado",
            "tipo_asignacion": "manual"
        }
        await queue_service.send_campaign_event_to_queue(event)
        # Simular procesamiento del evento como lo haría el worker
        azure_sql_service = AzureSQLService()
        event_obj = ManyChatCampaignAssignmentEvent(**event)
        await azure_sql_service.process_campaign_event(event_obj)
        # --- VERIFICACIÓN ---
        with get_db_session() as db:
            result = db.execute(
                select(CampaignContact).where(
                    CampaignContact.contact_id == contact_id,
                    CampaignContact.campaign_id == campaign_id
                )
            ).scalars().first()
            assert result is not None, "No se encontró el CampaignContact procesado"
            assert result.last_state == "asignado"
