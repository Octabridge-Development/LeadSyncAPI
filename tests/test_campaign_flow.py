# tests/test_campaign_flow.py
"""
Test de flujo completo para campañas: inserción, procesamiento y verificación de CampaignContact.
"""
import pytest
import asyncio
from app.services.queue_service import QueueService
from app.db.session import get_db_session
from app.db.models import CampaignContact, Campaign, Contact, Advisor, Channel, ContactState
from app.schemas.manychat import ManyChatCampaignAssignmentEvent
from sqlalchemy import select

@pytest.mark.asyncio
async def test_campaign_assignment_flow():
    queue_service = QueueService()
    await queue_service._ensure_queues_exist()
    # --- LIMPIEZA: eliminar datos previos para idempotencia y evitar errores de FK ---
    with get_db_session() as db:
        db.query(CampaignContact).delete()
        db.query(Campaign).filter(Campaign.name == "test-campaign-001").delete()
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
        # Crear Campaign dummy con channel_id válido
        campaign = Campaign(name="test-campaign-001", date_start="2025-06-01", date_end="2025-06-30", status="active", channel_id=channel.id)
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        # Crear Advisor dummy
        advisor = Advisor(name="Test Advisor", email="test@advisor.com", role="comercial", status="active")
        db.add(advisor)
        db.commit()
        db.refresh(advisor)
        contact_id = contact.id
        campaign_id = campaign.id
        advisor_id = advisor.id
    # --- ESPERA PARA VISIBILIDAD EN DB ---
    await asyncio.sleep(2)
    # --- ENVÍO EVENTO ---
    event = {
        "manychat_id": "test-lead-001",
        "campaign_id": str(campaign_id),
        "comercial_id": str(advisor_id),
        "datetime_actual": "2025-06-03T12:00:00Z",
        "ultimo_estado": "asignado",
        "tipo_asignacion": "manual"
    }
    await queue_service.send_message(event, queue_service.campaign_queue_name)
    await asyncio.sleep(5)
    # --- VERIFICACIÓN ---
    with get_db_session() as db:
        result = db.execute(
            select(CampaignContact).where(
                CampaignContact.contact_id == contact_id,
                CampaignContact.campaign_id == campaign_id
            )
        ).scalar_one_or_none()
        assert result is not None, "No se encontró el CampaignContact procesado"
        assert result.last_state == "asignado"
