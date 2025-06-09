# app/schemas/campaign_contact.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

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
    medical_advisor_id: Optional[int] = Field(None, description="ID del Médico/Asesor de la tabla Advisor")
    medical_assignment_date: Optional[datetime] = Field(None, description="Fecha y hora de asignación del médico. Si no se proporciona y la columna está vacía, se usará la fecha y hora UTC actuales.")
    last_state: Optional[str] = Field(None, max_length=100, description="Último estado de la campaña-contacto")

    class Config:
        # Permite que el modelo se use con objetos ORM (SQLAlchemy)
        from_attributes = True # Equivalente a orm_mode = True en Pydantic v1
        
        json_schema_extra = {
            "example": {
                "manychat_id": "psid_1234567890", # Ejemplo de un ManyChat ID
                "campaign_id": 10, # Ejemplo de un Campaign ID (opcional)
                "medical_advisor_id": 123,      # Ejemplo de un ID de asesor médico
                "medical_assignment_date": "2025-06-06T10:30:00Z", # Ejemplo de fecha y hora
                "last_state": "Asignado a Médico" # Ejemplo de estado
            }
        }