from pydantic import BaseModel, Field
from typing import Optional

class ChannelBase(BaseModel):
    name: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=255)

class ChannelCreate(ChannelBase):
    pass

class ChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=255)

class ChannelRead(ChannelBase):
    id: int
    class Config:
        from_attributes = True
