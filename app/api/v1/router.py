from fastapi import APIRouter

# Importa tus routers de endpoints existentes
from app.api.v1.endpoints.manychat import router as manychat_router
from app.api.v1.endpoints.reports import router as reports_router
# Si odoo.py tiene endpoints, descomenta la siguiente línea e inclúyelo
# from app.api.v1.endpoints.odoo import router as odoo_router # Descomentado si se usa Odoo
# --- NUEVAS IMPORTACIONES PARA CONTACT, CAMPAIGN, ADVISOR ---
from app.api.v1.endpoints.contact import router as contact_router
from app.api.v1.endpoints.campaign import router as campaign_router
from app.api.v1.endpoints.advisor import router as advisor_router
# -----------------------------------------------------------------------

api_router = APIRouter()

# Incluye los routers existentes con prefijos y tags para mejor organización
# Es una buena práctica usar 'prefix' para evitar conflictos de rutas
# y 'tags' para agrupar en la documentación de Swagger UI/Redoc.
api_router.include_router(manychat_router, prefix="/manychat", tags=["ManyChat"])
api_router.include_router(reports_router, prefix="/reports", tags=["Reports"])
# Incluye el router de odoo si lo vas a usar
# api_router.include_router(odoo_router, prefix="/odoo", tags=["Odoo"]) # COMENTADO: Asegúrate de que odoo.py exista y contenga un APIRouter

# --- NUEVAS INCLUSIONES DE ROUTERS PARA CONTACTS, CAMPAIGNS, ADVISORS ---
api_router.include_router(contact_router, prefix="/contacts", tags=["Contacts"])
api_router.include_router(campaign_router, prefix="/campaigns", tags=["Campaigns"])
api_router.include_router(advisor_router, prefix="/advisors", tags=["Advisors"])
# -------------------------------------------------------------------------------