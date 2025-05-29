# function_app.py - VERSIÓN CORREGIDA PARA AZURE FUNCTIONS V2
import azure.functions as func
import logging
import json
from datetime import datetime

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===============================================
# MÉTODO 1: IMPORTAR LA APP FASTAPI (RECOMENDADO)
# ===============================================

def create_fastapi_function_app():
    """
    Intenta cargar la aplicación FastAPI y exponerla como Azure Function.
    """
    try:
        logger.info("🔄 Intentando cargar aplicación FastAPI...")

        # Importar la aplicación FastAPI
        from app.main import app as fastapi_app

        logger.info("✅ FastAPI aplicación cargada exitosamente")

        # Crear AsgiFunctionApp que expone toda la FastAPI app
        function_app = func.AsgiFunctionApp(
            app=fastapi_app,
            http_auth_level=func.AuthLevel.ANONYMOUS
        )

        logger.info("✅ AsgiFunctionApp configurado correctamente")
        return function_app

    except ImportError as e:
        logger.error(f"❌ Error importando FastAPI app: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ Error inesperado cargando FastAPI: {str(e)}")
        return None


# ===============================================
# MÉTODO 2: ENDPOINTS AZURE FUNCTIONS DIRECTOS
# ===============================================

def create_direct_function_app():
    """
    Crea Azure Functions directas como fallback si FastAPI no se puede cargar.
    """
    logger.info("🔄 Creando Azure Functions directas como fallback...")

    # Crear Function App básica
    function_app = func.FunctionApp()

    @function_app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS)
    def health_check(req: func.HttpRequest) -> func.HttpResponse:
        """Health check básico"""
        try:
            return func.HttpResponse(
                json.dumps({
                    "status": "healthy",
                    "service": "MiaSalud Integration API",
                    "mode": "Azure Functions Direct",
                    "timestamp": datetime.utcnow().isoformat()
                }),
                status_code=200,
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:
            logger.error(f"Error en health check: {str(e)}")
            return func.HttpResponse(
                json.dumps({"error": str(e)}),
                status_code=500,
                headers={"Content-Type": "application/json"}
            )

    @function_app.route(route="webhook/manychat/contact", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
    def manychat_contact_webhook(req: func.HttpRequest) -> func.HttpResponse:
        """Webhook directo para contactos ManyChat"""
        try:
            # Verificar API Key
            api_key = req.headers.get('X-API-KEY')
            expected_key = "Miasaludnatural123**"  # Desde tu .env

            if not api_key or api_key != expected_key:
                return func.HttpResponse(
                    json.dumps({"error": "API Key inválido o faltante"}),
                    status_code=401,
                    headers={"Content-Type": "application/json"}
                )

            # Obtener datos del request
            try:
                event_data = req.get_json()
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": "JSON inválido"}),
                    status_code=400,
                    headers={"Content-Type": "application/json"}
                )

            # Validar campos requeridos
            required_fields = ['manychat_id', 'nombre_lead', 'ultimo_estado']
            for field in required_fields:
                if not event_data.get(field):
                    return func.HttpResponse(
                        json.dumps({"error": f"Campo requerido faltante: {field}"}),
                        status_code=400,
                        headers={"Content-Type": "application/json"}
                    )

            # Log del evento recibido
            logger.info(f"📨 Evento ManyChat recibido: {event_data.get('manychat_id')}")

            # TODO: Aquí podrías agregar lógica para encolar el mensaje
            # Por ahora, solo respondemos exitosamente

            return func.HttpResponse(
                json.dumps({
                    "status": "accepted",
                    "message": "Evento recibido exitosamente",
                    "manychat_id": event_data.get('manychat_id'),
                    "mode": "direct_function"
                }),
                status_code=202,
                headers={"Content-Type": "application/json"}
            )

        except Exception as e:
            logger.error(f"Error procesando webhook ManyChat: {str(e)}")
            return func.HttpResponse(
                json.dumps({"error": "Error interno del servidor"}),
                status_code=500,
                headers={"Content-Type": "application/json"}
            )

    @function_app.route(route="docs", auth_level=func.AuthLevel.ANONYMOUS)
    def api_docs(req: func.HttpRequest) -> func.HttpResponse:
        """Documentación básica de la API"""
        docs_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>MiaSalud Integration API - Azure Functions</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .method { color: #007acc; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>🚀 MiaSalud Integration API</h1>
            <p>Ejecutándose en Azure Functions - Modo Direct</p>

            <h2>Endpoints Disponibles:</h2>

            <div class="endpoint">
                <span class="method">GET</span> <code>/api/health</code><br>
                <small>Health check básico del sistema</small>
            </div>

            <div class="endpoint">
                <span class="method">POST</span> <code>/api/webhook/manychat/contact</code><br>
                <small>Webhook para recibir eventos de contacto de ManyChat</small><br>
                <small><strong>Requiere:</strong> Header X-API-KEY</small>
            </div>

            <h2>Autenticación:</h2>
            <p>Todos los endpoints (excepto /health y /docs) requieren el header:</p>
            <code>X-API-KEY: Miasaludnatural123**</code>

            <h2>Estado del Sistema:</h2>
            <ul>
                <li>✅ Azure Functions: Activo</li>
                <li>🔄 FastAPI: Intentando cargar...</li>
                <li>🔄 Base de datos: Por verificar</li>
            </ul>
        </body>
        </html>
        """

        return func.HttpResponse(docs_html, mimetype="text/html")

    logger.info("✅ Azure Functions directas configuradas")
    return function_app


# ===============================================
# LÓGICA PRINCIPAL DE CREACIÓN DE LA APP
# ===============================================

logger.info("🚀 Iniciando MiaSalud Integration API en Azure Functions...")

# Intentar primero el método FastAPI
app = create_fastapi_function_app()

# Si falla, usar Azure Functions directas
if app is None:
    logger.warning("⚠️ FastAPI no disponible, usando Azure Functions directas")
    app = create_direct_function_app()

logger.info("✅ Aplicación configurada y lista")

# IMPORTANTE: La variable 'app' debe estar disponible a nivel módulo
# para que Azure Functions la pueda detectar