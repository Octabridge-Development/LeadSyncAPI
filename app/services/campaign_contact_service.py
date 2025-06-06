# app/services/campaign_contact_service.py

# Importa Session de sqlalchemy.orm para sesiones sincrónicas
from sqlalchemy.orm import Session 
from sqlalchemy import select, update
from datetime import datetime
from typing import Optional

# Importa tus modelos de base de datos. La ruta 'app.models' es correcta.
from app.models import Contact, CampaignContact, Advisor 
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
        medical_advisor_id: Optional[int] = None,
        medical_assignment_date: Optional[datetime] = None,
        last_state: Optional[str] = None
    ) -> Optional[CampaignContact]:
        """
        Busca un Contacto por su ManyChat ID, luego encuentra su CampaignContact
        asociado y lo actualiza con los datos proporcionados.
        Esta versión es SÍNCRONA.

        Args:
            manychat_id (str): El ID de ManyChat del contacto a buscar.
            medical_advisor_id (Optional[int]): El ID del Médico/Asesor.
            medical_assignment_date (Optional[datetime]): La fecha de asignación del médico.
            last_state (Optional[str]): El último estado del registro.

        Returns:
            Optional[CampaignContact]: El objeto CampaignContact actualizado si se encontró
                                      y se actualizó, de lo contrario None.
        Raises:
            ValueError: Si el ID de asesor médico proporcionado no existe.
        """
        logger.info(f"Iniciando actualización de CampaignContact para ManyChat ID: {manychat_id}")

        # 1. Buscar el Contacto en la tabla 'Contact' usando el manychat_id
        # Para consultas sincrónicas, se usa .scalar_one_or_none() o .first() directamente
        contact = self.db.query(Contact).filter(Contact.manychat_id == manychat_id).first()

        if not contact:
            logger.warning(f"Contacto con ManyChat ID '{manychat_id}' no encontrado.")
            return None 

        logger.info(f"Contacto encontrado: ID {contact.id}, ManyChat ID: {contact.manychat_id}")

        # 2. Buscar el registro de Campaign_Contact asociado a ese Contact ID
        # Asumimos que para esta operación, buscamos el primer CampaignContact asociado.
        # Si un contacto puede tener múltiples CampaignContact activos y necesitas un criterio
        # más específico (ej. por campaign_id), se debería añadir un parámetro adicional.
        campaign_contact = self.db.query(CampaignContact).filter(CampaignContact.contact_id == contact.id).first()

        if not campaign_contact:
            logger.warning(f"CampaignContact para Contacto ID '{contact.id}' no encontrado.")
            return None 

        logger.info(f"CampaignContact encontrado: ID {campaign_contact.id}, Contact ID: {campaign_contact.contact_id}")

        # 3. Preparar los datos para la actualización
        # Ahora actualizamos directamente el objeto SQLAlchemy y luego hacemos commit.
        # No necesitamos un diccionario 'update_data' para .values() con ORM sincrónico.
        
        # Verificar si se proporcionó un medical_advisor_id y si es diferente al actual
        if medical_advisor_id is not None and medical_advisor_id != campaign_contact.medical_advisor_id:
            # Opcional pero recomendado: Verificar si el medical_advisor_id existe en la tabla Advisor
            advisor_exists = self.db.query(Advisor.id).filter(Advisor.id == medical_advisor_id).scalar_one_or_none()
            if not advisor_exists:
                logger.error(f"Medical Advisor ID {medical_advisor_id} no existe en la tabla Advisor.")
                raise ValueError(f"El ID de Asesor Médico {medical_advisor_id} no es válido. No se encontró en la tabla Advisor.")
            
            campaign_contact.medical_advisor_id = medical_advisor_id
            logger.debug(f"Actualizando medical_advisor_id a {medical_advisor_id}")

        # Verificar si se proporcionó medical_assignment_date y si es diferente al actual
        if medical_assignment_date is not None and medical_assignment_date != campaign_contact.medical_assignment_date:
            campaign_contact.medical_assignment_date = medical_assignment_date
            logger.debug(f"Actualizando medical_assignment_date a {medical_assignment_date}")
        elif medical_assignment_date is None and campaign_contact.medical_assignment_date is None:
            # Si no se proporcionó una fecha y la columna está vacía, usar la fecha y hora UTC actuales
            # Ten en cuenta que si ya tiene un valor, no se sobrescribe con la fecha actual si medical_assignment_date es None.
            campaign_contact.medical_assignment_date = datetime.utcnow()
            logger.debug(f"medical_assignment_date no proporcionado y nulo en DB, usando fecha actual: {campaign_contact.medical_assignment_date}")


        # Verificar si se proporcionó last_state y si es diferente al actual
        if last_state is not None and last_state != campaign_contact.last_state:
            campaign_contact.last_state = last_state
            logger.debug(f"Actualizando last_state a '{last_state}'")

        # Comprobar si se realizaron cambios reales para evitar un commit innecesario
        # SQLAlchemy marca los objetos como "dirty" si hay cambios
        if not self.db.is_modified(campaign_contact, include_collections=False):
            logger.info("No se detectaron cambios reales en el objeto CampaignContact para actualizar.")
            return campaign_contact


        # 4. Realizar la actualización en la base de datos
        try:
            # Aunque el objeto ya esté en la sesión, .add() es inofensivo y asegura que los cambios
            # hechos fuera de la sesión sean reconocidos.
            self.db.add(campaign_contact) 
            self.db.commit()              # Confirma la transacción
            self.db.refresh(campaign_contact) # Refresca el objeto para obtener los datos más recientes de la DB
            
            logger.info(f"CampaignContact ID {campaign_contact.id} actualizado exitosamente.")
            return campaign_contact

        except Exception as e:
            self.db.rollback() # Revierte la transacción si ocurre un error
            logger.error(f"Error al actualizar CampaignContact {campaign_contact.id}: {e}", exc_info=True)
            raise 

