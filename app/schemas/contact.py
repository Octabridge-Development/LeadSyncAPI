from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from typing import Optional

# Propiedades comunes que pueden ser útiles para crear o actualizar un Contacto
class ContactBase(BaseModel):
    manychat_id: str = Field(..., description="ID único del contacto en ManyChat")
    first_name: str = Field(..., max_length=100, description="Nombre del contacto")
    last_name: Optional[str] = Field(None, max_length=100, description="Apellido del contacto")
    email: Optional[EmailStr] = Field(None, description="Email del contacto")
    gender: Optional[str] = Field(None, max_length=50, description="Género del contacto")
    phone: Optional[str] = Field(None, max_length=50, description="Teléfono del contacto")
    subscription_date: Optional[datetime] = Field(None, description="Fecha de suscripción del contacto")
    initial_state: Optional[str] = Field(None, max_length=255, description="Estado inicial del contacto")
    channel_id: Optional[int] = Field(None, description="ID del canal asociado")
    address_id: Optional[int] = Field(None, description="ID de la dirección asociada")

# Esquema para crear un Contacto (todos los campos requeridos para la creación inicial)
class ContactCreate(ContactBase):
    pass # Hereda todos los campos de ContactBase, y puedes agregar más si son específicos de la creación

# Esquema para actualizar un Contacto (todos los campos son opcionales para permitir actualizaciones parciales)
class ContactUpdate(ContactBase):
    manychat_id: Optional[str] = None # manychat_id podría no ser actualizable
    first_name: Optional[str] = None
    # Puedes hacer que otros campos sean no opcionales si siempre deben ser actualizados
    # Por ejemplo, si siempre debes enviar el nombre al actualizar: first_name: str

# Esquema para la respuesta de un Contacto (incluye el ID y las fechas generadas por la DB)
class ContactInDB(ContactBase):
    id: int
    entry_date: Optional[datetime] = None # La DB genera esto, lo incluimos en la respuesta
    
    # Configuramos Pydantic para que pueda manejar objetos ORM (como los de SQLAlchemy)
    class Config:
        from_attributes = True # Anteriormente orm_mode = True
