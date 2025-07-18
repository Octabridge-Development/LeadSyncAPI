# tests/test_crm_integration.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Asegúrate de que la app se pueda importar. 
# Esto podría requerir ajustar el PYTHONPATH.
# from app.main import app 

# Como no tenemos la app real, la definimos de forma ficticia para el ejemplo.
# En tu proyecto real, importa tu 'app' de FastAPI desde app.main
from fastapi import FastAPI
app = FastAPI() 

# --- Mock del endpoint para poder probarlo ---
# Esto es necesario porque no podemos ejecutar el servidor real durante las pruebas.
# En tu código real, importa el router y la app. Aquí lo simulamos.
from app.api.v1.endpoints.crm import router as crm_router
app.include_router(crm_router, prefix="/api/v1")
# --- Fin del Mock ---

client = TestClient(app)

# Clave API para las pruebas
API_KEY = "Miasaludnatural123**"
HEADERS = {"X-API-KEY": API_KEY, "Content-Type": "application/json"}

# --- Casos de Prueba Críticos ---

# Escenario 1: Creación de un lead nuevo
def test_creacion_lead_nuevo():
    """
    Test de creación de un lead nuevo.
    Verifica que el endpoint encola un evento para un nuevo cliente.
    """
    payload = {
        "manychat_id": "nuevo_cliente_123",
        "first_name": "Juan",
        "last_name": "Perez",
        "entry_date": "2025-07-07T10:00:00Z",
        # Validación de estado de oportunidad, sin lógica de Odoo/contactos Odoo
    }
    
    # Usamos 'patch' para simular que el servicio de colas funciona sin ejecutarlo realmente
    with patch("app.services.queue_service.queue_service.send_message") as mock_send_message:
        response = client.post("/api/v1/crm/webhook/lead", headers=HEADERS, json=payload)
        
        # 1. Verificar que la API respondió correctamente
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "enqueued"
        assert json_response["manychat_id"] == "nuevo_cliente_123"
        
        # 2. Verificar que la tarea de encolado fue llamada
        mock_send_message.assert_called_once()

# Escenario 2: Actualización de lead (simulado)
def test_actualizacion_lead_existente():
    """
    Test para un lead existente.
    La lógica real ocurre en el worker, pero probamos que el endpoint lo encola correctamente.
    """
    payload = {
        "manychat_id": "cliente_existente_456",
        "first_name": "Ana",
        "entry_date": "2025-07-08T11:00:00Z",
        "state": {"sequence": 3, "summary": "Cliente interesado en plan anual", "date": "2025-07-08T11:05:00Z"}
    }
    
    with patch("app.services.queue_service.queue_service.send_message") as mock_send_message:
        response = client.post("/api/v1/crm/webhook/lead", headers=HEADERS, json=payload)
        
        assert response.status_code == 200
        assert response.json()["status"] == "enqueued"
        mock_send_message.assert_called_once()

# Escenario 3: Test de validación de secuencia (fuera de rango)
def test_validacion_de_sequence_invalida():
    """
    Test de validación de 'sequence'.
    Verifica que la API rechace un valor de secuencia fuera del rango 0-10.
    """
    payload = {
        "manychat_id": "test_seq_789",
        "first_name": "Test",
        "entry_date": "2025-07-08T12:00:00Z",
        "state": {"sequence": 11, "summary": "Secuencia invalida", "date": "2025-07-08T12:01:00Z"}
    }
    
    response = client.post("/api/v1/crm/webhook/lead", headers=HEADERS, json=payload)
    
    # Pydantic debe devolver un error 422 (Unprocessable Entity)
    assert response.status_code == 422

# Escenario 4: Test de autenticación
def test_autenticacion_api_key_invalida():
    """
    Test de autenticación con una API Key incorrecta.
    Verifica que el endpoint esté protegido.
    """
    payload = {"manychat_id": "test_auth_000"} # Payload mínimo
    invalid_headers = {"X-API-KEY": "ESTA-LLAVE-ES-INCORRECTA", "Content-Type": "application/json"}
    
    response = client.post("/api/v1/crm/webhook/lead", headers=invalid_headers, json=payload)
    
    # El endpoint debe devolver un error 401 (Unauthorized)
    assert response.status_code == 401