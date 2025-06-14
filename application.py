# application.py
import logging
import os
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

is_azure_functions = os.environ.get('FUNCTIONS_WORKER_RUNTIME') is not None
is_azure_app_service = os.environ.get('WEBSITE_SITE_NAME') is not None

logger.info(f"🔍 Entorno detectado - Functions: {is_azure_functions}, App Service: {is_azure_app_service}")

try:
    logger.info("🔄 Intentando importar aplicación FastAPI completa desde app.main...")
    from app.main import app as fastapi_app
    logger.info("✅ app.main importada exitosamente.")
    use_full_app = True
except ImportError as e:
    logger.warning(f"⚠️ No se pudo importar app.main: {e}. Activando modo de respaldo.")
    use_full_app = False

if use_full_app:
    app = fastapi_app
    logger.info("✅ Usando aplicación FastAPI completa.")
else:
    logger.info("🔄 Creando aplicación FastAPI de respaldo...")
    from fastapi import FastAPI, Depends, HTTPException, Header
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    from typing import Optional
    from app.core.config import get_settings, Settings # <-- IMPORTAMOS LA CONFIGURACIÓN

    app = FastAPI(title="MiaSalud API (Modo de Respaldo)")

    # --- INICIO DE LA CORRECCIÓN ---
    # Esta función ahora usa la configuración centralizada para la API Key.
    # Es mucho más segura y consistente.
    def verify_api_key(
        x_api_key: str = Header(None),
        settings: Settings = Depends(get_settings)
    ):
        if x_api_key != settings.API_KEY:
            raise HTTPException(status_code=401, detail="API Key inválido o ausente")
    # --- FIN DE LA CORRECCIÓN ---

    @app.get("/")
    async def root():
        return {"message": "MiaSalud API (Modo de Respaldo)"}

    # Creamos un endpoint de ejemplo que usa la protección de API Key
    class ExamplePayload(BaseModel):
        info: str

    @app.post("/example_webhook", dependencies=[Depends(verify_api_key)])
    async def example_webhook(payload: ExamplePayload):
        logger.info("Webhook de ejemplo (respaldo) recibido.", payload_info=payload.info)
        return {"status": "success", "message": "Webhook de respaldo procesado"}

    logger.info("✅ Aplicación FastAPI de respaldo creada.")

logger.info(f"🚀 MiaSalud Integration API inicializada.")
logger.info(f"📱 Modo: {'Completo' if use_full_app else 'Respaldo'}")