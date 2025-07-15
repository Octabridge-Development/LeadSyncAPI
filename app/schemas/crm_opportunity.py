# app/schemas/crm_opportunity.py

from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime

# Mapeo de stages ManyChat → Odoo stage_id
# Se recomienda que este mapeo sea una constante a nivel de módulo
# o incluso cargada desde configuración/base de datos si es muy dinámica.
# Por ahora, la mantenemos aquí como se especificó.
MANYCHAT_TO_ODOO_STAGE_ID: Dict[str, int] = { # Se añadió la anotación de tipo para mejor claridad
    "Recién Suscrito (Sin Asignar)": 16, # [cite: 19]
    "Recién suscrito Pendiente de AC": 17, # [cite: 19]
    "Retornó en AC": 18, # [cite: 19]
    "Comienza Atención Comercial": 19, # [cite: 19]
    "Retornó a Asesoría especializada": 20, # [cite: 19]
    "Derivado Asesoría Médica": 21, # [cite: 19]
    "Comienza Asesoría Médica": 22, # [cite: 21, 28, 29]
    "Terminó Asesoría Médica": 23, # [cite: 22, 30, 31]
    "No terminó Asesoría especializada Derivado a Comercial": 24, # [cite: 23, 32]
    "Comienza Cotización": 25, # [cite: 24, 33, 34]
    "Orden de venta Confirmada": 26 # [cite: 25, 35]
}

class CRMOpportunityEvent(BaseModel):
    manychat_id: str = Field(..., description="ID del contacto de ManyChat") # [cite: 50]
    stage_manychat: str = Field(..., description="Stage de ManyChat") # [cite: 52]
    # Eliminamos stage_odoo_id del constructor directo, ya que será calculado.
    # Se añade como una propiedad para el cálculo
    datetime_stage_change: datetime = Field(..., description="Timestamp del cambio de stage") # [cite: 54]
    advisor_id: Optional[str] = Field(None, description="ID del asesor (opcional)") # [cite: 55]

    # Añadimos una propiedad computada para stage_odoo_id.
    # Esto asegura que el valor se derive automáticamente del stage_manychat
    # cuando se acceda, y no se espere como entrada directa en la inicialización si no se provee.
    # Opcional: Si necesitas que el campo `stage_odoo_id` se serialice automáticamente al crear el modelo
    # a partir de un dict, puedes usar un @root_validator (Pydantic V1) o @model_validator (Pydantic V2).
    # Para este caso, un getter es suficiente y más claro para la lógica de mapeo.
    @property
    def stage_odoo_id(self) -> Optional[int]: # 
        """
        Devuelve el stage_id de Odoo correspondiente al stage de ManyChat. 
        Si no existe, retorna None.
        """
        return MANYCHAT_TO_ODOO_STAGE_ID.get(self.stage_manychat)

    # Puedes añadir un método para la validación si el stage_manychat NO tiene mapeo
    # para asegurar que no se creen eventos con stages inválidos antes de encolar.
    # Sin embargo, la validación principal se hace en el endpoint POST para decidir
    # si se encola o se lanza un error HTTP.