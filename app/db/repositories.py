from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.models import Contact, ContactState, Channel
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