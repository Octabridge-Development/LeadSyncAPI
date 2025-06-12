import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db.models import Contact, CampaignContact, Advisor, Campaign # Asegúrate de importar Campaign aquí
from datetime import datetime, timezone, timedelta

# Asume que `client`, `db_session`, `create_test_contact`,
# `create_test_campaign_contact`, `create_test_advisor`, `create_test_campaign`
# están definidos en `conftest.py` y disponibles aquí.

# Endpoint bajo prueba (ajústalo si la ruta real es diferente)
# VERIFICA TU manychat.py para la ruta exacta del endpoint PUT
ENDPOINT_URL = "/api/v1/manychat/campaign-contacts/update-by-manychat-id" # <<-- REVISA ESTA RUTA

# --- Test Suite 1: Funcionalidad Básica ---

def test_successful_update(client: TestClient, db_session: Session, create_test_contact, create_test_campaign, create_test_campaign_contact, create_test_advisor):
    """
    Verifica una actualización exitosa de CampaignContact con todos los campos.
    """
    # Preparar datos de prueba en la base real
    contact = create_test_contact(manychat_id="manychat_id_existente_1", first_name="Juan")
    campaign = create_test_campaign(id=1, name="Campaña Verano", date_start=datetime.now(timezone.utc))
    advisor = create_test_advisor(id=101, name="Dr. Smith", odoo_id="advisor_101")
    campaign_contact = create_test_campaign_contact(
        contact_id=contact.id,
        campaign_id=campaign.id,
        registration_date=datetime.now(timezone.utc) - timedelta(days=5),
        last_state="Initial State"
    )

    update_data = {
        "manychat_id": contact.manychat_id,
        "campaign_id": campaign_contact.campaign_id,  # Ya es int
        "medical_advisor_id": advisor.id,
        "medical_assignment_date": datetime.now(timezone.utc).isoformat(),
        "last_state": "Assigned to Doctor"
    }

    response = client.put(ENDPOINT_URL, json=update_data)
    assert response.status_code == 200
    updated_cc = response.json()

    db_session.expire_all()  # Ensure session sees latest DB state

    # Verificar que los datos se actualizaron en la DB
    db_campaign_contact = db_session.query(CampaignContact).filter_by(id=campaign_contact.id).first()
    assert db_campaign_contact.medical_advisor_id == advisor.id
    assert db_campaign_contact.last_state == "Assigned to Doctor"
    # Para datetime, comparar solo la parte de la fecha o con un margen de tolerancia
    assert db_campaign_contact.medical_assignment_date.date() == datetime.now(timezone.utc).date()
    assert updated_cc["medical_advisor_id"] == advisor.id
    assert updated_cc["last_state"] == "Assigned to Doctor"


def test_contact_not_found(client: TestClient):
    """
    Verifica que el endpoint maneja correctamente un manychat_id inexistente.
    """
    update_data = {
        "manychat_id": "manychat_id_inexistente",
        "last_state": "Estado de prueba"
    }
    response = client.put(ENDPOINT_URL, json=update_data)
    assert response.status_code == 400 # O 404, dependiendo de cómo manejes el ValueError en tu endpoint API
    assert "El contacto (manychat_id='manychat_id_inexistente') no existe." in response.json()["detail"]


def test_advisor_not_found(client: TestClient, db_session: Session, create_test_contact, create_test_campaign, create_test_campaign_contact):
    """
    Confirma que se maneja un medical_advisor_id inválido.
    """
    contact = create_test_contact(manychat_id="manychat_id_existente_2", first_name="Pedro")
    campaign = create_test_campaign(id=2, name="Campaña Invierno", date_start=datetime.now(timezone.utc))
    campaign_contact = create_test_campaign_contact(
        contact_id=contact.id,
        campaign_id=campaign.id,
        registration_date=datetime.now(timezone.utc) - timedelta(days=2),
        last_state="Pending"
    )
    non_existent_advisor_id = 99999

    update_data = {
        "manychat_id": contact.manychat_id,
        "campaign_id": campaign_contact.campaign_id,
        "medical_advisor_id": non_existent_advisor_id,
        "last_state": "Updated"
    }
    response = client.put(ENDPOINT_URL, json=update_data)
    assert response.status_code == 400
    assert f"El ID de Asesor Médico {non_existent_advisor_id} no es válido." in response.json()["detail"]


def test_multiple_campaigns_without_campaign_id_updates_most_recent(
    client: TestClient, db_session: Session, create_test_contact, create_test_campaign, create_test_campaign_contact, create_test_advisor
):
    """
    Verifica que si un contacto tiene múltiples Campaign_Contact y no se especifica campaign_id,
    se actualice el más reciente.
    """
    contact = create_test_contact(manychat_id="manychat_id_multi_campaign", first_name="Ana")
    advisor = create_test_advisor(id=202, name="Dr. House", odoo_id="advisor_202")

    # Crear campañas
    campaign_old = create_test_campaign(id=10, name="Campaña Antigua", date_start=datetime.now(timezone.utc) - timedelta(days=10))
    campaign_recent = create_test_campaign(id=11, name="Campaña Reciente", date_start=datetime.now(timezone.utc) - timedelta(days=1))


    # Crear una campaña antigua
    old_campaign_contact = create_test_campaign_contact(
        contact_id=contact.id,
        campaign_id=campaign_old.id,
        registration_date=datetime.now(timezone.utc) - timedelta(days=10),
        last_state="Old State"
    )

    # Crear una campaña reciente
    recent_campaign_contact = create_test_campaign_contact(
        contact_id=contact.id,
        campaign_id=campaign_recent.id,
        registration_date=datetime.now(timezone.utc) - timedelta(days=1), # Esta es la más reciente
        last_state="Recent State"
    )

    update_data = {
        "manychat_id": contact.manychat_id,
        # No se especifica campaign_id, por lo que debería actualizar el más reciente por registration_date
        "medical_advisor_id": advisor.id,
        "last_state": "Updated Most Recent"
    }

    response = client.put(ENDPOINT_URL, json=update_data)
    assert response.status_code == 200

    db_session.expire_all()  # Ensure session sees latest DB state

    # Verificar que la campaña más reciente fue actualizada
    db_recent_cc = db_session.query(CampaignContact).filter_by(id=recent_campaign_contact.id).first()
    assert db_recent_cc.medical_advisor_id == advisor.id
    assert db_recent_cc.last_state == "Updated Most Recent"

    # Verificar que la campaña antigua NO fue actualizada
    db_old_cc = db_session.query(CampaignContact).filter_by(id=old_campaign_contact.id).first()
    assert db_old_cc.medical_advisor_id is None # O su valor original
    assert db_old_cc.last_state == "Old State" # O su valor original

def test_specific_campaign_update(
    client: TestClient, db_session: Session, create_test_contact, create_test_campaign, create_test_campaign_contact, create_test_advisor
):
    """
    Asegura que la actualización funciona correctamente cuando se especifica un campaign_id.
    """
    contact = create_test_contact(manychat_id="manychat_id_specific_campaign", first_name="Carlos")
    advisor = create_test_advisor(id=303, name="Dr. Strange", odoo_id="advisor_303")

    # Crear varias campañas
    campaign_20 = create_test_campaign(id=20, name="Campaña X", date_start=datetime.now(timezone.utc) - timedelta(days=10))
    campaign_21 = create_test_campaign(id=21, name="Campaña Y", date_start=datetime.now(timezone.utc) - timedelta(days=5))
    campaign_22 = create_test_campaign(id=22, name="Campaña Z", date_start=datetime.now(timezone.utc) - timedelta(days=1))

    campaign_contact_1 = create_test_campaign_contact(
        contact_id=contact.id,
        campaign_id=campaign_20.id,
        registration_date=datetime.now(timezone.utc) - timedelta(days=10),
        last_state="State C20"
    )
    campaign_contact_2 = create_test_campaign_contact(
        contact_id=contact.id,
        campaign_id=campaign_21.id, # Esta es la que queremos actualizar
        registration_date=datetime.now(timezone.utc) - timedelta(days=5),
        last_state="State C21"
    )
    campaign_contact_3 = create_test_campaign_contact(
        contact_id=contact.id,
        campaign_id=campaign_22.id,
        registration_date=datetime.now(timezone.utc) - timedelta(days=1),
        last_state="State C22"
    )

    update_data = {
        "manychat_id": contact.manychat_id,
        "campaign_id": campaign_21.id, # Especificamos el ID de campaña
        "medical_advisor_id": advisor.id,
        "last_state": "Updated for Campaign 21"
    }

    response = client.put(ENDPOINT_URL, json=update_data)
    assert response.status_code == 200

    db_session.expire_all()  # Ensure session sees latest DB state

    # Verificar que SOLO la campaña 21 fue actualizada
    db_cc_21 = db_session.query(CampaignContact).filter_by(id=campaign_contact_2.id).first()
    assert db_cc_21.medical_advisor_id == advisor.id
    assert db_cc_21.last_state == "Updated for Campaign 21"

    # Verificar que las otras campañas NO fueron actualizadas
    db_cc_20 = db_session.query(CampaignContact).filter_by(id=campaign_contact_1.id).first()
    assert db_cc_20.medical_advisor_id is None # O su valor original
    assert db_cc_20.last_state == "State C20"

    db_cc_22 = db_session.query(CampaignContact).filter_by(id=campaign_contact_3.id).first()
    assert db_cc_22.medical_advisor_id is None # O su valor original
    assert db_cc_22.last_state == "State C22"


# --- Test Suite 2: Edge Cases ---

def test_no_campaign_contact_exists(client: TestClient, db_session: Session, create_test_contact):
    """
    Confirma el comportamiento cuando el contacto existe pero no tiene un Campaign_Contact asociado.
    """
    contact = create_test_contact(manychat_id="manychat_no_campaign_contact", first_name="Daniel")

    update_data = {
        "manychat_id": contact.manychat_id,
        "last_state": "Should Fail"
    }
    response = client.put(ENDPOINT_URL, json=update_data)
    assert response.status_code == 400
    assert f"El contacto (manychat_id='{contact.manychat_id}') no tiene asignaciones de campaña activas." in response.json()["detail"]


def test_partial_update(client: TestClient, db_session: Session, create_test_contact, create_test_campaign, create_test_campaign_contact, create_test_advisor):
    """
    Verifica que se pueden actualizar solo algunos campos sin afectar los demás.
    """
    contact = create_test_contact(manychat_id="manychat_partial_update", first_name="Elena")
    campaign = create_test_campaign(id=30, name="Campaña Parcial", date_start=datetime.now(timezone.utc))
    initial_date = datetime.now(timezone.utc) - timedelta(days=30)
    campaign_contact = create_test_campaign_contact(
        contact_id=contact.id,
        campaign_id=campaign.id,
        registration_date=datetime.now(timezone.utc) - timedelta(days=20),
        medical_assignment_date=initial_date,
        last_state="Original State"
    )

    # Actualizar solo last_state
    update_data_1 = {
        "manychat_id": contact.manychat_id,
        "campaign_id": campaign_contact.campaign_id,
        "last_state": "New State"
    }
    response_1 = client.put(ENDPOINT_URL, json=update_data_1)
    assert response_1.status_code == 200
    db_session.expire_all()  # Ensure session sees latest DB state
    db_cc_1 = db_session.query(CampaignContact).filter_by(id=campaign_contact.id).first()
    assert db_cc_1.last_state == "New State"
    assert db_cc_1.medical_advisor_id is None # No debe haber cambiado
    # Compare only date part to avoid microsecond/tzinfo issues
    assert db_cc_1.medical_assignment_date.date() == initial_date.date() if db_cc_1.medical_assignment_date and initial_date else db_cc_1.medical_assignment_date == initial_date

    # Actualizar solo medical_advisor_id (last_state ya está actualizado)
    advisor = create_test_advisor(id=404, name="Dr. Who", odoo_id="advisor_404")
    update_data_2 = {
        "manychat_id": contact.manychat_id,
        "campaign_id": campaign_contact.campaign_id,
        "medical_advisor_id": advisor.id
    }
    response_2 = client.put(ENDPOINT_URL, json=update_data_2)
    assert response_2.status_code == 200
    db_session.expire_all()  # Ensure session sees latest DB state
    db_cc_2 = db_session.query(CampaignContact).filter_by(id=campaign_contact.id).first()
    assert db_cc_2.last_state == "New State" # Debe seguir siendo el mismo
    assert db_cc_2.medical_advisor_id == advisor.id
    # Compare only date part to avoid microsecond/tzinfo issues
    assert db_cc_2.medical_assignment_date.date() == initial_date.date() if db_cc_2.medical_assignment_date and initial_date else db_cc_2.medical_assignment_date == initial_date


def test_idempotency(client: TestClient, db_session: Session, create_test_contact, create_test_campaign, create_test_campaign_contact, create_test_advisor):
    """
    Asegura que múltiples llamadas con los mismos datos no cambian el resultado después de la primera actualización exitosa.
    """
    contact = create_test_contact(manychat_id="manychat_idempotency", first_name="Felipe")
    campaign = create_test_campaign(id=40, name="Campaña Idempotente", date_start=datetime.now(timezone.utc))
    advisor = create_test_advisor(id=505, name="Dr. Octopus", odoo_id="advisor_505")
    campaign_contact = create_test_campaign_contact(
        contact_id=contact.id,
        campaign_id=campaign.id,
        registration_date=datetime.now(timezone.utc) - timedelta(days=1),
        last_state="Initial State"
    )
    initial_assignment_date = campaign_contact.medical_assignment_date # Capturar la fecha inicial si se generó

    update_data = {
        "manychat_id": contact.manychat_id,
        "campaign_id": campaign_contact.campaign_id,
        "medical_advisor_id": advisor.id,
        "last_state": "Final State"
    }

    # Primera actualización
    response_1 = client.put(ENDPOINT_URL, json=update_data)
    assert response_1.status_code == 200
    db_session.expire_all()  # Ensure session sees latest DB state

    # Segunda actualización con los mismos datos
    response_2 = client.put(ENDPOINT_URL, json=update_data)
    assert response_2.status_code == 200 # Debe seguir siendo 200 OK
    db_session.expire_all()  # Ensure session sees latest DB state
    db_campaign_contact_after_2nd_call = db_session.query(CampaignContact).filter_by(id=campaign_contact.id).first()
    assert db_campaign_contact_after_2nd_call.medical_advisor_id == advisor.id
    assert db_campaign_contact_after_2nd_call.last_state == "Final State"
    # Only check medical_assignment_date if it was set in update_data
    if update_data.get("medical_assignment_date"):
        assert db_campaign_contact_after_2nd_call.medical_assignment_date is not None
        # Compare only date part to avoid microsecond/tzinfo issues
        assert db_campaign_contact_after_2nd_call.medical_assignment_date.date() == datetime.now(timezone.utc).date()
    else:
        # If not set, it should remain None
        assert db_campaign_contact_after_2nd_call.medical_assignment_date is None

    # Si tienes un campo `updated_at` en tu modelo CampaignContact,
    # deberías verificar que no se haya modificado en la segunda llamada
    # ya que no hubo cambios reales (si tu lógica de servicio lo maneja así).
    # Por ejemplo:
    # assert db_session.query(CampaignContact).filter_by(id=campaign_contact.id).first().updated_at == updated_at_1


# --- Test Suite 3: Integration Testing (Simulación) ---
# Los tests de integración suelen ser más complejos y simulan un flujo completo.
# El informe QA menciona un script bash. Aquí simularé una pequeña parte del flujo.

def test_full_campaign_flow_simulation(client: TestClient, db_session: Session, create_test_contact, create_test_campaign, create_test_campaign_contact, create_test_advisor):
    """
    Simulación de un flujo completo: Contacto -> Campaign -> CampaignContact -> Actualización.
    """
    # Paso 1: Crear un nuevo contacto (simulado por la fixture create_test_contact)
    contact_manychat_id = "flow_manychat_id_1"
    contact = create_test_contact(manychat_id=contact_manychat_id, first_name="Gabriela")
    assert contact.id is not None

    # Paso 2: Crear una Campaña (simulado por la fixture create_test_campaign)
    campaign_id_for_flow = 50
    campaign = create_test_campaign(id=campaign_id_for_flow, name="Campaña Flujo", date_start=datetime.now(timezone.utc))
    assert campaign.id is not None

    # Paso 3: Crear un CampaignContact para ese contacto y campaña (simulado por la fixture)
    campaign_contact = create_test_campaign_contact(
        contact_id=contact.id,
        campaign_id=campaign.id, # Usamos el ID de la campaña creada
        registration_date=datetime.now(timezone.utc)
    )
    assert campaign_contact.id is not None
    assert campaign_contact.last_state is None
    assert campaign_contact.medical_advisor_id is None

    # Paso 4: Crear un asesor
    advisor = create_test_advisor(id=606, name="Dr. Flow", odoo_id="advisor_606")
    assert advisor.id is not None

    # Paso 5: Actualizar el CampaignContact a través del endpoint PUT
    update_data = {
        "manychat_id": contact_manychat_id,
        "campaign_id": campaign_id_for_flow, # Usamos el ID de la campaña para la actualización específica
        "medical_advisor_id": advisor.id,
        "medical_assignment_date": datetime.now(timezone.utc).isoformat(),
        "last_state": "Completed Flow"
    }
    response = client.put(ENDPOINT_URL, json=update_data)
    assert response.status_code == 200
    db_session.expire_all()  # Ensure session sees latest DB state
    # Paso 6: Verificar el estado final en la base de datos
    db_updated_cc = db_session.query(CampaignContact).filter_by(id=campaign_contact.id).first()
    assert db_updated_cc.medical_advisor_id == advisor.id
    assert db_updated_cc.last_state == "Completed Flow"
    assert db_updated_cc.medical_assignment_date is not None
    # Puedes añadir más aserciones para verificar que otros campos no se corrompieron.