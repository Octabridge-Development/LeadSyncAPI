from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from app.services.odoo_service import odoo_service
from app.schemas.odoo import OdooContactCreate
from typing import List, Any
from app.core.config import get_settings

router = APIRouter()

@router.get("/contacts/", response_model=List[Any])
def get_all_contacts():
    """Obtiene 20 contactos de Odoo (res.partner)."""
    try:
        ids = odoo_service.execute("res.partner", "search", [], 0, 20)  # offset=0, limit=20
        contacts = odoo_service.execute("res.partner", "read", ids)
        return contacts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/contacts/", response_model=Any)
def create_contact(contact: OdooContactCreate):
    """Crea un nuevo contacto en Odoo (res.partner)."""
    try:
        contact_dict = contact.dict(exclude_unset=True)
        contact_id = odoo_service.execute("res.partner", "create", [contact_dict])
        new_contact = odoo_service.execute("res.partner", "read", [contact_id])
        return new_contact[0] if new_contact else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/contacts/{contact_id}", response_model=Any)
def get_contact_by_id(contact_id: int):
    """Obtiene un contacto específico de Odoo (res.partner) por su ID."""
    try:
        contact = odoo_service.execute("res.partner", "read", [contact_id])
        if contact:
            return contact[0]
        else:
            raise HTTPException(status_code=404, detail="Contacto no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/contacts/{contact_id}", response_model=Any)
def delete_contact(contact_id: int, confirm: str = Query(..., description="Debes ingresar el nombre de la base de datos para confirmar la eliminación")):
    """Elimina un contacto de Odoo por ID, solo si el parámetro confirm coincide con el nombre de la base de datos."""
    settings = get_settings()
    if confirm != settings.ODOO_DB:
        raise HTTPException(status_code=403, detail="Confirmación inválida. Debes ingresar el nombre correcto de la base de datos.")
    try:
        result = odoo_service.execute("res.partner", "unlink", [contact_id])
        if result:
            return {"detail": f"Contacto {contact_id} eliminado correctamente."}
        else:
            raise HTTPException(status_code=404, detail="Contacto no encontrado o no se pudo eliminar")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/contacts/{contact_id}", response_model=Any)
def update_contact(contact_id: int, updates: dict = Body(..., description="Campos a actualizar en el contacto de Odoo")):
    """Actualiza campos específicos de un contacto de Odoo (res.partner) por su ID."""
    try:
        # Verificar si el contacto existe
        contact = odoo_service.execute("res.partner", "read", [contact_id])
        if not contact:
            raise HTTPException(status_code=404, detail="Contacto no encontrado")
        # Realizar la actualización
        result = odoo_service.execute("res.partner", "write", [contact_id, updates])
        if result:
            updated = odoo_service.execute("res.partner", "read", [contact_id])
            return updated[0] if updated else {}
        else:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el contacto")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/contacts/short/", response_model=List[dict])
def get_short_contacts():
    """Obtiene 20 contactos de Odoo con solo los campos clave para sincronización."""
    try:
        ids = odoo_service.execute("res.partner", "search", [], 0, 20)
        fields = ["id", "name", "email", "phone", "create_date", "write_date", "active"]
        contacts = odoo_service.execute("res.partner", "read", ids, fields)
        return contacts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
