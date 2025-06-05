from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Date, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone # Asegúrate de importar datetime y timezone

from app.db.session import Base

# --- Modelo Address ---
class Address(Base):
    __tablename__ = "Address"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    street = Column(String(100), nullable=True)
    district = Column(String(50), nullable=True)
    city = Column(String(50), nullable=True)
    state = Column(String(50), nullable=True)
    country = Column(String(25), nullable=True)

    contacts = relationship("Contact", back_populates="address")

    def __repr__(self):
        return f"<Address(id={self.id}, street='{self.street}', city='{self.city}')>"

# --- Modelo Channel ---
class Channel(Base):
    __tablename__ = "Channel"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    name = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)

    contacts = relationship("Contact", back_populates="channel")

    def __repr__(self):
        return f"<Channel(id={self.id}, name='{self.name}')>"

# --- Modelo ContactState ---
class ContactState(Base):
    __tablename__ = "Contact_State"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    contact_id = Column(Integer, ForeignKey("Contact.id"), nullable=False)
    state = Column(String(100), nullable=False)
    category = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    contact = relationship("Contact", foreign_keys=[contact_id], back_populates="state_history")

    def __repr__(self):
        return f"<ContactState(id={self.id}, state='{self.state}', contact_id='{self.contact_id}')>"

# --- Modelo Contact ---
class Contact(Base):
    __tablename__ = "Contact"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    manychat_id = Column(String(255), nullable=False, unique=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    gender = Column(String(50), nullable=True)
    phone = Column(String(50), nullable=True)
    subscription_date = Column(DateTime, nullable=True)
    # Usar datetime.now(timezone.utc) es la práctica recomendada para UTC.
    entry_date = Column(DateTime, nullable=True, default=lambda: datetime.now(timezone.utc))
    initial_state = Column(String(255), nullable=True)
    odoo_contact_id = Column(String(255), nullable=True)

    channel_id = Column(Integer, ForeignKey("Channel.id"), nullable=True)
    channel = relationship("Channel", back_populates="contacts")

    address_id = Column(Integer, ForeignKey("Address.id"), nullable=True)
    address = relationship("Address", back_populates="contacts")

    state_history = relationship("ContactState", foreign_keys="ContactState.contact_id", back_populates="contact")

    campaign_assignments = relationship("CampaignContact", back_populates="contact")

    def __repr__(self):
        return f"<Contact(id={self.id}, email='{self.email}', manychat_id='{self.manychat_id}')>"

# --- Modelo SyncLog ---
class SyncLog(Base):
    __tablename__ = "Sync_Log"

    id = Column(Integer, primary_key=True, index=True)
    source_system = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<SyncLog(id={self.id}, status='{self.status}', created_at='{self.created_at}')>"

# --- Modelo Campaign (CORREGIDO PARA COINCIDIR CON TU DB) ---
class Campaign(Base):
    __tablename__ = "Campaign"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False) # Ajustado a 100 según INFORMATION_SCHEMA
    date_start = Column(DateTime, nullable=False) # Ajustado a DateTime según INFORMATION_SCHEMA
    date_end = Column(DateTime, nullable=True) # Ajustado a DateTime según INFORMATION_SCHEMA
    budget = Column(Numeric(18, 2), nullable=True) # Añadido según INFORMATION_SCHEMA, asumiendo precision/scale
    status = Column(String(20), nullable=True) # Ajustado a 20 según INFORMATION_SCHEMA
    channel_id = Column(Integer, ForeignKey("Channel.id"), nullable=True) # Añadido según INFORMATION_SCHEMA

    # Eliminadas: 'description', 'created_at', 'updated_at' ya que no están en tu DB Campaign

    # Relación con Channel (si quieres acceder al objeto Channel desde Campaign)
    channel = relationship("Channel")

    contact_assignments = relationship("CampaignContact", back_populates="campaign")

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}')>"

class Advisor(Base):
    __tablename__ = "Advisor"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    commercial_assignments = relationship(
        "CampaignContact",
        foreign_keys="[CampaignContact.commercial_advisor_id]",
        back_populates="commercial_advisor"
    )
    medical_assignments = relationship(
        "CampaignContact",
        foreign_keys="[CampaignContact.medical_advisor_id]",
        back_populates="medical_advisor"
    )

    def __repr__(self):
        return f"<Advisor(id={self.id}, name='{self.name}', email='{self.email}')>"

class CampaignContact(Base):
    __tablename__ = "Campaign_Contact"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("Contact.id"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("Campaign.id"), nullable=False)
    commercial_advisor_id = Column(Integer, ForeignKey("Advisor.id"), nullable=True)
    medical_advisor_id = Column(Integer, ForeignKey("Advisor.id"), nullable=True)
    registration_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_state = Column(String(100), nullable=True)
    lead_state = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    contact = relationship("Contact", back_populates="campaign_assignments")
    campaign = relationship("Campaign", back_populates="contact_assignments")
    commercial_advisor = relationship(
        "Advisor",
        foreign_keys=[commercial_advisor_id],
        back_populates="commercial_assignments"
    )
    medical_advisor = relationship(
        "Advisor",
        foreign_keys=[medical_advisor_id],
        back_populates="medical_assignments"
    )

    def __repr__(self):
        return f"<CampaignContact(id={self.id}, contact_id={self.contact_id}, campaign_id={self.campaign_id})>"