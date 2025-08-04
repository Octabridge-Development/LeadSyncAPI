# app/schemas/manychat.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ManyChatContactEvent(BaseModel):
    """
    Define el esquema para un evento de contacto de ManyChat.
    """
    manychat_id: str
    nombre_lead: str
    apellido_lead: Optional[str] = None
    whatsapp: Optional[str] = None
    email_lead: Optional[str] = None 
    datetime_suscripcion: Optional[datetime] = None
    datetime_actual: datetime
    canal_entrada: Optional[str] = None
    estado_inicial: Optional[str] = None

class ManyChatCampaignAssignmentEvent(BaseModel):
    """
    Define el esquema para eventos de asignación de campaña de ManyChat.
    """
    manychat_id: str
    campaign_id: int
    comercial_id: Optional[str] = None
    medico_id: Optional[str] = None
    datetime_actual: datetime
    ultimo_estado: str
    tipo_asignacion: str = "comercial"
    summary: Optional[str] = None

# --- 🚀 NUEVO ESQUEMA AÑADIDO 🚀 ---
class ManyChatAddressEvent(BaseModel):
    """
    Define el esquema para un evento de dirección desde ManyChat.
    Estos campos deben coincidir con los que envías desde el flujo de ManyChat.
    """
    manychat_id: str = Field(..., description="ID único del usuario en ManyChat.")
    street: Optional[str] = Field(None, description="Calle y número.")
    district: Optional[str] = Field(None, description="Comuna o distrito.")
    city: Optional[str] = Field(None, description="Ciudad.")
    state: Optional[str] = Field(None, description="Región o estado.")
    country: Optional[str] = Field(None, description="País.")