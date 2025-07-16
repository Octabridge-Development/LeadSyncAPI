# app/schemas/crm_opportunity.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, ClassVar
from datetime import datetime


class CRMOpportunityEvent(BaseModel):
    class Config:
        extra = "allow"
    manychat_id: str = Field(..., description="ID del contacto de ManyChat") # [cite: 50]
    stage_manychat: str = Field(..., description="Stage de ManyChat") # [cite: 52]
    advisor_id: Optional[str] = Field(None, description="ID del asesor (opcional)") # [cite: 55]

    MANYCHAT_TO_ODOO_STAGE: ClassVar[Dict[str, int]] = {
        "Recién Suscrito (Sin Asignar)": 16,
        "Recién suscrito Pendiente de AC": 17,
        "Retornó en AC": 18,
        "Comienza Atención Comercial": 19,
        "Retornó a Asesoría especializada": 20,
        "Derivado Asesoría Médica": 21,
        "Comienza Asesoría Médica": 22,
        "Terminó Asesoría Médica": 23,
        "No terminó Asesoría especializada Derivado a Comercial": 24,
        "Comienza Cotización": 25,
        "Orden de venta Confirmada": 26
    }

    @property
    def stage_odoo_id(self) -> Optional[int]:
        return self.MANYCHAT_TO_ODOO_STAGE.get(self.stage_manychat)