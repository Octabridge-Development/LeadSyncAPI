from sqlalchemy.orm import Session
from sqlalchemy import or_
# Asegúrate de importar datetime y timezone aquí
from datetime import datetime, timezone # <--- AÑADE O ASEGÚRATE DE ESTA LÍNEA
import logging

from app.db.models import Contact, ContactState, Channel, Campaign, Advisor, CampaignContact # Importa todos los modelos necesarios
from typing import Optional, Dict, Any

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

# --- Repositorios para Campañas ---
class CampaignRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_campaign_by_name(self, name: str) -> Optional[Campaign]:
        """Helper to get campaign by name"""
        return self.db.query(Campaign).filter(Campaign.name == name).first()

    def create_campaign(self, name: str) -> Campaign:
        """Create a new campaign with default values."""
        new_campaign = Campaign(
            name=name,
            # Usar datetime.now(timezone.utc) para un objeto datetime consciente del huso horario
            date_start=datetime.now(timezone.utc),
            status="active", # Puedes ajustar el valor por defecto si es necesario
            budget=0.0, # <--- AÑADIDO: Inicializar budget ya que existe en la DB
            # channel_id = None # Puedes añadirlo si siempre debe tener un valor inicial o se toma de algún lugar
        )
        self.db.add(new_campaign)
        self.db.commit()
        self.db.refresh(new_campaign)
        return new_campaign

    def get_or_create_by_name(self, name: str) -> Campaign:
        """Get campaign by name or create if it doesn't exist."""
        campaign = self.get_campaign_by_name(name)
        if not campaign:
            logging.info(f"Campaña '{name}' no encontrada. Creando nueva campaña.")
            campaign = self.create_campaign(name) # Llama a la nueva función create_campaign
        return campaign

class AdvisorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id_or_email(self, identifier: str) -> Optional[Advisor]:
        """Get advisor by ID or email."""
        try:
            advisor_id = int(identifier)
            return self.db.query(Advisor).filter(Advisor.id == advisor_id).first()
        except ValueError:
            return self.db.query(Advisor).filter(
                or_(Advisor.email == identifier, Advisor.name == identifier)
            ).first()

class CampaignContactRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_or_update_assignment(self, data: Dict[str, Any]) -> CampaignContact:
        """Create new CampaignContact or update existing one (UPSERT)."""
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