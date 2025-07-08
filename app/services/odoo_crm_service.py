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
        Busca un lead abierto (sequence < 10) para un manychat_id específico. [cite: 58]
        """
        print(f"Buscando lead abierto para manychat_id: {manychat_id}")
        # Lógica para buscar en Odoo
        search_criteria = [
            ('x_studio_manychatid_crm', '=', manychat_id), # [cite: 66]
            ('stage_id.sequence', '<', 10) # [cite: 67]
        ]
        # open_leads = odoo_connector.search('crm.lead', search_criteria)
        # return open_leads[0] if open_leads else None
        pass # Reemplazar con la llamada real a Odoo

    def _prepare_lead_values(self, lead_data: dict) -> dict:
        """
        Mapea los datos de ManyChat al formato requerido por Odoo.
        """
        # El worker buscará el stage_id basado en la secuencia.
        # Aquí preparamos el resto de los valores.
        return {
            "name": f"Oportunidad para {lead_data['first_name']}",
            "contact_name": f"{lead_data['first_name']} {lead_data.get('last_name', '')}".strip(),
            "phone": lead_data.get('phone'),
            "description": lead_data['state']['summary'], # [cite: 157]
            "x_studio_manychatid_crm": lead_data['manychat_id'], # [cite: 152]
            "x_studio_asesor_medico": lead_data.get('medical_advisor_id'), # [cite: 153]
            "x_studio_asesor_comercial": lead_data.get('commercial_advisor_id'), # [cite: 154]
            # Nota: 'stage_id' se manejará por separado, buscando el id a partir de 'sequence'.
        }

    def create_or_update_lead(self, lead_data: dict):
        """
        Lógica principal: busca un lead abierto y lo actualiza. Si no existe, crea uno nuevo. [cite: 57, 61]
        """
        manychat_id = lead_data['manychat_id'] # [cite: 62]
        
        # 1. Buscar leads ABIERTOS para este ManyChat ID [cite: 25, 63]
        open_lead_id = self._find_open_lead(manychat_id)
        
        # 2. Preparar los valores a escribir en Odoo
        prepared_values = self._prepare_lead_values(lead_data)

        # Aquí el worker deberá añadir el 'stage_id' correcto a 'prepared_values'
        # Ejemplo: sequence = lead_data['state']['sequence']
        # stage_id = odoo_connector.search('crm.stage', [('sequence', '=', sequence)])[0]
        # prepared_values['stage_id'] = stage_id

        if open_lead_id:
            # 3. Si existe un lead abierto, actualizarlo [cite: 69]
            print(f"Actualizando lead existente (ID: {open_lead_id}) en Odoo.")
            # odoo_connector.write('crm.lead', [open_lead_id], prepared_values) [cite: 70]
            return {"status": "updated", "odoo_id": open_lead_id}
        else:
            # 4. Si no hay leads abiertos, crear uno nuevo [cite: 26, 71]
            print("Creando nuevo lead en Odoo.")
            # new_lead_id = odoo_connector.create('crm.lead', prepared_values) [cite: 72]
            # return {"status": "created", "odoo_id": new_lead_id}
            return {"status": "created", "odoo_id": "dummy_id"} # Placeholder

# Instancia del servicio para ser usada por otros módulos
odoo_crm_service = OdooCRMService()