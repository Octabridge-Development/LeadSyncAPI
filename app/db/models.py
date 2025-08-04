# app/db/models.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base # Asegúrate que la importación de Base sea correcta

# --- Modelo Address (CORREGIDO) ---
class Address(Base):
    __tablename__ = "Address"
    
    id = Column(Integer, primary_key=True, index=True)
    street = Column(String(100), nullable=True)
    district = Column(String(50), nullable=True)
    city = Column(String(50), nullable=True)
    state = Column(String(50), nullable=True)
    country = Column(String(25), nullable=True)
    
    # --- ✅ CORRECCIÓN ---
    # Añadimos la clave foránea para apuntar al Contacto al que pertenece esta dirección.
    contact_id = Column(Integer, ForeignKey("Contact.id"))
    
    # Esta relación permite que desde una dirección (address) se pueda acceder 
    # a la información del contacto (contact) al que pertenece.
    contact = relationship("Contact", back_populates="addresses")

# --- Modelo Channel ---
class Channel(Base):
    __tablename__ = "Channel"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)
    contacts = relationship("Contact", back_populates="channel")

# --- Modelo ContactState ---
class ContactState(Base):
    __tablename__ = "Contact_State"
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("Contact.id"), nullable=False)
    state = Column(String(100), nullable=False)
    category = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    contact = relationship("Contact", back_populates="state_history")

# --- Modelo Contact (CORREGIDO) ---
class Contact(Base):
    __tablename__ = "Contact"

    id = Column(Integer, primary_key=True, index=True)
    manychat_id = Column(String(50), nullable=False, unique=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True, index=True)
    gender = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True)
    subscription_date = Column(DateTime, nullable=True)
    entry_date = Column(DateTime, nullable=True)
    initial_state = Column(String(50), nullable=True)
    odoo_contact_id = Column(String(50), nullable=True)

    # --- Relaciones ---
    channel_id = Column(Integer, ForeignKey("Channel.id"), nullable=True)
    channel = relationship("Channel", back_populates="contacts")

    # --- ✅ CORRECCIÓN ---
    # Se elimina la 'address_id' y 'address' de aquí.
    # En su lugar, esta relación crea una lista de direcciones (addresses) para cada contacto.
    # Si un contacto se elimina, todas sus direcciones se borrarán en cascada.
    addresses = relationship("Address", back_populates="contact", cascade="all, delete-orphan")

    state_history = relationship("ContactState", back_populates="contact")
    campaign_assignments = relationship("CampaignContact", back_populates="contact")
    product_interactions = relationship("ProductInteraction", back_populates="contact")

# --- (El resto de tus modelos permanecen igual) ---

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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- Modelo Campaign ---
class Campaign(Base):
    __tablename__ = "Campaign"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    date_start = Column(DateTime, nullable=False)
    date_end = Column(DateTime, nullable=True)
    budget = Column(DECIMAL(10, 2), nullable=True)
    status = Column(String(20), nullable=True)
    channel_id = Column(Integer, ForeignKey("Channel.id"), nullable=True)
    contact_assignments = relationship("CampaignContact", back_populates="campaign")

# --- Modelo Advisor ---
class Advisor(Base):
    __tablename__ = "Advisor"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(String(50), nullable=True)
    status = Column(String(20), nullable=True)
    genre = Column(String(25), nullable=True)
    odoo_id = Column(String(50), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    commercial_assignments = relationship("CampaignContact", foreign_keys="CampaignContact.commercial_advisor_id", back_populates="commercial_advisor")
    medical_assignments = relationship("CampaignContact", foreign_keys="CampaignContact.medical_advisor_id", back_populates="medical_advisor")

# --- Modelo CampaignContact ---
class CampaignContact(Base):
    __tablename__ = "Campaign_Contact"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("Campaign.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("Contact.id"), nullable=False)
    commercial_advisor_id = Column(Integer, ForeignKey("Advisor.id"), nullable=True)
    medical_advisor_id = Column(Integer, ForeignKey("Advisor.id"), nullable=True)
    registration_date = Column(DateTime, server_default=func.now())
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
    summary = Column(String(255), nullable=True)
    sync_status = Column(String(20), nullable=False, default="new", index=True)
    campaign = relationship("Campaign", back_populates="contact_assignments")
    contact = relationship("Contact", back_populates="campaign_assignments")
    commercial_advisor = relationship("Advisor", foreign_keys=[commercial_advisor_id], back_populates="commercial_assignments")
    medical_advisor = relationship("Advisor", foreign_keys=[medical_advisor_id], back_populates="medical_assignments")
    order_products = relationship("OrderProduct", back_populates="campaign_contact")
    product_interactions = relationship("ProductInteraction", back_populates="campaign_contact")

# --- Modelo Product ---
class Product(Base):
    __tablename__ = "Product"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=True)
    order_products = relationship("OrderProduct", back_populates="product")
    product_interactions = relationship("ProductInteraction", back_populates="product")

# --- Modelo OrderProduct ---
class OrderProduct(Base):
    __tablename__ = "Order_Product"
    id = Column(Integer, primary_key=True, index=True)
    campaign_contact_id = Column(Integer, ForeignKey("Campaign_Contact.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("Product.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(DECIMAL(10, 2))
    campaign_contact = relationship("CampaignContact", back_populates="order_products")
    product = relationship("Product", back_populates="order_products")

# --- Modelo ProductInteraction ---
class ProductInteraction(Base):
    __tablename__ = "Product_Interaction"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("Product.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("Contact.id"), nullable=False)
    campaign_contact_id = Column(Integer, ForeignKey("Campaign_Contact.id"), nullable=True)
    interaction_type = Column(String(50))
    interaction_date = Column(DateTime)
    product = relationship("Product", back_populates="product_interactions")
    contact = relationship("Contact", back_populates="product_interactions")
    campaign_contact = relationship("CampaignContact", back_populates="product_interactions")