from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.core.logging import logger

# Obtener configuración
settings = get_settings()

# Configuración de metadatos para Swagger
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
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
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

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, cambiar a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(
    api_v1_router,
    prefix=settings.API_V1_STR
)


# Endpoint raíz
@app.get("/",
         summary="Endpoint raíz",
         description="Verifica que la API está funcionando correctamente",
         tags=["health"])
async def root():
    """
    Endpoint de verificación básica.

    Retorna un mensaje simple confirmando que la API está activa.
    """
    return {
        "message": "MiaSalud Integration API",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json"
    }


# Health check simple
@app.get("/health",
         summary="Health Check simple",
         description="Verifica que la API está respondiendo",
         tags=["health"])
async def health_check():
    """
    Health check simple para verificar que la API está activa.
    Para un health check detallado use /api/v1/reports/health
    """
    return {
        "status": "healthy",
        "service": "MiaSalud Integration API",
        "detailed_health": "/api/v1/reports/health"
    }


# Evento de inicio
@app.on_event("startup")
async def startup_event():
    """
    Ejecuta tareas de inicialización al arrancar la aplicación.
    """
    logger.info("🚀 Iniciando MiaSalud Integration API...")

    # Verificar conexión a base de datos
    try:
        from app.db.session import check_database_connection
        if check_database_connection():
            logger.info("✅ Conexión a base de datos establecida")
        else:
            logger.error("❌ No se pudo conectar a la base de datos")
    except Exception as e:
        logger.error(f"❌ Error al verificar base de datos: {str(e)}")

    # Verificar colas de Azure
    try:
        from app.services.queue_service import QueueService
        queue_service = QueueService()
        logger.info("✅ Colas de Azure Storage verificadas")
    except Exception as e:
        logger.error(f"❌ Error al verificar colas: {str(e)}")

    logger.info("✅ API iniciada exitosamente")


# Evento de cierre
@app.on_event("shutdown")
async def shutdown_event():
    """
    Ejecuta tareas de limpieza al cerrar la aplicación.
    """
    logger.info("👋 Cerrando MiaSalud Integration API...")


# Manejo de excepciones personalizado
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint no encontrado",
            "message": "El endpoint solicitado no existe en esta API",
            "docs": "/docs",
            "available_endpoints": {
                "docs": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json",
                "health": "/health",
                "api_health": "/api/v1/reports/health",
                "contact_webhook": "/api/v1/manychat/webhook/contact",
                "campaign_webhook": "/api/v1/manychat/webhook/campaign-assignment"
            }
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Error interno del servidor: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Error interno del servidor",
            "message": "Ha ocurrido un error inesperado. Por favor contacte al equipo de soporte."
        }
    )
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.core.logging import logger

# Obtener configuración
settings = get_settings()

# Configuración de metadatos para Swagger
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
    docs_url="/docs",   # Swagger UI
    redoc_url="/redoc",   # ReDoc
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

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # En producción, cambiar a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(
    api_v1_router,
    prefix=settings.API_V1_STR
)


# Endpoint raíz
@app.get("/",
          summary="Endpoint raíz",
          description="Verifica que la API está funcionando correctamente",
          tags=["health"])
async def root():
    """
    Endpoint de verificación básica.

    Retorna un mensaje simple confirmando que la API está activa.
    """
    return {
        "message": "MiaSalud Integration API",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json"
    }


# Health check simple
@app.get("/health",
          summary="Health Check simple",
          description="Verifica que la API está respondiendo",
          tags=["health"])
async def health_check():
    """
    Health check simple para verificar que la API está activa.
    Para un health check detallado use /api/v1/reports/health
    """
    return {
        "status": "healthy",
        "service": "MiaSalud Integration API",
        "detailed_health": "/api/v1/reports/health"
    }


@app.on_event("startup")
async def startup_event():
    """
    Ejecuta tareas de inicialización al arrancar la aplicación.
    """
    logger.info("🚀 Iniciando MiaSalud Integration API...")

    # Verificar conexión a base de datos
    try:
        from app.db.session import check_database_connection
        if check_database_connection():
            logger.info("✅ Conexión a base de datos establecida")
        else:
            logger.error("❌ No se pudo conectar a la base de datos")
    except Exception as e:
        logger.error(f"❌ Error al verificar base de datos: {str(e)}")

    # Verificar colas de Azure
    try:
        from app.services.queue_service import QueueService
        print(f"DEBUG_SETTINGS_OBJECT_RAW: {settings.model_dump()}")
        logger.info(f"Cadena de conexión de Azure Storage (desde settings - logger): {settings.AZURE_STORAGE_CONNECTION_STRING}")
        print(f"DEBUG_CONNECTION_STRING_RAW: {settings.AZURE_STORAGE_CONNECTION_STRING}")
        queue_service = QueueService()
        logger.info("✅ Colas de Azure Storage verificadas")
    except Exception as e:
        logger.error(f"❌ Error al verificar colas: {str(e)}")

    logger.info("✅ API iniciada exitosamente")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Ejecuta tareas de limpieza al cerrar la aplicación.
    """
    logger.info("👋 Cerrando MiaSalud Integration API...")


# Manejo de excepciones personalizado
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint no encontrado",
            "message": "El endpoint solicitado no existe en esta API",
            "docs": "/docs",
            "available_endpoints": {
                "docs": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json",
                "health": "/health",
                "api_health": "/api/v1/reports/health",
                "contact_webhook": "/api/v1/manychat/webhook/contact",
                "campaign_webhook": "/api/v1/manychat/webhook/campaign-assignment"
            }
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Error interno del servidor: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Error interno del servidor",
            "message": "Ha ocurrido un error inesperado. Por favor contacte al equipo de soporte."
        }
    )
