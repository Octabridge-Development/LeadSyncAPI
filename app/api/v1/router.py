from fastapi import APIRouter

# Importa los routers de los endpoints de forma individual y explícita
from app.api.v1.endpoints.manychat import router as manychat_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.contact import router as contact_router
from app.api.v1.endpoints.campaign import router as campaign_router
from app.api.v1.endpoints.advisor import router as advisor_router
from app.api.v1.endpoints.campaign_contact import router as campaign_contact_by_manychat_router
from app.api.v1.endpoints.channel import router as channel_router
from app.api.v1.endpoints.odoo import router as odoo_router

# Router principal que agrupará a todos los demás
router = APIRouter()

# Incluye los sub-routers con sus prefijos y etiquetas para una API bien organizada
router.include_router(manychat_router, prefix="/manychat", tags=["ManyChat"])
router.include_router(reports_router, prefix="/reports", tags=["Reports"])
router.include_router(contact_router, prefix="/contacts", tags=["Contacts"])
router.include_router(campaign_router, prefix="/campaigns", tags=["Campaigns"])
router.include_router(advisor_router, prefix="/advisors", tags=["Advisors"])
router.include_router(campaign_contact_by_manychat_router, prefix="/campaign-contacts", tags=["CampaignContact"])
router.include_router(channel_router, prefix="/channels", tags=["Channels"])
router.include_router(odoo_router, prefix="/odoo", tags=["Odoo"])