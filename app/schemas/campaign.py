from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal

# Propiedades comunes para crear o actualizar una Campaña
class CampaignBase(BaseModel):
    name: str = Field(..., max_length=100, description="Nombre de la campaña")
    date_start: datetime = Field(..., description="Fecha de inicio de la campaña")
    date_end: Optional[datetime] = Field(None, description="Fecha de fin de la campaña")
    budget: Optional[Decimal] = Field(None, decimal_places=2, description="Presupuesto de la campaña")
    status: Optional[str] = Field(None, max_length=20, description="Estado actual de la campaña")
    channel_id: Optional[int] = Field(None, description="ID del canal asociado")

# Esquema para crear una Campaña
class CampaignCreate(CampaignBase):
    pass

# Esquema para actualizar una Campaña
class CampaignUpdate(CampaignBase):
    name: Optional[str] = None # El nombre es opcional al actualizar
    date_start: Optional[datetime] = None
    # Otros campos ya son opcionales en CampaignBase, por lo que se mantienen así

# Esquema para la respuesta de una Campaña
class CampaignInDB(CampaignBase):
    id: int

    class Config:
        from_attributes = True
