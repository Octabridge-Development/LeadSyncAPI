# app/schemas/crm.py

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional

class CRMLeadState(BaseModel):
    """Esquema para el estado del lead dentro del payload de ManyChat."""
    stage_id: int = Field(..., ge=16, le=26)  # IDs válidos de Odoo
    summary: Optional[str] = None
    date: datetime

class CRMLeadEvent(BaseModel):
    """
    Esquema para el evento completo de CRM recibido desde ManyChat. [cite: 77]
    Valida el payload de entrada. [cite: 130]
    """
    manychat_id: str # [cite: 132]
    first_name: str # [cite: 133]
    last_name: Optional[str] = None # [cite: 134]
    phone: Optional[str] = None # [cite: 135]
    channel: Optional[str] = "WhatsApp" # [cite: 136]
    entry_date: datetime # [cite: 137]
    medical_advisor_id: Optional[int] = None # [cite: 138]
    commercial_advisor_id: Optional[int] = None # [cite: 139]
    state: CRMLeadState # 

class CRMLeadResponse(BaseModel):
    """Esquema para la respuesta del endpoint de CRM. [cite: 78]"""
    status: str
    message: str
    manychat_id: str