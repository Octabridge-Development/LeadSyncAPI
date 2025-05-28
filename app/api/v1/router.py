from fastapi import APIRouter

from app.api.v1.endpoints import manychat, reports

router = APIRouter()

# Incluir endpoints de ManyChat (contacto y campaña) y reports (health, etc.)
router.include_router(manychat.router)
router.include_router(reports.router)
# Si en el futuro hay endpoints en odoo.py, también se pueden incluir aquí
# from app.api.v1.endpoints import odoo
# router.include_router(odoo.router)