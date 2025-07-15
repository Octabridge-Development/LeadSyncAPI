# app/api/v1/router.py

from fastapi import APIRouter

# Importa los routers de los endpoints de forma individual y explícita

from app.api.v1.endpoints.manychat import router as manychat_router
from app.api.v1.endpoints.reports import router as reports_router
# REMOVIDO: from app.api.v1.endpoints.contact import router as contact_router # Si era para sincronización de contactos con Odoo
from app.api.v1.endpoints.campaign import router as campaign_router
from app.api.v1.endpoints.advisor import router as advisor_router
from app.api.v1.endpoints.campaign_contact import router as campaign_contact_by_manychat_router
from app.api.v1.endpoints.channel import router as channel_router
# REMOVIDO: from app.api.v1.endpoints.odoo import router as odoo_router # Si era para sincronización de contactos con Odoo
from app.api.v1.endpoints.crm_opportunities import router as crm_opportunities_router # CAMBIO: Aseguramos el nombre correcto del router del endpoint que creamos

# Router principal que agrupará a todos los demás
router = APIRouter()

# Incluye los sub-routers con sus prefijos y etiquetas para una API bien organizada

router.include_router(manychat_router, prefix="/manychat", tags=["ManyChat"])
router.include_router(reports_router, prefix="/reports", tags=["Reports"])
# REMOVIDO: router.include_router(contact_router, prefix="/contacts", tags=["Contacts"]) # Si era para sincronización de contactos con Odoo
router.include_router(campaign_router, prefix="/campaigns", tags=["Campaigns"])
router.include_router(advisor_router, prefix="/advisors", tags=["Advisors"])
router.include_router(campaign_contact_by_manychat_router, prefix="/campaign-contacts", tags=["CampaignContact"])
router.include_router(channel_router, prefix="/channels", tags=["Channels"])
# REMOVIDO: router.include_router(odoo_router, prefix="/odoo", tags=["Odoo"]) # Si era para sincronización de contactos con Odoo

# NUEVO: Incluye el router de Oportunidades CRM
router.include_router(crm_opportunities_router, prefix="/crm", tags=["CRM Opportunities"]) # CAMBIO: Se usa el nombre de router correcto y un tag más específico