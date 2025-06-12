# app/services/campaign_contact_service.py

# Importa Session de sqlalchemy.orm para sesiones sincrónicas
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from datetime import datetime
from typing import Optional

# CORRECCIÓN 1: Import Path Incorrecto 
# Cambiado de 'from app.models import Contact, CampaignContact, Advisor'
# A:
from app.db.models import Contact, CampaignContact, Advisor # 
from app.core.logging import logger # Asumo que tienes un logger configurado


class CampaignContactService:
    def __init__(self, db: Session): # Cambiado a Session (sincrónica)
        """
        Inicializa el servicio con una sesión de base de datos sincrónica.
        """
        self.db = db

    def update_campaign_contact_by_manychat_id( # Ya no es 'async'
        self,
        manychat_id: str,
        # CORRECCIÓN 2B: Añadir especificidad de campaña - campaign_id opcional al servicio 
        campaign_id: Optional[int] = None, # Añadir este parámetro 
        # Accept extra kwargs for partial update
        **kwargs
    ) -> Optional[CampaignContact]:
        """
        Busca un Contacto por su ManyChat ID, luego encuentra su CampaignContact
        asociado y lo actualiza con los datos proporcionados.
        Esta versión es SÍNCRONA.

        Args:
            manychat_id (str): El ID de ManyChat del contacto a buscar.
            campaign_id (Optional[int]): El ID específico de la campaña si se desea actualizar una asignación específica. 
            medical_advisor_id (Optional[int]): El ID del Médico/Asesor.
            medical_assignment_date (Optional[datetime]): La fecha de asignación del médico.
            last_state (Optional[str]): El último estado del registro.

        Returns:
            Optional[CampaignContact]: El objeto CampaignContact actualizado si se encontró
                                       y se actualizó, de lo contrario None.
        Raises:
            ValueError: Si el ID de asesor médico proporcionado no existe,
                        o si no se encuentra el contacto o la asignación de campaña. 
        """
        logger.info(f"Iniciando actualización de CampaignContact para ManyChat ID: {manychat_id}")

        # 1. Buscar el Contacto en la tabla 'Contact' usando el manychat_id
        contact = self.db.query(Contact).filter(Contact.manychat_id == manychat_id).first() # 

        if not contact:
            logger.warning(f"Contacto con ManyChat ID '{manychat_id}' no encontrado.")
            # CORRECCIÓN 3: Mejorar manejo de errores - Levantar excepción 
            raise ValueError(f"El contacto (manychat_id='{manychat_id}') no existe.") # 

        logger.info(f"Contacto encontrado: ID {contact.id}, ManyChat ID: {contact.manychat_id}")

        # 2. Buscar el registro de Campaign_Contact asociado a ese Contact ID
        # CORRECCIÓN 2B: Mejorar Lógica de Búsqueda para manejar campaign_id 
        campaign_contact = self._find_campaign_contact(contact.id, campaign_id) # Usar la nueva función de ayuda 

        if not campaign_contact:
            logger.warning(f"CampaignContact para Contacto ID '{contact.id}' (Campaign ID: {campaign_id if campaign_id else 'No especificado'}) no encontrado.") # 
            # CORRECCIÓN 3: Mejorar manejo de errores - Levantar excepción con más contexto 
            if campaign_id: # 
                raise ValueError(f"No se encontró asignación de campaña (campaign_id={campaign_id}) para el contacto (contact_id={contact.id}).") # 
            else: # 
                raise ValueError(f"El contacto (manychat_id='{manychat_id}') no tiene asignaciones de campaña activas.") # 

        logger.info(f"CampaignContact encontrado: ID {campaign_contact.id}, Contact ID: {campaign_contact.contact_id}, Campaign ID: {campaign_contact.campaign_id}")

        # 3. Preparar los datos para la actualización
        # Only update fields that are present in kwargs
        for field, value in kwargs.items():
            if field == "medical_advisor_id":
                if value is not None:
                    advisor_exists = self.db.query(Advisor.id).filter(Advisor.id == value).one_or_none()
                    if not advisor_exists:
                        logger.error(f"Medical Advisor ID {value} no existe en la tabla Advisor.")
                        raise ValueError(f"El ID de Asesor Médico {value} no es válido. No se encontró en la tabla Advisor.")
                setattr(campaign_contact, field, value)
                logger.debug(f"Actualizando {field} a {value}")
            elif field == "medical_assignment_date":
                if value is not None:
                    setattr(campaign_contact, field, value)
                    logger.debug(f"Actualizando {field} a {value}")
                elif getattr(campaign_contact, field) is None:
                    now = datetime.utcnow()
                    setattr(campaign_contact, field, now)
                    logger.debug(f"{field} no proporcionado y nulo en DB, usando fecha actual: {now}")
            elif field in ["last_state"]:
                setattr(campaign_contact, field, value)
                logger.debug(f"Actualizando {field} a '{value}'")
            # Add more fields as needed

        # 4. Realizar la actualización en la base de datos
        try:
            self.db.add(campaign_contact) # 
            self.db.commit() # 
            self.db.refresh(campaign_contact) # 
            
            logger.info(f"CampaignContact ID {campaign_contact.id} actualizado exitosamente.")
            return campaign_contact

        except Exception as e:
            self.db.rollback() # 
            logger.error(f"Error al actualizar CampaignContact {campaign_contact.id}: {e}", exc_info=True)
            raise

    # CORRECCIÓN 2B: Añadir función auxiliar para la lógica de búsqueda de CampaignContact 
    def _find_campaign_contact(self, contact_id: int, campaign_id: Optional[int] = None) -> Optional[CampaignContact]: # 
        """
        Función auxiliar para buscar el CampaignContact.
        Si se proporciona campaign_id, busca el específico.
        De lo contrario, busca el más reciente por registration_date.
        """
        query = self.db.query(CampaignContact).filter(CampaignContact.contact_id == contact_id) # 

        if campaign_id: # 
            # Buscar Campaign_Contact específico 
            return query.filter(CampaignContact.campaign_id == campaign_id).first() # 
        else: # 
            # Buscar el más reciente si no se especifica 
            # Asumo que 'registration_date' es el campo para determinar la recencia.
            # Si no existe, deberías usar un campo como 'created_at' o 'updated_at'.
            return query.order_by(CampaignContact.registration_date.desc()).first() #