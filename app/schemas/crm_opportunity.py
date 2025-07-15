from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

# Mapeo de stages ManyChat → Odoo stage_id
MANYCHAT_TO_ODOO_STAGE_ID = {
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

class CRMOpportunityEvent(BaseModel):
    manychat_id: str
    stage_manychat: str
    stage_odoo_id: Optional[int] = None
    datetime_stage_change: datetime
    advisor_id: Optional[str] = None

    def get_odoo_stage_id(self) -> Optional[int]:
        """
        Devuelve el stage_id de Odoo correspondiente al stage de ManyChat.
        Si no existe, retorna None.
        """
        return MANYCHAT_TO_ODOO_STAGE_ID.get(self.stage_manychat)
