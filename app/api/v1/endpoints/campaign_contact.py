
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Any
from app.db.session import get_db
from app.db.models import Contact, CampaignContact, ContactState
from app.schemas.campaign_contact import CampaignContactUpsert, CampaignContactRead
from app.core.logging import logger
from app.db.repositories import ContactRepository, CampaignContactRepository, ContactStateRepository
from app.services.queue_service import QueueService, QueueServiceError
import json

router = APIRouter()

# Endpoint unificado para asignación de campaña y cambio de estado (ManyChat → SQL y worker)
@router.post("/assign", response_model=CampaignContactRead, summary="Asignar campaña y estado (unificado)")
async def assign_campaign_and_state(
    data: CampaignContactUpsert,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    contact_repo = ContactRepository(db)
    campaign_contact_repo = CampaignContactRepository(db)
    contact_state_repo = ContactStateRepository(db)
    queue_service = QueueService()

    # Buscar contacto
    contact = contact_repo.get_by_manychat_id(data.manychat_id)
    if not contact:
        raise HTTPException(status_code=404, detail=f"No se encontró contacto con manychat_id={data.manychat_id}")

    # Upsert CampaignContact
    cc_data = {
        "contact_id": contact.id,
        "campaign_id": data.campaign_id,
        "last_state": data.ultimo_estado,
        "summary": data.summary,
        "sync_status": "new",
    }
    # Asignar advisor según tipo
    if data.tipo_asignacion == "comercial":
        cc_data["commercial_advisor_id"] = data.comercial_id
        cc_data["commercial_assignment_date"] = data.fecha_asignacion
    elif data.tipo_asignacion == "medico":
        cc_data["medical_advisor_id"] = data.medico_id
        cc_data["medical_assignment_date"] = data.fecha_asignacion

    campaign_contact = campaign_contact_repo.create_or_update_assignment(cc_data)

    # Upsert ContactState
    contact_state = contact_state_repo.create_or_update(
        contact_id=contact.id,
        state=data.state,
        category="crm"
    )

    # Encolar evento para worker CRM (Odoo)
    event = {
        "manychat_id": data.manychat_id,
        "campaign_id": data.campaign_id,
        "state": data.state,
        "summary": data.summary,
        "tipo_asignacion": data.tipo_asignacion,
        "comercial_id": data.comercial_id,
        "medico_id": data.medico_id,
        "fecha_asignacion": data.fecha_asignacion.isoformat(),
        "ultimo_estado": data.ultimo_estado,
        "contact_id": contact.id,
        "contact_state_id": contact_state.id,
    }
    try:
        await queue_service.send_message(queue_service.crm_queue_name, event)
    except Exception as e:
        logger.error(f"Error al encolar evento para worker CRM: {e}")

    return campaign_contact




@router.get("/", response_model=List[CampaignContactRead], summary="Listar todos los CampaignContacts")
def list_campaign_contacts(db: Session = Depends(get_db)):
    return db.query(CampaignContact).all()

@router.get("/{contact_id}/{campaign_id}", response_model=CampaignContactRead, summary="Obtener CampaignContact por contact_id y campaign_id")
def get_campaign_contact(contact_id: int, campaign_id: int, db: Session = Depends(get_db)):
    cc = db.query(CampaignContact).filter(
        CampaignContact.contact_id == contact_id,
        CampaignContact.campaign_id == campaign_id
    ).first()
    if not cc:
        raise HTTPException(status_code=404, detail="CampaignContact no encontrado")
    return cc

@router.put("/{contact_id}/{campaign_id}", response_model=CampaignContactRead, summary="Actualizar CampaignContact por contact_id y campaign_id")
def update_campaign_contact(contact_id: int, campaign_id: int, data: CampaignContactUpsert, db: Session = Depends(get_db)):
    cc = db.query(CampaignContact).filter(
        CampaignContact.contact_id == contact_id,
        CampaignContact.campaign_id == campaign_id
    ).first()
    if not cc:
        raise HTTPException(status_code=404, detail="CampaignContact no encontrado")
    update_fields = data.dict(exclude_unset=True, exclude={"manychat_id", "campaign_id"})
    for key, value in update_fields.items():
        if hasattr(cc, key):
            setattr(cc, key, value)
    cc.sync_status = "updated"
    db.add(cc)
    db.commit()
    db.refresh(cc)
    return cc

@router.delete("/{contact_id}/{campaign_id}", status_code=204, summary="Eliminar CampaignContact por contact_id y campaign_id")
def delete_campaign_contact(contact_id: int, campaign_id: int, db: Session = Depends(get_db)):
    cc = db.query(CampaignContact).filter(
        CampaignContact.contact_id == contact_id,
        CampaignContact.campaign_id == campaign_id
    ).first()
    if not cc:
        raise HTTPException(status_code=404, detail="CampaignContact no encontrado")
    db.delete(cc)
    db.commit()
    return None
