# function_app.py - VERSIÓN UNIVERSAL (reemplaza tu function_app.py actual)
import os
import sys
import logging
from datetime import datetime

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Detectar el entorno
is_azure_functions = os.environ.get('FUNCTIONS_WORKER_RUNTIME') is not None
is_azure_app_service = os.environ.get('WEBSITE_SITE_NAME') is not None

logger.info(f"🔍 Entorno detectado - Functions: {is_azure_functions}, App Service: {is_azure_app_service}")

try:
    # Intentar importar tu aplicación FastAPI existente
    logger.info("🔄 Intentando importar aplicación FastAPI existente...")
    from app.main import app as fastapi_app

    logger.info("✅ FastAPI app importada exitosamente")
    use_fastapi = True
except ImportError as e:
    logger.warning(f"⚠️ No se pudo importar FastAPI app: {str(e)}")
    logger.info("🔄 Creando aplicación básica...")
    use_fastapi = False

if use_fastapi:
    # Usar la aplicación FastAPI existente
    app = fastapi_app
    logger.info("✅ Usando aplicación FastAPI completa")
else:
    # Crear aplicación básica de respaldo
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse, HTMLResponse
    import json

    app = FastAPI(
        title="MiaSalud Integration API",
        description="API de integración ManyChat-Odoo-Azure SQL",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )


    @app.get("/", response_class=JSONResponse)
    async def root():
        """Endpoint raíz"""
        return {
            "message": "MiaSalud Integration API",
            "status": "active",
            "version": "1.0.0",
            "mode": "basic_fallback",
            "environment": {
                "functions": is_azure_functions,
                "app_service": is_azure_app_service
            },
            "endpoints": {
                "docs": "/docs",
                "redoc": "/redoc",
                "health": "/health",
                "webhook_contact": "/webhook/manychat/contact"
            }
        }


    @app.get("/health", response_class=JSONResponse)
    async def health_check():
        """Health check básico"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "MiaSalud Integration API",
            "mode": "basic_fallback"
        }


    @app.post("/webhook/manychat/contact", response_class=JSONResponse)
    async def manychat_webhook(request_data: dict):
        """Webhook básico para ManyChat"""
        try:
            # Validaciones básicas
            if not request_data.get('manychat_id'):
                raise HTTPException(status_code=400, detail="manychat_id requerido")

            logger.info(f"📨 Webhook recibido: {request_data.get('manychat_id')}")

            return {
                "status": "received",
                "message": "Evento procesado (modo básico)",
                "manychat_id": request_data.get('manychat_id'),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error en webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    # Endpoints adicionales para compatibilidad
    @app.get("/api/health", response_class=JSONResponse)
    async def api_health():
        """Health check en /api/health"""
        return await health_check()


    @app.get("/api/v1/health", response_class=JSONResponse)
    async def api_v1_health():
        """Health check en /api/v1/health"""
        return await health_check()


    @app.get("/api/docs", response_class=HTMLResponse)
    async def api_docs():
        """Redirige a /docs"""
        return HTMLResponse("""
        <html>
        <head><title>Redirecting...</title></head>
        <body>
        <h1>Redirecting to documentation...</h1>
        <script>window.location.href='/docs';</script>
        <a href="/docs">Click here if not redirected</a>
        </body>
        </html>
        """)


    logger.info("✅ Aplicación básica de respaldo creada")

# Para Azure Functions
if is_azure_functions:
    import azure.functions as func

    # Envolver la aplicación FastAPI para Azure Functions
    azure_app = func.AsgiFunctionApp(app=app, http_auth_level=func.AuthLevel.ANONYMOUS)
    logger.info("🔧 Configurado para Azure Functions")

# Para compatibilidad con Gunicorn (Azure App Service)
# La variable 'app' ya está definida y Gunicorn la puede usar directamente

logger.info("🚀 MiaSalud Integration API inicializada correctamente")

# Si se ejecuta directamente (para testing local)
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🌐 Ejecutando servidor de desarrollo en puerto {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)