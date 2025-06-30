from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.db.models import Channel
from app.schemas.channel import ChannelCreate, ChannelUpdate, ChannelRead
from app.core.config import get_settings

router = APIRouter()

@router.post("/", response_model=ChannelRead, status_code=status.HTTP_201_CREATED)
def create_channel(channel: ChannelCreate, db: Session = Depends(get_db)):
    db_channel = Channel(**channel.model_dump())
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    return db_channel

@router.get("/", response_model=List[ChannelRead])
def list_channels(db: Session = Depends(get_db)):
    return db.query(Channel).all()

@router.get("/{channel_id}", response_model=ChannelRead)
def get_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel

@router.put("/{channel_id}", response_model=ChannelRead)
def update_channel(channel_id: int, channel_update: ChannelUpdate, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    for key, value in channel_update.model_dump(exclude_unset=True).items():
        setattr(channel, key, value)
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel

@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(channel_id: int, api_key: str = Query(..., description="Debes ingresar el API_KEY para confirmar la eliminación"), db: Session = Depends(get_db)):
    settings = get_settings()
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API_KEY inválido. No autorizado para eliminar.")
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    db.delete(channel)
    db.commit()
    return None
