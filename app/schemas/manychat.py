from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ManyChatWebhookEvent(BaseModel):
    manychat_id: str
    nombre_lead: str
    apellido_lead: Optional[str] = None
    whatsapp: Optional[str] = None
    comercial: Optional[str] = None
    datetime_suscripcion: Optional[datetime] = None
    datetime_actual: datetime
    ultimo_estado: str
    canal_entrada: Optional[str] = None
    estado_inicial: Optional[str] = None