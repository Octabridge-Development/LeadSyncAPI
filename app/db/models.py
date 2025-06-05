<<<<<<< HEAD
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Date, DECIMAL
=======
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Date, Numeric
>>>>>>> aed482550ac07ce92ea389bdfd1ae01c0b4b9838
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

<<<<<<< HEAD
    # Relación al historial de estados (un Contact puede tener muchos ContactState)
    # Aquí especificamos explícitamente la FK de esta relación.
=======
    address_id = Column(Integer, ForeignKey("Address.id"), nullable=True)
    address = relationship("Address", back_populates="contacts")

>>>>>>> aed482550ac07ce92ea389bdfd1ae01c0b4b9838
    state_history = relationship("ContactState", foreign_keys="ContactState.contact_id", back_populates="contact")

    campaign_assignments = relationship("CampaignContact", back_populates="contact")

    # Nueva columna y relación con Address
    address_id = Column(Integer, ForeignKey("Address.id"), nullable=True)
    address = relationship("Address", back_populates="contacts")

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
<<<<<<< HEAD
    name = Column(String(100), nullable=False)
    date_start = Column(DateTime, nullable=False)
    date_end = Column(DateTime, nullable=True)
    budget = Column(DECIMAL(10, 2), nullable=True)
    status = Column(String(20), nullable=True)
    channel_id = Column(Integer, ForeignKey("Channel.id"), nullable=True)
=======
    name = Column(String(100), unique=True, nullable=False) # Ajustado a 100 según INFORMATION_SCHEMA
    date_start = Column(DateTime, nullable=False) # Ajustado a DateTime según INFORMATION_SCHEMA
    date_end = Column(DateTime, nullable=True) # Ajustado a DateTime según INFORMATION_SCHEMA
    budget = Column(Numeric(18, 2), nullable=True) # Añadido según INFORMATION_SCHEMA, asumiendo precision/scale
    status = Column(String(20), nullable=True) # Ajustado a 20 según INFORMATION_SCHEMA
    channel_id = Column(Integer, ForeignKey("Channel.id"), nullable=True) # Añadido según INFORMATION_SCHEMA

    # Eliminadas: 'description', 'created_at', 'updated_at' ya que no están en tu DB Campaign

    # Relación con Channel (si quieres acceder al objeto Channel desde Campaign)
    channel = relationship("Channel")
>>>>>>> aed482550ac07ce92ea389bdfd1ae01c0b4b9838

    # Relationships
    contact_assignments = relationship("CampaignContact", back_populates="campaign")

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}')>"

<<<<<<< HEAD
=======
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
>>>>>>> aed482550ac07ce92ea389bdfd1ae01c0b4b9838

class CampaignContact(Base):
    __tablename__ = "Campaign_Contact"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("Campaign.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("Contact.id"), nullable=False)
    commercial_advisor_id = Column(Integer, ForeignKey("Advisor.id"), nullable=True)
    medical_advisor_id = Column(Integer, ForeignKey("Advisor.id"), nullable=True)
<<<<<<< HEAD
    registration_date = Column(DateTime, server_default=func.now(), nullable=False)
    commercial_assignment_date = Column(DateTime, nullable=True)
    commercial_process_start_date = Column(DateTime, nullable=True)
    medical_assignment_date = Column(DateTime, nullable=True)
    medical_process_start_date = Column(DateTime, nullable=True)
    medical_process_end_date = Column(DateTime, nullable=True)
    quotation_start_date = Column(DateTime, nullable=True)
    sale_order_date = Column(DateTime, nullable=True)
    successful_sale_date = Column(DateTime, nullable=True)
    conversation_closed_date = Column(DateTime, nullable=True)
    last_state = Column(String(100), nullable=True)
    lead_state = Column(String(50), nullable=True)

    # Relationships
    campaign = relationship("Campaign", back_populates="contact_assignments")
    contact = relationship("Contact", back_populates="campaign_assignments")
    commercial_advisor = relationship("Advisor", foreign_keys=[commercial_advisor_id], back_populates="commercial_assignments")
    medical_advisor = relationship("Advisor", foreign_keys=[medical_advisor_id], back_populates="medical_assignments")

    def __repr__(self):
        return f"<CampaignContact(id={self.id}, contact_id={self.contact_id}, campaign_id={self.campaign_id})>"


class Advisor(Base):
    __tablename__ = "Advisor"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(String(50), nullable=True)
    status = Column(String(20), nullable=True)
    genre = Column(String(25), nullable=True)
    odoo_id = Column(String(50), nullable=True)

    # Relaciones explícitas para evitar ambigüedad con CampaignContact
    commercial_assignments = relationship(
        "CampaignContact",
        foreign_keys=[CampaignContact.commercial_advisor_id],
        back_populates="commercial_advisor"
=======
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
>>>>>>> aed482550ac07ce92ea389bdfd1ae01c0b4b9838
    )
    medical_assignments = relationship(
        "CampaignContact",
        foreign_keys=[CampaignContact.medical_advisor_id],
        back_populates="medical_advisor"
    )

    def __repr__(self):
        return f"<Advisor(id={self.id}, name='{self.name}', email='{self.email}')>"

# --- Modelo Lead ---
class Lead(Base):
    __tablename__ = "Lead"

    id = Column(Integer, primary_key=True, index=True)
    campaign_contact_id = Column(Integer, ForeignKey("Campaign_Contact.id"), nullable=False)
    cold_date = Column(DateTime, nullable=True)
    warm_date = Column(DateTime, nullable=True)
    hot_date = Column(DateTime, nullable=True)
    hot_plus_date = Column(DateTime, nullable=True)
    current_temperature = Column(String(20), nullable=True)
    last_update = Column(DateTime, nullable=True)

    # Relación con CampaignContact
    campaign_contact = relationship("CampaignContact", backref="leads")

    def __repr__(self):
        return f"<Lead(id={self.id}, campaign_contact_id={self.campaign_contact_id})>"

class Client(Base):
    __tablename__ = "Client"

    id = Column(Integer, primary_key=True, index=True)
    campaign_contact_id = Column(Integer, ForeignKey("Campaign_Contact.id"), nullable=False)
    new_client_date = Column(DateTime, nullable=True)
    active_client_date = Column(DateTime, nullable=True)
    at_risk_client_date = Column(DateTime, nullable=True)
    inactive_client_date = Column(DateTime, nullable=True)
    lost_client_date = Column(DateTime, nullable=True)
    reactive_client_date = Column(DateTime, nullable=True)
    current_status = Column(String(20), nullable=True)
    odoo_client_id = Column(String(50), nullable=True)

    # Relación con CampaignContact
    campaign_contact = relationship("CampaignContact", backref="clients")
    # Relación con ClientDetail
    details = relationship("ClientDetail", back_populates="client")

    def __repr__(self):
        return f"<Client(id={self.id}, campaign_contact_id={self.campaign_contact_id})>"

class ClientDetail(Base):
    __tablename__ = "Client_Detail"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("Client.id"), nullable=False)
    summary = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Relación con Client
    client = relationship("Client", back_populates="details")

    def __repr__(self):
        return f"<ClientDetail(id={self.id}, client_id={self.client_id})>"

class LeadDetail(Base):
    __tablename__ = "Lead_Detail"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("Lead.id"), nullable=False)
    summary = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Relación con Lead
    lead = relationship("Lead", backref="details")

    def __repr__(self):
        return f"<LeadDetail(id={self.id}, lead_id={self.lead_id})>"

class Product(Base):
    __tablename__ = "Product"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(DECIMAL(10, 2), nullable=True)
    is_active = Column(Boolean, default=True, nullable=True)
    created_at = Column(DateTime, nullable=True)

    # Relación con OrderProduct
    order_products = relationship("OrderProduct", back_populates="product")

    def __repr__(self):
        return f"<Product(id={self.id}, code='{self.code}', name='{self.name}')>"

class OrderProduct(Base):
    __tablename__ = "Order_Product"

    id = Column(Integer, primary_key=True, index=True)
    campaign_contact_id = Column(Integer, ForeignKey("Campaign_Contact.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("Product.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    discount = Column(DECIMAL(10, 2), nullable=True, default=0)
    status = Column(String(50), nullable=True)
    order_date = Column(DateTime, nullable=False)

    # Relaciones
    campaign_contact = relationship("CampaignContact", backref="order_products")
    product = relationship("Product", back_populates="order_products")

    def __repr__(self):
        return f"<OrderProduct(id={self.id}, campaign_contact_id={self.campaign_contact_id}, product_id={self.product_id})>"

class ProductInteraction(Base):
    __tablename__ = "Product_Interaction"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("Product.id"), nullable=False)
    interaction_type = Column(String(50), nullable=False)
    interaction_date = Column(DateTime, nullable=False)
    source = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    campaign_contact_id = Column(Integer, ForeignKey("Campaign_Contact.id"), nullable=True)
    contact_id = Column(Integer, ForeignKey("Contact.id"), nullable=False)

    # Relaciones
    product = relationship("Product", backref="product_interactions")
    campaign_contact = relationship("CampaignContact", backref="product_interactions")
    contact = relationship("Contact", backref="product_interactions")

    def __repr__(self):
        return f"<ProductInteraction(id={self.id}, product_id={self.product_id}, contact_id={self.contact_id})>"