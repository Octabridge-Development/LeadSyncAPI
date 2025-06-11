from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# Propiedades comunes para crear o actualizar un Asesor
class AdvisorBase(BaseModel):
    name: str = Field(..., max_length=100, description="Nombre completo del asesor")
    email: EmailStr = Field(..., max_length=100, description="Email del asesor")
    phone: Optional[str] = Field(None, max_length=20, description="Teléfono del asesor")
    role: Optional[str] = Field(None, max_length=50, description="Rol del asesor (ej. Comercial, Médico)")
    status: Optional[str] = Field(None, max_length=20, description="Estado del asesor (ej. Activo, Inactivo)")
    genre: Optional[str] = Field(None, max_length=25, description="Género del asesor")
    odoo_id: Optional[str] = Field(None, max_length=50, description="ID del asesor en Odoo")

# Esquema para crear un Asesor
class AdvisorCreate(AdvisorBase):
    pass

# Esquema para actualizar un Asesor
class AdvisorUpdate(AdvisorBase):
    name: Optional[str] = None # El nombre es opcional al actualizar
    email: Optional[EmailStr] = None
    # Los demás campos ya son opcionales en AdvisorBase

# Esquema para la respuesta de un Asesor
class AdvisorInDB(AdvisorBase):
    id: int

    class Config:
        from_attributes = True