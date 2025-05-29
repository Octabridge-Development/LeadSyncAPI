import logging
import azure.functions as func
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Crear la aplicación FastAPI
app = FastAPI(
    title="MiaSalud Integration API",
    description="API de integración ManyChat-Odoo-Azure SQL",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {
        "message": "MiaSalud Integration API",
        "status": "active",
        "version": "1.0.0",
        "environment": "Azure Functions"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "MiaSalud Integration API"}

@app.post("/api/v1/manychat/webhook/contact")
async def manychat_webhook(request_data: dict):
    """Webhook básico para ManyChat - versión simplificada"""
    logging.info(f"Webhook recibido: {request_data}")
    return {
        "status": "received",
        "message": "Evento procesado correctamente",
        "timestamp": "2025-05-29"
    }

# Crear la Azure Function App
azure_app = func.AsgiFunctionApp(app=app, http_auth_level=func.AuthLevel.ANONYMOUS)

logging.info("✅ MiaSalud Integration API inicializada correctamente")