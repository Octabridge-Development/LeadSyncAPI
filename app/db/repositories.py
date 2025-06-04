from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.models import Contact, ContactState, Channel, Campaign, Advisor, CampaignContact # Importa los nuevos modelos [cite: 10]
from typing import Optional, Dict, Any
import logging

class ContactRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_manychat_id(self, manychat_id: str) -> Optional[Contact]:
        """Get contact by ManyChat ID"""
        return self.db.query(Contact).filter(
            Contact.manychat_id == manychat_id
        ).first()

    def create_or_update(self, contact_data: Dict[str, Any]) -> Contact:
        """Create new contact or update existing one (UPSERT)"""
        existing = self.get_by_manychat_id(contact_data["manychat_id"])

        if existing:
            # Update existing contact
            for key, value in contact_data.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            contact = existing
        else:
            # Create new contact
            contact = Contact(**contact_data)
            self.db.add(contact)

        self.db.commit()
        self.db.refresh(contact)
        return contact

class ContactStateRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, contact_id: int, state: str, category: str = "manychat") -> ContactState:
        """Create new contact state record"""
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
        """Get latest state for a contact"""
        return self.db.query(ContactState).filter(
            ContactState.contact_id == contact_id
        ).order_by(ContactState.created_at.desc()).first()

class ChannelRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_by_name(self, name: str) -> Channel:
        """Get channel by name or create if doesn't exist"""
        channel = self.db.query(Channel).filter(Channel.name == name).first()
        if not channel:
            channel = Channel(name=name, description=f"Auto-created: {name}")
            self.db.add(channel)
            self.db.commit()
            self.db.refresh(channel)
        return channel

# --- Nuevos Repositorios (Tarea A2) ---
class CampaignRepository: # Agregado [cite: 5]
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_by_name(self, name: str) -> Campaign: # Agregado [cite: 5]
        """Get campaign by name or create if it doesn't exist."""
        campaign = self.db.query(Campaign).filter(Campaign.name == name).first()
        if not campaign:
            # Aquí podrías añadir más campos por defecto o requeridos para Campaign
            campaign = Campaign(name=name, date_start=datetime.utcnow().date(), status="active") # Ejemplo
            self.db.add(campaign)
            self.db.commit()
            self.db.refresh(campaign)
        return campaign

class AdvisorRepository: # Agregado [cite: 5]
    def __init__(self, db: Session):
        self.db = db

    def get_by_id_or_email(self, identifier: str) -> Optional[Advisor]: # Agregado [cite: 5]
        """Get advisor by ID or email."""
        try:
            # Intenta convertir a int para buscar por ID
            advisor_id = int(identifier)
            return self.db.query(Advisor).filter(Advisor.id == advisor_id).first()
        except ValueError:
            # Si no es un int, busca por email o nombre
            return self.db.query(Advisor).filter(
                or_(Advisor.email == identifier, Advisor.name == identifier)
            ).first()

class CampaignContactRepository: # Agregado [cite: 5]
    def __init__(self, db: Session):
        self.db = db

    def create_or_update_assignment(self, data: Dict[str, Any]) -> CampaignContact: # Agregado [cite: 5]
        """Create new CampaignContact or update existing one (UPSERT)."""
        # Busca por contact_id y campaign_id para evitar duplicados de asignación
        existing = self.db.query(CampaignContact).filter(
            CampaignContact.contact_id == data["contact_id"],
            CampaignContact.campaign_id == data["campaign_id"]
        ).first()

        if existing:
            for key, value in data.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            campaign_contact = existing
        else:
            campaign_contact = CampaignContact(**data)
            self.db.add(campaign_contact)

        self.db.commit()
        self.db.refresh(campaign_contact)
        return campaign_contact