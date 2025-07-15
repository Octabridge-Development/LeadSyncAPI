# app/schemas/campaign_contact.py

from pydantic import BaseModel, Field
from pydantic import ConfigDict
from datetime import datetime
from typing import Optional, ClassVar

class CampaignContactUpdate(BaseModel):
    """
    Esquema para la actualización de un registro de Campaign_Contact
    basado en el ManyChat ID del Contacto.

    Este esquema se utiliza para validar los datos que se esperan en el cuerpo
    de la solicitud PUT para actualizar la asignación de campaña de un contacto.
    """
    manychat_id: str = Field(..., description="ID de ManyChat del contacto a buscar")
    # CORRECCIÓN 2A: Añadir especificidad de campaña - campaign_id opcional al esquema 
    campaign_id: Optional[int] = Field(None, description="ID específico de campaña para la asignación a actualizar (opcional). Si no se proporciona, se intentará actualizar el registro de campaña más reciente para el contacto.") # 
    last_state: Optional[str] = Field(None, max_length=100, description="Último estado de la campaña-contacto")
    summary: Optional[str] = Field(None, description="Resumen de Conversación")

    model_config = ConfigDict(from_attributes=True)
    json_schema_extra: ClassVar[dict] = {
        "example": {
            "manychat_id": "psid_1234567890", # Ejemplo de un ManyChat ID
            "campaign_id": 10, # Ejemplo de un Campaign ID (opcional)
            "medical_advisor_id": 123,      # Ejemplo de un ID de asesor médico
            "medical_assignment_date": "2025-06-06T10:30:00Z", # Ejemplo de fecha y hora
            "last_state": "Asignado a Médico", # Ejemplo de estado
            "summary": "Cliente interesado en producto X. Conversación positiva."
        }
    }

class CampaignContactRead(BaseModel):
    id: int
    campaign_id: int
    contact_id: int
    commercial_advisor_id: Optional[int] = None
    registration_date: datetime
    commercial_assignment_date: Optional[datetime] = None
    commercial_process_start_date: Optional[datetime] = None
    medical_process_start_date: Optional[datetime] = None
    medical_process_end_date: Optional[datetime] = None
    quotation_start_date: Optional[datetime] = None
    sale_order_date: Optional[datetime] = None
    successful_sale_date: Optional[datetime] = None
    conversation_closed_date: Optional[datetime] = None
    last_state: Optional[str] = None
    lead_state: Optional[str] = None
    summary: Optional[str] = None

    class Config:
        orm_mode = True