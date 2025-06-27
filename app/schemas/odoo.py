from pydantic import BaseModel
from typing import Optional

class OdooContactCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    # Puedes agregar más campos según el modelo de Odoo
