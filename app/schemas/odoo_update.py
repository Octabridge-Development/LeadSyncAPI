from pydantic import BaseModel
from typing import Optional

class OdooContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    active: Optional[bool] = None
    x_studio_manychatid_customer: Optional[str] = None
    # Agrega aquí solo los campos que realmente se pueden actualizar
