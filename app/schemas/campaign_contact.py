# app/schemas/campaign_contact.py

from pydantic import BaseModel, Field
from pydantic import ConfigDict
from datetime import datetime, timezone
from typing import Optional, ClassVar, Dict, Any

class CampaignContactUpsert(BaseModel):
    """
    Esquema para la asignación de campaña y actualización de estado desde ManyChat.
    Mapea los campos que ManyChat envía a las tablas Contact_State y Campaign_Contact.
    """
    # Campos obligatorios
    manychat_id: str = Field(..., description="ID de ManyChat del contacto")
    campaign_id: int = Field(..., description="ID de la campaña")
    state: str = Field(..., description="Estado actual del contacto en ManyChat")
    registration_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Fecha de registro del contacto en la campaña")
    
    # Campos de asignación de asesores
    comercial_id: Optional[int] = Field(None, description="ID del asesor comercial")
    medico_id: Optional[int] = Field(None, description="ID del asesor médico")
    # tipo_asignacion eliminado temporalmente, se usará en el futuro
    fecha_asignacion: datetime = Field(..., description="Fecha y hora de la asignación del asesor")
    
    # Campos opcionales
    category: str = Field(default="manychat", description="Categoría del estado (default: manychat)")
    summary: Optional[str] = Field(None, description="Notas o comentarios adicionales")

    class Config:
        json_schema_extra = {
            "example": {
                "manychat_id": "21168802",
                "campaign_id": 1034,
                "state": "Retornó en AC",
                "comercial_id": 123,
                "fecha_asignacion": "2025-07-21T23:35:32.661Z",
                "summary": "Cliente interesado en retomar el proceso"
            }
        }

    class Config:
        extra = "forbid"
        from_attributes = True

    @classmethod
    def example(cls) -> Dict[str, Any]:
        return {
            "manychat_id": "21168802",
            "campaign_id": 1034,
            "state": "Asignado a Comercial",
            "summary": "Cliente interesado en producto X. Conversación positiva.",
            "comercial_id": 2023,
            "fecha_asignacion": "2025-07-21T10:00:00"
        }

class CampaignContactRead(BaseModel):
    id: int
    campaign_id: int
    contact_id: int
    commercial_advisor_id: Optional[int] = None
    medical_advisor_id: Optional[int] = None
    registration_date: datetime
    commercial_assignment_date: Optional[datetime] = None
    commercial_process_start_date: Optional[datetime] = None
    medical_assignment_date: Optional[datetime] = None
    medical_process_start_date: Optional[datetime] = None
    medical_process_end_date: Optional[datetime] = None
    quotation_start_date: Optional[datetime] = None
    sale_order_date: Optional[datetime] = None
    successful_sale_date: Optional[datetime] = None
    conversation_closed_date: Optional[datetime] = None
    last_state: Optional[str] = None
    lead_state: Optional[str] = None
    summary: Optional[str] = None
    sync_status: str

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }