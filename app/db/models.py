# app/db/models.py (VERSIÓN FINAL CORREGIDA PARA RELACIONES AMBIGUAS)

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

# --- Modelo Address ---
class Address(Base):
    __tablename__ = "Address" # Nombre de tabla confirmado: "Address"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    street = Column(String(100), nullable=True)
    district = Column(String(50), nullable=True)
    city = Column(String(50), nullable=True)
    state = Column(String(50), nullable=True)
    country = Column(String(25), nullable=True)

    # Relación uno a muchos con Contact (un Address puede tener varios Contacts)
    contacts = relationship("Contact", back_populates="address")

    def __repr__(self):
        return f"<Address(id={self.id}, street='{self.street}', city='{self.city}')>"

# --- Modelo Channel ---
class Channel(Base):
    __tablename__ = "Channel" # Nombre de tabla confirmado: "Channel"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    name = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)

    # Relación uno a muchos con Contact (un Channel puede tener varios Contacts)
    contacts = relationship("Contact", back_populates="channel")

    def __repr__(self):
        return f"<Channel(id={self.id}, name='{self.name}')>"

# --- Modelo ContactState ---
class ContactState(Base):
    __tablename__ = "Contact_State" # Nombre de tabla confirmado: "Contact_State"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    contact_id = Column(Integer, ForeignKey("Contact.id"), nullable=False) # Clave foránea a Contact.id
    state = Column(String(100), nullable=False)
    category = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relación muchos a uno con Contact (un ContactState pertenece a un Contact)
    # Aquí especificamos explícitamente la FK de esta relación.
    contact = relationship("Contact", foreign_keys=[contact_id], back_populates="state_history")

    def __repr__(self):
        return f"<ContactState(id={self.id}, state='{self.state}', contact_id='{self.contact_id}')>"

# --- Modelo Contact ---
class Contact(Base):
    __tablename__ = "Contact" # Nombre de tabla confirmado: "Contact"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    manychat_id = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    gender = Column(String(50), nullable=True)
    phone = Column(String(50), nullable=True)
    subscription_date = Column(DateTime, nullable=True)
    entry_date = Column(DateTime, nullable=True)
    initial_state = Column(String(255), nullable=True) # Tu campo VARCHAR en DB
    odoo_contact_id = Column(String(255), nullable=True)

    # Claves Foráneas y relaciones
    channel_id = Column(Integer, ForeignKey("Channel.id"), nullable=True)
    channel = relationship("Channel", back_populates="contacts")

    address_id = Column(Integer, ForeignKey("Address.id"), nullable=True)
    address = relationship("Address", back_populates="contacts")

    # Relación al estado ACTUAL del Contact (un Contact tiene UN estado actual)
    state_id = Column(Integer, ForeignKey("Contact_State.id"), nullable=True)
    # Aquí especificamos explícitamente la FK para esta relación.
    current_state = relationship("ContactState", foreign_keys=[state_id])

    # Relación al historial de estados (un Contact puede tener muchos ContactState)
    # Aquí especificamos explícitamente la FK de esta relación.
    state_history = relationship("ContactState", foreign_keys="ContactState.contact_id", back_populates="contact")


    def __repr__(self):
        return f"<Contact(id={self.id}, email='{self.email}', manychat_id='{self.manychat_id}')>"

# --- Modelo SyncLog ---
class SyncLog(Base):
    __tablename__ = "Sync_Log" # Nombre de tabla confirmado: "Sync_Log"

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

# --- Modelo Campaign ---
class Campaign(Base):
    __tablename__ = "Campaign"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    date_start = Column(DateTime, nullable=False)
    date_end = Column(DateTime, nullable=False)
    budget = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False)
    channel_id = Column(Integer, ForeignKey("Channel.id"), nullable=False)

    channel = relationship("Channel", backref="campaigns")
    contacts = relationship("CampaignContact", back_populates="campaign")

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}')>"

# --- Modelo Advisor ---
class Advisor(Base):
    __tablename__ = "Advisor"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    role = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    genre = Column(String(20), nullable=True)
    odoo_id = Column(String(100), nullable=True)

    campaign_contacts_commercial = relationship("CampaignContact", back_populates="commercial_advisor", foreign_keys='CampaignContact.commercial_advisor_id')
    campaign_contacts_medical = relationship("CampaignContact", back_populates="medical_advisor", foreign_keys='CampaignContact.medical_advisor_id')

    def __repr__(self):
        return f"<Advisor(id={self.id}, name='{self.name}')>"

# --- Modelo CampaignContact ---
class CampaignContact(Base):
    __tablename__ = "Campaign_Contact"
    __table_args__ = (
        UniqueConstraint('campaign_id', 'contact_id', name='uq_campaign_contact'),
    )
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    campaign_id = Column(Integer, ForeignKey("Campaign.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("Contact.id"), nullable=False)
    commercial_advisor_id = Column(Integer, ForeignKey("Advisor.id"), nullable=True)
    medical_advisor_id = Column(Integer, ForeignKey("Advisor.id"), nullable=True)
    registration_date = Column(DateTime, nullable=False, server_default=func.now())
    last_state = Column(String(50), nullable=True)
    lead_state = Column(String(50), nullable=True)

    campaign = relationship("Campaign", back_populates="contacts")
    contact = relationship("Contact")
    commercial_advisor = relationship("Advisor", foreign_keys=[commercial_advisor_id], back_populates="campaign_contacts_commercial")
    medical_advisor = relationship("Advisor", foreign_keys=[medical_advisor_id], back_populates="campaign_contacts_medical")

    def __repr__(self):
        return f"<CampaignContact(id={self.id}, campaign_id={self.campaign_id}, contact_id={self.contact_id})>"