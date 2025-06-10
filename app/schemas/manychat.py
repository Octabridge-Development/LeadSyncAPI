# app/schemas/manychat.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ManyChatContactEvent(BaseModel):
    """
    Define el esquema para un evento de contacto de ManyChat.
    Utilizado para procesar datos de contacto recibidos.
    """
    manychat_id: str
    nombre_lead: str
    apellido_lead: Optional[str] = None
    whatsapp: Optional[str] = None
    datetime_suscripcion: Optional[datetime] = None
    datetime_actual: datetime
    ultimo_estado: str
    canal_entrada: Optional[str] = None
    estado_inicial: Optional[str] = None

# 🔧 AGREGAR ESTA CLASE FALTANTE:
class ManyChatCampaignAssignmentEvent(BaseModel):
    """
    Define el esquema para eventos de asignación de campaña de ManyChat.
    campaign_id ahora es int para consistencia con la base de datos y el API.
    """
    manychat_id: str
    campaign_id: int  # Cambiado de str a int
    comercial_id: Optional[str] = None
    medico_id: Optional[str] = None
    datetime_actual: datetime
    ultimo_estado: str
    tipo_asignacion: str = "comercial"