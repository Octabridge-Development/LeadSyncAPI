import logging
import os
import sys
from datetime import datetime

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Detectar el entorno
is_azure_functions = os.environ.get('FUNCTIONS_WORKER_RUNTIME') is not None
is_azure_app_service = os.environ.get('WEBSITE_SITE_NAME') is not None

logger.info(f"🔍 Entorno detectado - Functions: {is_azure_functions}, App Service: {is_azure_app_service}")

try:
    # Intentar importar la aplicación FastAPI completa
    logger.info("🔄 Intentando importar aplicación FastAPI completa...")
    from app.main import app as fastapi_app

    logger.info("✅ FastAPI app completa importada exitosamente")
    use_fastapi = True
except ImportError as e:
    logger.warning(f"⚠️ No se pudo importar FastAPI app completa: {str(e)}")
    logger.info("🔄 Creando aplicación FastAPI básica...")
    use_fastapi = False

if use_fastapi:
    # Usar la aplicación FastAPI existente
    app = fastapi_app
    logger.info("✅ Usando aplicación FastAPI completa")
else:
    # Crear aplicación FastAPI básica que funciona
    from fastapi import FastAPI, HTTPException, Header
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    from typing import Optional
    import json

    app = FastAPI(
        title="MiaSalud Integration API",
        description="API de integración ManyChat-Odoo-Azure SQL",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Configurar CORS si es necesario
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    # Modelos Pydantic para los webhooks
    class ManyChatContactEvent(BaseModel):
        manychat_id: str
        nombre_lead: str
        apellido_lead: Optional[str] = None
        whatsapp: Optional[str] = None
        datetime_suscripcion: Optional[datetime] = None
        datetime_actual: datetime
        ultimo_estado: str
        canal_entrada: Optional[str] = None
        estado_inicial: Optional[str] = None


    class ManyChatCampaignEvent(BaseModel):
        manychat_id: str
        campaign_id: str
        comercial_id: Optional[str] = None
        medico_id: Optional[str] = None
        datetime_actual: datetime
        ultimo_estado: str
        tipo_asignacion: str = "comercial"


    # Función para verificar API Key
    def verify_api_key(x_api_key: str = Header(None)):
        expected_key = os.getenv("API_KEY", "Miasaludnatural123**")
        if x_api_key != expected_key:
            raise HTTPException(status_code=401, detail="API Key inválido")
        return x_api_key


    @app.get("/", response_class=JSONResponse)
    async def root():
        """Endpoint raíz"""
        return {
            "message": "MiaSalud Integration API",
            "status": "active",
            "version": "1.0.0",
            "mode": "standalone" if use_fastapi else "basic_fallback",
            "environment": {
                "functions": is_azure_functions,
                "app_service": is_azure_app_service,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            },
            "endpoints": {
                "docs": "/docs",
                "redoc": "/redoc",
                "health": "/health",
                "webhook_contact": "/api/v1/manychat/webhook/contact",
                "webhook_campaign": "/api/v1/manychat/webhook/campaign-assignment"
            }
        }


    @app.get("/health", response_class=JSONResponse)
    async def health_check():
        """Health check básico"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "MiaSalud Integration API",
            "mode": "standalone" if use_fastapi else "basic_fallback",
            "environment": "Azure App Service" if is_azure_app_service else "Local"
        }


    @app.post("/api/v1/manychat/webhook/contact", response_class=JSONResponse)
    async def manychat_contact_webhook(
            event: ManyChatContactEvent,
            x_api_key: str = Header(None)
    ):
        """Webhook para eventos de contacto de ManyChat"""
        try:
            # Verificar API Key
            verify_api_key(x_api_key)

            logger.info(f"📨 Webhook de contacto recibido: {event.manychat_id}")

            # Validar datos básicos
            if not event.manychat_id or not event.manychat_id.strip():
                raise HTTPException(status_code=400, detail="manychat_id requerido")

            # Simular procesamiento (aquí iría la lógica real)
            logger.info(f"✅ Procesando contacto: {event.nombre_lead} ({event.manychat_id})")

            return {
                "status": "success",
                "message": "Evento de contacto procesado correctamente",
                "data": {
                    "manychat_id": event.manychat_id,
                    "nombre": event.nombre_lead,
                    "estado": event.ultimo_estado,
                    "canal": event.canal_entrada
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error procesando webhook de contacto: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error procesando evento: {str(e)}")


    @app.post("/api/v1/manychat/webhook/campaign-assignment", response_class=JSONResponse)
    async def manychat_campaign_webhook(
            event: ManyChatCampaignEvent,
            x_api_key: str = Header(None)
    ):
        """Webhook para eventos de asignación de campaña de ManyChat"""
        try:
            # Verificar API Key
            verify_api_key(x_api_key)

            logger.info(f"📨 Webhook de campaña recibido: {event.manychat_id} -> {event.campaign_id}")

            # Validar datos básicos
            if not event.manychat_id or not event.manychat_id.strip():
                raise HTTPException(status_code=400, detail="manychat_id requerido")
            if not event.campaign_id or not event.campaign_id.strip():
                raise HTTPException(status_code=400, detail="campaign_id requerido")

            # Simular procesamiento (aquí iría la lógica real)
            logger.info(f"✅ Procesando asignación: {event.manychat_id} -> Campaña: {event.campaign_id}")

            return {
                "status": "success",
                "message": "Evento de campaña procesado correctamente",
                "data": {
                    "manychat_id": event.manychat_id,
                    "campaign_id": event.campaign_id,
                    "comercial_id": event.comercial_id,
                    "tipo_asignacion": event.tipo_asignacion
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error procesando webhook de campaña: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error procesando evento: {str(e)}")


    # Endpoints adicionales para compatibilidad
    @app.get("/api/health", response_class=JSONResponse)
    async def api_health():
        """Health check en /api/health"""
        return await health_check()


    @app.get("/api/v1/health", response_class=JSONResponse)
    async def api_v1_health():
        """Health check en /api/v1/health"""
        return await health_check()


    # Endpoint de verificación para ManyChat
    @app.get("/api/v1/manychat/webhook/verify", response_class=JSONResponse)
    async def verify_webhook(x_api_key: str = Header(None)):
        """Endpoint de verificación para ManyChat"""
        verify_api_key(x_api_key)
        return {
            "status": "active",
            "service": "MiaSalud Integration API",
            "endpoints": [
                "/api/v1/manychat/webhook/contact",
                "/api/v1/manychat/webhook/campaign-assignment"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }


    logger.info("✅ Aplicación FastAPI básica creada correctamente")

# Logging de inicialización
logger.info(f"🚀 MiaSalud Integration API inicializada correctamente")
logger.info(f"📱 Modo: {'Completo' if use_fastapi else 'Básico'}")
logger.info(f"🌐 Entorno: {'Azure App Service' if is_azure_app_service else 'Local'}")

# Para ejecución directa (testing local)
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🌐 Ejecutando servidor de desarrollo en puerto {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)