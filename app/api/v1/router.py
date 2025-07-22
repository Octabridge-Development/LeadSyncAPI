# app/api/v1/router.py

from fastapi import APIRouter

# Importa los routers de los endpoints de forma individual y explícita


from app.api.v1.endpoints.contact import router as contact_router
from app.api.v1.endpoints.campaign import router as campaign_router
from app.api.v1.endpoints.advisor import router as advisor_router
from app.api.v1.endpoints.campaign_contact import router as campaign_contact_router
from app.api.v1.endpoints.channel import router as channel_router
from app.api.v1.endpoints.crm_opportunities import router as crm_opportunities_router
from app.api.v1.endpoints.manychat import router as manychat_router
from app.api.v1.endpoints.reports import router as reports_router

# Router principal que agrupará a todos los demás
router = APIRouter()



# Orden lógico y limpio para Swagger UI
router.include_router(contact_router, prefix="/contacts", tags=["Contacts"])
router.include_router(campaign_router, prefix="/campaigns", tags=["Campaigns"])
router.include_router(advisor_router, prefix="/advisors", tags=["Advisors"])
router.include_router(campaign_contact_router, prefix="/campaign-contacts", tags=["CampaignContacts"])
router.include_router(channel_router, prefix="/channels", tags=["Channels"])
router.include_router(crm_opportunities_router, prefix="/crm", tags=["CRM Opportunities"])
router.include_router(manychat_router, prefix="/manychat", tags=["ManyChat"])
router.include_router(reports_router, prefix="/reports", tags=["Reports"])
