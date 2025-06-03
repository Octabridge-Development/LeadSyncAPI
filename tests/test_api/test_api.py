import pytest
from fastapi import status
from app.core.config import get_settings

settings = get_settings()

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert "message" in response.json()

def test_documentation_endpoints(client):
    docs_endpoints = ["/docs", "/redoc", "/openapi.json"]
    for endpoint in docs_endpoints:
        response = client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data

def test_detailed_health_check(client):
    headers = {"X-API-KEY": settings.API_KEY}
    response = client.get("/api/v1/reports/health", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert "dependencies" in data
    assert "database" in data["dependencies"]
    assert "queues" in data["dependencies"]