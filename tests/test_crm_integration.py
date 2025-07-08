import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.queue_service import QueueService
from app.services.azure_sql_service import AzureSQLService
from app.services.odoo_crm_service import OdooCRMService
from app.schemas.crm import CRMLeadEvent
from workers.crm_processor import CRMProcessor

@pytest.mark.asyncio
async def test_create_new_lead(monkeypatch):
    # Simula un evento ManyChat válido para crear un lead nuevo
    event_data = {
        "manychat_id": "test123",
        "first_name": "Test",
        "last_name": "User",
        "phone": "+51999999999",
        "channel": "WhatsApp",
        "entry_date": "2025-07-07T10:00:00Z",
        "medical_advisor_id": 1,
        "commercial_advisor_id": 2,
        "state": {
            "sequence": 3,
            "summary": "Cliente interesado en plan anual",
            "date": "2025-07-07T10:10:00Z"
        }
    }
    event = CRMLeadEvent(**event_data)

    # Mock servicios
    queue_service = AsyncMock(spec=QueueService)
    azure_sql_service = AsyncMock(spec=AzureSQLService)
    odoo_crm_service = AsyncMock(spec=OdooCRMService)
    queue_service.receive_message.return_value = AsyncMock(content=str(event_data), id="msgid", pop_receipt="popr")
    queue_service.delete_message.return_value = None
    azure_sql_service.process_crm_lead_event.return_value = None
    odoo_crm_service.create_or_update_lead.return_value = None

    processor = CRMProcessor()
    processor.queue_service = queue_service
    processor.azure_sql_service = azure_sql_service
    processor.odoo_crm_service = odoo_crm_service

    # Ejecuta un ciclo del worker
    with patch("asyncio.sleep", return_value=None):
        await processor.process()

# Más tests: actualización, múltiples oportunidades, secuencia inválida, etc.
# Se pueden agregar funciones similares para cubrir los otros escenarios críticos.
