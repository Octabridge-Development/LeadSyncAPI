# function_app.py - VERSIÓN SIMPLE PARA AZURE FUNCTIONS
import azure.functions as func
import logging
import json
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear la Function App
app = func.FunctionApp()


@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check básico"""
    logger.info("Health check solicitado")

    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "service": "MiaSalud Integration API",
            "timestamp": datetime.utcnow().isoformat(),
            "python_version": "3.10.17",
            "azure_functions": "OK"
        }),
        status_code=200,
        headers={"Content-Type": "application/json"}
    )


@app.route(route="webhook/manychat/contact", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def manychat_contact_webhook(req: func.HttpRequest) -> func.HttpResponse:
    """Webhook para contactos ManyChat"""
    try:
        logger.info("Webhook ManyChat recibido")

        # Verificar API Key
        api_key = req.headers.get('X-API-KEY')
        expected_key = "Miasaludnatural123**"

        if not api_key or api_key != expected_key:
            logger.warning("API Key inválido")
            return func.HttpResponse(
                json.dumps({"error": "API Key inválido o faltante"}),
                status_code=401,
                headers={"Content-Type": "application/json"}
            )

        # Obtener datos del request
        try:
            event_data = req.get_json()
            logger.info(f"Datos recibidos: {event_data}")
        except ValueError as e:
            logger.error(f"JSON inválido: {str(e)}")
            return func.HttpResponse(
                json.dumps({"error": "JSON inválido"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )

        # Validar campos requeridos
        required_fields = ['manychat_id', 'nombre_lead', 'ultimo_estado']
        for field in required_fields:
            if not event_data.get(field):
                logger.error(f"Campo faltante: {field}")
                return func.HttpResponse(
                    json.dumps({"error": f"Campo requerido faltante: {field}"}),
                    status_code=400,
                    headers={"Content-Type": "application/json"}
                )

        # Procesar evento
        manychat_id = event_data.get('manychat_id')
        nombre = event_data.get('nombre_lead')
        estado = event_data.get('ultimo_estado')

        logger.info(f"Procesando evento - ID: {manychat_id}, Nombre: {nombre}, Estado: {estado}")

        # TODO: Aquí irá la lógica de procesamiento (colas, base de datos, etc.)

        # Respuesta exitosa
        response_data = {
            "status": "accepted",
            "message": "Evento recibido y procesado exitosamente",
            "manychat_id": manychat_id,
            "processed_at": datetime.utcnow().isoformat()
        }

        logger.info(f"Evento procesado exitosamente: {manychat_id}")

        return func.HttpResponse(
            json.dumps(response_data),
            status_code=202,
            headers={"Content-Type": "application/json"}
        )

    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Error interno del servidor"}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


@app.route(route="docs", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def api_docs(req: func.HttpRequest) -> func.HttpResponse:
    """Documentación de la API"""
    docs_html = """
<!DOCTYPE html>
<html>
<head>
    <title>MiaSalud Integration API</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .endpoint { background: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #007acc; }
        .method { color: #007acc; font-weight: bold; font-size: 14px; }
        .url { font-family: monospace; background: #e9ecef; padding: 2px 6px; border-radius: 3px; }
        .status { padding: 4px 8px; border-radius: 12px; font-size: 12px; }
        .success { background: #d4edda; color: #155724; }
        .warning { background: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 MiaSalud Integration API</h1>
        <p>API para integración entre ManyChat, Odoo y Azure SQL</p>

        <div class="status success">✅ Azure Functions: Activo</div>
        <div class="status warning">🔄 FastAPI: En desarrollo</div>

        <h2>📋 Endpoints Disponibles</h2>

        <div class="endpoint">
            <span class="method">GET</span> <span class="url">/api/health</span><br>
            <small><strong>Descripción:</strong> Verifica el estado del sistema</small><br>
            <small><strong>Autenticación:</strong> No requerida</small>
        </div>

        <div class="endpoint">
            <span class="method">POST</span> <span class="url">/api/webhook/manychat/contact</span><br>
            <small><strong>Descripción:</strong> Recibe eventos de contacto desde ManyChat</small><br>
            <small><strong>Autenticación:</strong> Header X-API-KEY requerido</small><br>
            <small><strong>Content-Type:</strong> application/json</small>
        </div>

        <div class="endpoint">
            <span class="method">GET</span> <span class="url">/api/docs</span><br>
            <small><strong>Descripción:</strong> Esta documentación</small><br>
            <small><strong>Autenticación:</strong> No requerida</small>
        </div>

        <h2>🔐 Autenticación</h2>
        <p>Para endpoints protegidos, incluye el header:</p>
        <div class="url">X-API-KEY: Miasaludnatural123**</div>

        <h2>📖 Ejemplo de uso</h2>
        <pre style="background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto;">
    curl -X POST https://tu-function-app.azurewebsites.net/api/webhook/manychat/contact \\
  -H "Content-Type: application/json" \\
  -H "X-API-KEY: Miasaludnatural123**" \\
  -d '{
    "manychat_id": "123456789",
    "nombre_lead": "Juan Pérez",
    "ultimo_estado": "Nuevo Lead"
  }'
        </pre>

        <hr style="margin: 30px 0;">
        <small>MiaSalud Integration API v1.0 - Powered by Azure Functions</small>
    </div>
</body>
</html>
    """

    return func.HttpResponse(docs_html, mimetype="text/html")


# Log de inicialización
logger.info("🚀 MiaSalud Integration API inicializada correctamente")