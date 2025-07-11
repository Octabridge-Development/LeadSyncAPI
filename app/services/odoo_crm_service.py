from app.services.odoo_service import odoo_service

# app/services/odoo_crm_service.py

# Suponiendo que tienes una forma de conectar con Odoo, ej. a través de odoorpc o una librería similar.
# Este es un ejemplo y necesitarás adaptarlo a tu conector de Odoo.
# odoo_connector = OdooConnector() 

class OdooCRMService:
    """
    Servicio principal para manejar la lógica de negocio de Odoo CRM. [cite: 55]
    """

    def _find_open_lead(self, manychat_id: str):
        """
        Busca un lead abierto (stage_id < 10) para un manychat_id específico en Odoo.
        """
        search_criteria = [
            ('x_studio_manychatid_crm', '=', manychat_id),
            ('stage_id', '!=', False),
            ('stage_id.sequence', '<', 10)
        ]
        lead_ids = odoo_service.execute('crm.lead', 'search', search_criteria)
        return lead_ids[0] if lead_ids else None

    def _get_odoo_partner_id(self, manychat_id):
        """
        Busca el contacto en Odoo por ManychatID y retorna su partner_id.
        """
        partner_ids = odoo_service.execute('res.partner', 'search', [('x_studio_manychatid_customer', '=', manychat_id)])
        return partner_ids[0] if partner_ids else None

    def _prepare_lead_values(self, lead_data):
        """
        Mapea los datos de ManyChat al formato requerido por Odoo, incluyendo el contacto relacionado.
        """
        partner_id = self._get_odoo_partner_id(lead_data.manychat_id)
        full_name = f"{lead_data.first_name} {lead_data.last_name or ''}".strip()
        vals = {
            "name": full_name,  # El nombre de la oportunidad será el nombre completo del contacto
            "contact_name": full_name,
            "phone": lead_data.phone,
            "description": lead_data.state.summary,
            "x_studio_manychatid_crm": lead_data.manychat_id,
            "x_studio_asesor_medico": lead_data.medical_advisor_id,
            "x_studio_asesor_comercial": lead_data.commercial_advisor_id,
            "partner_id": partner_id,
        }
        # Puedes agregar más campos aquí si lo necesitas
        return vals

    def create_or_update_lead(self, lead_data):
        """
        Busca un lead abierto y lo actualiza. Si no existe, crea uno nuevo en Odoo.
        """
        manychat_id = lead_data.manychat_id
        state = lead_data.state
        stage_id = getattr(state, 'stage_id', None)
        prepared_values = self._prepare_lead_values(lead_data)
        prepared_values['stage_id'] = stage_id
        # Buscar lead abierto
        open_lead_id = self._find_open_lead(manychat_id)
        if open_lead_id:
            # Actualizar lead existente
            odoo_service.execute('crm.lead', 'write', [open_lead_id], prepared_values)
            print(f"Actualizando lead existente (ID: {open_lead_id}) en Odoo a stage_id {stage_id}.")
            return {"status": "updated", "odoo_id": open_lead_id, "stage_id": stage_id}
        else:
            # Crear nuevo lead
            new_lead_id = odoo_service.execute('crm.lead', 'create', prepared_values)
            print(f"Creando nuevo lead en Odoo en stage_id {stage_id}.")
            return {"status": "created", "odoo_id": new_lead_id, "stage_id": stage_id}

# Instancia del servicio para ser usada por otros módulos
odoo_crm_service = OdooCRMService()