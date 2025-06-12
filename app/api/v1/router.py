from fastapi import APIRouter

# Importa los routers de los endpoints
from app.api.v1.endpoints.manychat import router as manychat_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.contact import router as contact_router
from app.api.v1.endpoints.campaign import router as campaign_router
from app.api.v1.endpoints.advisor import router as advisor_router
from app.api.v1.endpoints.campaign_contact import router as campaign_contact_by_manychat_router
from app.api.v1.endpoints.channel import router as channel_router

# Router principal - CAMBIADO a 'router' para consistencia
router = APIRouter()

# Incluye los sub-routers (actualizado para usar 'router')
router.include_router(manychat_router, prefix="/manychat", tags=["ManyChat"])
router.include_router(reports_router, prefix="/reports", tags=["Reports"])
router.include_router(contact_router, prefix="/contacts", tags=["Contacts"])
router.include_router(campaign_router, prefix="/campaigns", tags=["Campaigns"])
router.include_router(advisor_router, prefix="/advisors", tags=["Advisors"])
router.include_router(campaign_contact_by_manychat_router, prefix="/campaign-contacts", tags=["CampaignContact"])
router.include_router(channel_router, prefix="/channels", tags=["Channels"])
=======
from fastapi import APIRouter

from app.api.v1.endpoints import manychat, reports

router = APIRouter()

# Incluir endpoints de ManyChat (contacto y campaña) y reports (health, etc.)
router.include_router(manychat.router)
router.include_router(reports.router)
# Si en el futuro hay endpoints en odoo.py, también se pueden incluir aquí
# from app.api.v1.endpoints import odoo
# router.include_router(odoo.router)
from fastapi import APIRouter

from app.api.v1.endpoints import manychat, reports

router = APIRouter()

# Incluir endpoints de ManyChat (contacto y campaña) y reports (health, etc.)
router.include_router(manychat.router)
router.include_router(reports.router)
# Si en el futuro hay endpoints en odoo.py, también se pueden incluir aquí
# from app.api.v1.endpoints import odoo
# router.include_router(odoo.router)