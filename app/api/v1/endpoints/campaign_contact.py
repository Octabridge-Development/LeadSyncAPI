from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from app.db.session import get_db
from app.db.models import Contact, CampaignContact
from app.schemas.campaign_contact import CampaignContactUpdate, CampaignContactRead
from app.core.logging import logger

router = APIRouter()

@router.get("/by-manychat/{manychat_id}", response_model=List[CampaignContactRead], summary="Obtener CampaignContact(s) por ManyChat ID")
def get_campaign_contacts_by_manychat_id(manychat_id: str, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.manychat_id == manychat_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail=f"No se encontró contacto con manychat_id={manychat_id}")
    campaign_contacts = db.query(CampaignContact).filter(CampaignContact.contact_id == contact.id).all()
    if not campaign_contacts:
        raise HTTPException(status_code=404, detail=f"No se encontraron registros CampaignContact para el contacto {manychat_id}")
    return campaign_contacts

@router.put("/by-manychat/{manychat_id}", response_model=List[CampaignContactRead], summary="Actualizar CampaignContact(s) por ManyChat ID")
def update_campaign_contacts_by_manychat_id(
    manychat_id: str,
    update_data: dict,
    db: Session = Depends(get_db)
):
    contact = db.query(Contact).filter(Contact.manychat_id == manychat_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail=f"No se encontró contacto con manychat_id={manychat_id}")
    campaign_contacts = db.query(CampaignContact).filter(CampaignContact.contact_id == contact.id).all()
    if not campaign_contacts:
        raise HTTPException(status_code=404, detail=f"No se encontraron registros CampaignContact para el contacto {manychat_id}")
    updated = []
    for cc in campaign_contacts:
        for key, value in update_data.items():
            if hasattr(cc, key):
                setattr(cc, key, value)
        db.add(cc)
        updated.append(cc)
    try:
        logger.info(f"Intentando commit de {len(updated)} CampaignContact(s) para manychat_id={manychat_id}")
        db.commit()
        logger.info(f"Commit exitoso de CampaignContact(s) para manychat_id={manychat_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error al hacer commit de CampaignContact(s) para manychat_id={manychat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al guardar los cambios en la base de datos")
    return updated
