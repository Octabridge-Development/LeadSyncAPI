import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import Channel
from sqlalchemy.orm import Session

def get_test_client():
    return TestClient(app)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def db_session():
    from app.db.session import get_db
    db = next(get_db())
    yield db
    db.close()

def test_create_channel(client, db_session):
    data = {"name": "WhatsApp", "description": "Canal de WhatsApp"}
    response = client.post("/api/v1/channels/", json=data)
    assert response.status_code == 201
    result = response.json()
    assert result["name"] == data["name"]
    assert result["description"] == data["description"]
    # Verifica en la base de datos
    db_obj = db_session.query(Channel).filter_by(id=result["id"]).first()
    assert db_obj is not None

def test_list_channels(client, db_session):
    # Crea un canal para asegurar que la lista no esté vacía
    db_session.add(Channel(name="Telegram", description="Canal Telegram"))
    db_session.commit()
    response = client.get("/api/v1/channels/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(c["name"] == "Telegram" for c in data)

def test_get_channel(client, db_session):
    channel = Channel(name="Facebook", description="Canal Facebook")
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    response = client.get(f"/api/v1/channels/{channel.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Facebook"

def test_update_channel(client, db_session):
    channel = Channel(name="Instagram", description="Canal Instagram")
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    update = {"name": "Instagram Updated", "description": "Nuevo Desc"}
    response = client.put(f"/api/v1/channels/{channel.id}", json=update)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update["name"]
    assert data["description"] == update["description"]

def test_delete_channel(client, db_session):
    channel = Channel(name="ToDelete", description="Borrar")
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    response = client.delete(f"/api/v1/channels/{channel.id}")
    assert response.status_code == 204
    # Verifica que ya no existe
    db_obj = db_session.query(Channel).filter_by(id=channel.id).first()
    assert db_obj is None
