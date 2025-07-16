from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ContactStateBase(BaseModel):
    contact_id: int = Field(..., description="ID del contacto asociado")
    state: str = Field(..., description="Estado del contacto (ManyChat stage)")
    category: Optional[str] = Field(None, description="Categoría del estado (ej: manychat)")

class ContactStateCreate(ContactStateBase):
    pass

class ContactStateInDB(ContactStateBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
