import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db.models import Contact, CampaignContact
from app.main import app
from datetime import datetime
from uuid import uuid4

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def db_session():
    # Aquí deberías usar tu fixture real de sesión de base de datos
    # o un mock si usas una base de datos de test
    from app.db.session import get_db
    db = next(get_db())
    yield db
    db.close()

@pytest.fixture
def create_test_contact(db_session):
    def _create(manychat_id=None, **kwargs):
        if manychat_id is None:
            manychat_id = f"test_{uuid4()}"
        contact = Contact(manychat_id=manychat_id, first_name="Test", **kwargs)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        return contact
    return _create

@pytest.fixture
def create_test_campaign(db_session):
    def _create(name=None, date_start=None, **kwargs):
        from app.db.models import Campaign
        if name is None:
            name = f"Test Campaign {uuid4()}"
        if date_start is None:
            date_start = datetime.utcnow()
        campaign = Campaign(name=name, date_start=date_start, **kwargs)
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)
        return campaign
    return _create

@pytest.fixture
def create_test_campaign_contact(db_session, create_test_campaign):
    def _create(contact_id, campaign_id=None, **kwargs):
        if campaign_id is None:
            campaign = create_test_campaign()
            campaign_id = campaign.id
        cc = CampaignContact(contact_id=contact_id, campaign_id=campaign_id, registration_date=datetime.utcnow(), **kwargs)
        db_session.add(cc)
        db_session.commit()
        db_session.refresh(cc)
        return cc
    return _create

def test_get_campaign_contacts_by_manychat_id(client, db_session, create_test_contact, create_test_campaign_contact):
    manychat_id = f"mcid_get_{uuid4()}"
    contact = create_test_contact(manychat_id=manychat_id)
    cc1 = create_test_campaign_contact(contact_id=contact.id, last_state="A")
    cc2 = create_test_campaign_contact(contact_id=contact.id, last_state="B")
    response = client.get(f"/api/v1/campaign-contacts/by-manychat/{contact.manychat_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(cc["last_state"] == "A" for cc in data)
    assert any(cc["last_state"] == "B" for cc in data)

def test_put_campaign_contacts_by_manychat_id(client, db_session, create_test_contact, create_test_campaign_contact):
    manychat_id = f"mcid_put_{uuid4()}"
    contact = create_test_contact(manychat_id=manychat_id)
    cc = create_test_campaign_contact(contact_id=contact.id, last_state="Old")
    update_data = {"last_state": "Updated"}
    response = client.put(f"/api/v1/campaign-contacts/by-manychat/{contact.manychat_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert any(c["last_state"] == "Updated" for c in data)
    # Verifica en la base de datos
    db_session.expire_all()
    cc_db = db_session.query(CampaignContact).filter_by(id=cc.id).first()
    assert cc_db.last_state == "Updated"

def test_get_campaign_contacts_by_manychat_id_not_found(client):
    response = client.get("/api/v1/campaign-contacts/by-manychat/noexiste")
    assert response.status_code == 404

def test_put_campaign_contacts_by_manychat_id_not_found(client):
    response = client.put("/api/v1/campaign-contacts/by-manychat/noexiste", json={"last_state": "X"})
    assert response.status_code == 404
