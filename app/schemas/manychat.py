# app/schemas/manychat.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

# ... (otras clases BaseModel que ya tengas, si las hay)

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

# ... (otras clases BaseModel que ya tengas, si las las hay)