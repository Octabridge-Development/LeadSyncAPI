from sqlalchemy.orm import Session
from sqlalchemy import or_
# Asegúrate de importar todos los modelos que usas en los repositorios
from app.db.models import Contact, ContactState, Channel, Campaign, Advisor, CampaignContact 
from typing import Optional, Dict, Any
import logging
from datetime import datetime, date # date no se usa en este archivo, puedes removerlo si no lo necesitas en otros repos.

class ContactRepository:
    def __init__(self, db: Session):
        self.db = db
        
    def get_by_manychat_id(self, manychat_id: str) -> Optional[Contact]:
        """Obtiene un contacto por su ID de ManyChat."""
        return self.db.query(Contact).filter(
            Contact.manychat_id == manychat_id
        ).first()
        
    def create_or_update(self, contact_data: Dict[str, Any]) -> Contact:
        """
        Crea un nuevo contacto o actualiza uno existente (UPSERT)
        basado en el manychat_id.
        """
        existing_contact = self.get_by_manychat_id(contact_data["manychat_id"])
        
        if existing_contact:
            # Actualiza el contacto existente
            for key, value in contact_data.items():
                if hasattr(existing_contact, key) and value is not None:
                    setattr(existing_contact, key, value)
            contact = existing_contact
        else:
            # Crea un nuevo contacto
            contact = Contact(**contact_data)
            self.db.add(contact)
            
        self.db.commit()
        self.db.refresh(contact)
        return contact


class ContactStateRepository:
    def __init__(self, db: Session):
        self.db = db
        

    def create_or_update(self, contact_id: int, state: str, category: str = "manychat") -> ContactState:
        """
        Crea o actualiza el estado del contacto: si existe un registro previo, lo actualiza; si no, lo crea.
        Siempre habrá solo un registro por contacto.
        """
        latest = self.get_latest_by_contact(contact_id)
        if latest:
            latest.state = state
            latest.category = category
            self.db.commit()
            self.db.refresh(latest)
            return latest
        else:
            contact_state = ContactState(
                contact_id=contact_id,
                state=state,
                category=category
            )
            self.db.add(contact_state)
            self.db.commit()
            self.db.refresh(contact_state)
            return contact_state
        
    def get_latest_by_contact(self, contact_id: int) -> Optional[ContactState]:
        """Obtiene el último estado registrado para un contacto."""
        return self.db.query(ContactState).filter(
            ContactState.contact_id == contact_id
        ).order_by(ContactState.created_at.desc()).first()

class ChannelRepository:
    def __init__(self, db: Session):
        self.db = db
        
    def get_or_create_by_name(self, name: str) -> Channel:
        """Obtiene un canal por nombre o lo crea si no existe."""
        channel = self.db.query(Channel).filter(Channel.name == name).first()
        if not channel:
            channel = Channel(name=name, description=f"Auto-created: {name}")
            self.db.add(channel)
            self.db.commit()
            self.db.refresh(channel)
        return channel

# --- Nuevos Repositorios (Tarea A2) ---
class CampaignRepository: 
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_by_name(self, name: str) -> Campaign: 
        """Obtiene una campaña por nombre o la crea si no existe."""
        campaign = self.db.query(Campaign).filter(Campaign.name == name).first()
        if not campaign:
            now = datetime.utcnow()
            campaign = Campaign(
                name=name,
                date_start=now,
                date_end=None,
                status="active"
            )
            self.db.add(campaign)
            self.db.commit()
            self.db.refresh(campaign)
        return campaign

    def get_by_id(self, campaign_id: int) -> Optional[Campaign]:
        """Obtiene una campaña por su ID entero."""
        return self.db.query(Campaign).filter(Campaign.id == campaign_id).first()

class AdvisorRepository: 
    def __init__(self, db: Session):
        self.db = db

    def get_by_id_or_email(self, identifier: str) -> Optional[Advisor]: 
        """Obtiene un asesor por su ID o email."""
        try:
            advisor_id = int(identifier)
            return self.db.query(Advisor).filter(Advisor.id == advisor_id).first()
        except ValueError: # Si no es un entero, intenta buscar por email o nombre
            return self.db.query(Advisor).filter(
                or_(Advisor.email == identifier, Advisor.name == identifier)
            ).first()

class CampaignContactRepository: 
    def __init__(self, db: Session):
        self.db = db

    def create_or_update_assignment(self, data: Dict[str, Any]) -> CampaignContact: 
        """Crea una nueva asignación de CampaignContact o actualiza una existente (UPSERT)."""
        from datetime import datetime, timezone
        # Busca por contact_id y campaign_id para evitar duplicados de asignación
        existing = self.db.query(CampaignContact).filter(
            CampaignContact.contact_id == data["contact_id"],
            CampaignContact.campaign_id == data["campaign_id"]
        ).first()

        if existing:
            for key, value in data.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            # Marcar como nuevo para que el worker CRM lo procese
            existing.sync_status = "new"
            campaign_contact = existing
        else:
            # Si no viene registration_date, usar ahora en UTC
            if "registration_date" not in data or data["registration_date"] is None:
                data["registration_date"] = datetime.now(timezone.utc)
            data["sync_status"] = "new"
            campaign_contact = CampaignContact(**data)
            self.db.add(campaign_contact)

        self.db.commit()
        self.db.refresh(campaign_contact)
        return campaign_contact