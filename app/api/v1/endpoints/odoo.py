from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from app.services.odoo_service import odoo_service
from app.schemas.odoo import OdooContactCreate
from app.schemas.odoo_update import OdooContactUpdate
from typing import List, Any
from app.core.config import get_settings

router = APIRouter()  # Sin tags ni prefix globales

@router.get("/contacts/short/", response_model=List[dict], tags=["Odoo"], summary="Obtener los 10 contactos más recientes (campos clave)")
def get_short_contacts():
    """Obtiene los 10 contactos más recientes de Odoo con solo los campos clave para sincronización, incluyendo manychat_id."""
    try:
        ids = odoo_service.execute("res.partner", "search", [], 0, 10, "create_date desc")
        fields = [
            "id", "name", "email", "phone", "create_date", "write_date", "active", "x_studio_manychatid_customer"
        ]
        contacts = odoo_service.execute("res.partner", "read", ids, fields)
        return contacts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/contacts/by_manychat_id/{manychat_id}", response_model=Any, tags=["Odoo"], summary="Obtener contacto por manychat_id")
def get_contact_by_manychat_id(manychat_id: str):
    """Obtiene un contacto de Odoo (res.partner) por su manychat_id (campo x_studio_manychatid_customer)."""
    try:
        partner_ids = odoo_service.execute("res.partner", "search", [("x_studio_manychatid_customer", "=", manychat_id)])
        if not partner_ids:
            raise HTTPException(status_code=404, detail="Contacto no encontrado para ese manychat_id")
        contact = odoo_service.execute("res.partner", "read", [partner_ids[0]])
        if contact:
            return contact[0]
        else:
            raise HTTPException(status_code=404, detail="Contacto no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/contacts/{contact_id}", response_model=Any, tags=["Odoo"], summary="Eliminar contacto por ID (requiere confirmación)")
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

@router.put("/contacts/{contact_id}", response_model=Any, tags=["Odoo"], summary="Actualizar campos permitidos de un contacto por ID")
def update_contact(contact_id: int, updates: OdooContactUpdate = Body(..., description="Campos a actualizar en el contacto de Odoo")):
    """Actualiza campos permitidos de un contacto de Odoo (res.partner) por su ID."""
    try:
        contact = odoo_service.execute("res.partner", "read", [contact_id])
        if not contact:
            raise HTTPException(status_code=404, detail="Contacto no encontrado")
        update_data = updates.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")
        result = odoo_service.execute("res.partner", "write", [contact_id, update_data])
        if result:
            updated = odoo_service.execute("res.partner", "read", [contact_id])
            return updated[0] if updated else {}
        else:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el contacto")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/contacts/sync_manychat/", response_model=Any, tags=["Odoo"], summary="Sincronizar contacto por manychatID (crea o actualiza)")
def sync_manychat_contact(contact: OdooContactCreate):
    """Crea o actualiza un contacto en Odoo según el manychatID. Si existe, actualiza teléfono/celular; si no, crea."""
    try:
        # Buscar por manychatID
        manychat_id = getattr(contact, 'x_studio_manychatid_customer', None) or getattr(contact, 'manychat_id', None)
        if not manychat_id:
            raise HTTPException(status_code=400, detail="Falta el campo manychatID (x_studio_manychatid_customer)")
        # Construir dict para Odoo
        contact_dict = contact.dict(exclude_unset=True)
        # Buscar si existe en Odoo
        partner_ids = odoo_service.execute("res.partner", "search", [("x_studio_manychatid_customer", "=", manychat_id)])
        if partner_ids:
            # Actualizar teléfono/celular y otros campos permitidos
            odoo_service.execute("res.partner", "write", [partner_ids[0], contact_dict])
            updated = odoo_service.execute("res.partner", "read", [partner_ids[0]])
            return {"result": "updated", "contact": updated[0] if updated else {}}
        else:
            # Crear nuevo contacto
            new_id = odoo_service.execute("res.partner", "create", [contact_dict])
            new_contact = odoo_service.execute("res.partner", "read", [new_id])
            return {"result": "created", "contact": new_contact[0] if new_contact else {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
