# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# --- INICIO DE LA CORRECCIÓN CLAVE ---
# Se importa el archivo 'base' para que SQLAlchemy conozca todos los modelos.
# Esto soluciona el error de "Table 'Address' is already defined".
from app.db import base
# --- FIN DE LA CORRECCIÓN CLAVE ---

from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.core.logging import logger

# Obtener configuración
settings = get_settings()

# Configuración de metadatos para Swagger (Tu código original)
app = FastAPI(
    title="MiaSalud Integration API",
    description="""
    ## 🚀 API de Integración MiaSalud

    Esta API permite la integración entre ManyChat, Odoo 18 y Azure SQL para el manejo de leads y campañas de marketing.

    ### Características principales:

    * **Webhook de Contactos**: Recibe y procesa información de nuevos contactos desde ManyChat
    * **Webhook de Campañas**: Gestiona asignaciones de campañas y asesores comerciales
    * **Procesamiento Asíncrono**: Usa colas de Azure Storage para procesamiento resiliente
    * **Rate Limiting**: Respeta los límites de API de Odoo (1 req/s)
    * **Idempotencia**: Previene duplicación de datos

    ### Flujos principales:

    1. **Nuevo Contacto**: ManyChat → API → Cola → Worker → Azure SQL + Odoo
    2. **Asignación de Campaña**: ManyChat → API → Cola → Worker → Azure SQL + Odoo

    ### Autenticación:

    Todos los endpoints requieren un header `X-API-KEY` con el valor configurado en las variables de entorno.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Equipo de Desarrollo MiaSalud",
        "email": "sistemas@miasaludnatural.com",
    },
    license_info={
        "name": "Propietario",
        "url": "https://miasaludnatural.com",
    },
)

# Configuración de CORS (Tu código original)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers (Tu código original)
app.include_router(
    api_v1_router,
    prefix=settings.API_V1_STR
)

# Endpoint raíz (Tu código original)
@app.get("/", summary="Endpoint raíz", description="Verifica que la API está funcionando correctamente", tags=["health"])
async def root():
    return {
        "message": "MiaSalud Integration API",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json"
    }

# Health Check completo (Tu código original)
@app.get("/health", summary="Health Check Detallado", description="Verifica el estado de la API y sus dependencias críticas.", tags=["health"])
async def health_check():
    async def check_database_connection():
        return "ok"
    
    async def check_azure_storage():
        return "ok"

    async def check_key_vault():
        return "ok"

    return {
        "status": "healthy",
        "environment": "azure-app-service",
        "dependencies": {
            "database": await check_database_connection(),
            "azure_storage": await check_azure_storage(),
            "key_vault": await check_key_vault()
        }
    }

# Eventos de inicio y cierre (Tu código original)
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Iniciando MiaSalud Integration API...")
    try:
        from app.db.session import check_database_connection
        if check_database_connection():
            logger.info("✅ Conexión a base de datos establecida")
        else:
            logger.error("❌ No se pudo conectar a la base de datos")
    except Exception as e:
        logger.error(f"❌ Error al verificar base de datos: {str(e)}")
    # ... (resto de tu lógica de startup)
    logger.info("✅ API iniciada exitosamente")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Cerrando MiaSalud Integration API...")

# Manejo de excepciones (Tu código original)
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"error": "Endpoint no encontrado"})

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Error interno del servidor: {str(exc)}")
    return JSONResponse(status_code=500, content={"error": "Error interno del servidor"})