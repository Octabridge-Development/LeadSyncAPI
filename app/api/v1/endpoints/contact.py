from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Asegúrate de que estas importaciones sean correctas para tu configuración
from app.db.session import SessionLocal # Usado para Type Hinting si no se usa directamente
from app.db import models
from app.api import deps # Para get_db_session
from app.schemas.contact import ContactCreate, ContactUpdate, ContactInDB # Asegúrate que sean correctas

router = APIRouter()

@router.get("/", response_model=List[ContactInDB], summary="Obtener todos los contactos")
def read_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db_session)):
    """
    Obtiene una lista paginada de todos los contactos.
    """
    contacts = db.query(models.Contact).offset(skip).limit(limit).all()
    return contacts

@router.get("/{contact_id}", response_model=ContactInDB, summary="Obtener contacto por ID")
def read_contact(contact_id: int, db: Session = Depends(deps.get_db_session)):
    """
    Obtiene un contacto específico usando su ID.
    """
    contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado")
    return contact

@router.post("/", response_model=ContactInDB, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo contacto")
def create_contact(contact: ContactCreate, db: Session = Depends(deps.get_db_session)):
    """
    Crea un nuevo contacto con la información proporcionada.
    Valida que 'manychat_id' sea único.
    """
    # Verificar si manychat_id ya existe para evitar duplicados
    existing_contact = db.query(models.Contact).filter(models.Contact.manychat_id == contact.manychat_id).first()
    if existing_contact:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un contacto con manychat_id '{contact.manychat_id}'"
        )
    
    # Convertir el esquema Pydantic a un objeto de modelo SQLAlchemy
    db_contact = models.Contact(**contact.model_dump()) # .model_dump() para Pydantic v2+
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact) # Actualiza el objeto con los datos generados por la DB (ej. ID)
    return db_contact

@router.put("/{contact_id}", response_model=ContactInDB, summary="Actualizar contacto por ID")
def update_contact(contact_id: int, contact_update: ContactUpdate, db: Session = Depends(deps.get_db_session)):
    """
    Actualiza un contacto existente por su ID.
    Los campos no proporcionados en el cuerpo de la solicitud no serán modificados.
    """
    db_contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado")

    # exclude_unset=True asegura que solo los campos realmente enviados en la solicitud se usen para actualizar
    update_data = contact_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_contact, key, value)
    
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar contacto por ID")
def delete_contact(contact_id: int, db: Session = Depends(deps.get_db_session)):
    """
    Elimina un contacto específico usando su ID.
    """
    db_contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado")
    
    db.delete(db_contact)
    db.commit()
    return {"message": "Contacto eliminado exitosamente"}
