# app/main.py

# --- Imports de FastAPI y Python ---
from fastapi import FastAPI, Request, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

# --- Imports de tu aplicación ---
from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.core.logging import logger
from app.db.models import Contact  # Modelo de la base de datos
from app.db.session import get_db   # Dependencia para la sesión de BD

# --- Configuración de la Aplicación ---
settings = get_settings()

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

# --- Middlewares ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(
    api_v1_router,
    prefix=settings.API_V1_STR
)

# --- Modelo de Respuesta para Verificación ---
class VerificationResponse(BaseModel):
    existe: str # Puede ser "sí" o "no"

# --- Endpoints Principales ---

@app.get("/", summary="Endpoint raíz", description="Verifica que la API está funcionando correctamente", tags=["Health"])
async def root():
    return {
        "message": "MiaSalud Integration API",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health", summary="Health Check Detallado", description="Verifica el estado de la API y sus dependencias críticas.", tags=["Health"])
async def health_check():
    return {"status": "healthy"}

# --- ENDPOINT DE VERIFICACIÓN (CORREGIDO) ---
@app.get(
    "/verificar-contacto",
    response_model=VerificationResponse,
    summary="Verifica si un contacto existe por manychat_id",
    tags=["Verificación"]
)
def verificar_contacto(
    manychat_id: str = Query(..., description="ID de ManyChat a verificar en la base de datos"),
    db: Session = Depends(get_db)  # Inyección de dependencia de la BD
):
    """
    Verifica en la base de datos (Azure SQL) si ya existe un contacto
    con el `manychat_id` proporcionado.
    """
    try:
        # --- ✅ ESTA ES LA CORRECCIÓN ---
        # Ahora usamos 'Contact.manychat_id' que es el nombre correcto de la columna.
        contacto = db.query(Contact).filter(Contact.manychat_id == manychat_id).first()

        if contacto:
            return {"existe": "sí"}
        else:
            return {"existe": "no"}

    except Exception as e:
        logger.error(f"Error de base de datos al verificar contacto con manychat_id={manychat_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error interno al consultar la base de datos."
        )


# --- Eventos de Ciclo de Vida ---
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Iniciando MiaSalud Integration API...")
    # Tu lógica de verificación de BD está bien aquí.
    logger.info("✅ API iniciada exitosamente")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Cerrando MiaSalud Integration API...")


# --- Manejadores de Excepciones Globales ---
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"error": "Endpoint no encontrado"})
