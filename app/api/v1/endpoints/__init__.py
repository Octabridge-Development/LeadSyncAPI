# app/api/v1/endpoints/__init__.py

# Mantén solo las importaciones necesarias, si alguna otra parte de tu código
# espera importar estos módulos de forma directa como 'from app.api.v1.endpoints import manychat'
# Si no, puedes eliminarlas también para reducir la superficie.
from . import manychat
from . import odoo # Descomenta si odoo.py tiene rutas
from . import reports

# --- SE REMUEVEN LAS IMPORTACIONES DE CONTACT, CAMPAIGN, ADVISOR DE AQUÍ ---
# Ya que router.py los importa directamente, no es necesario que __init__.py los exponga,
# y esto es lo que está causando la importación circular.
# from . import contact
# from . import campaign
# from . import advisor
# -------------------------------------------------------------------------

# No es necesario definir __all__ si no usas 'from package import *' en otras partes del código.
# Si lo usas, asegúrate de listar solo los módulos que realmente necesites exponer y que no causen circulares.
# __all__ = ["manychat", "odoo", "reports"]