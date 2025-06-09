# tests/conftest.py
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv
from typing import Generator, Tuple
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import importlib # Importar esto

# Importamos Base desde app.db.session. Esto es seguro porque Base es un objeto estático
# y no activa la inicialización del motor/sesión.
from app.db.session import Base
from app.db.models import Contact, CampaignContact, Advisor, Campaign, ProductInteraction, ContactState, Client, Lead, OrderProduct

# Importamos los módulos para parchearlos, no sus contenidos directos.
import app.db.session as db_session_module
import app.core.config as app_config_module
import app.api.deps as api_deps_module # Asumimos que app.api.deps existe y tiene get_db, get_queue_service
import app.services.queue_service as queue_service_module # Para parchear la clase QueueService
import app.services.azure_sql_service as azure_sql_service_module # Para parchear la clase AzureSQLService


# --- PASO CRUCIAL: Configurar variables de entorno ANTES de cualquier importación de la app ---
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(TESTS_DIR, '.env')
load_dotenv(DOTENV_PATH, override=True)

# Configuración explícita para pruebas en memoria y mocks de credenciales.
# Estas variables de entorno pueden ser usadas por get_settings si no se parchea,
# pero el parcheo de get_settings es la estrategia más robusta ahora.
# Cambia la base de datos a la real para pruebas integradas
os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "mssql+pyodbc://usuario:password@servidor.database.windows.net:1433/basedatos?driver=ODBC+Driver+17+for+SQL+Server")
os.environ["AZURE_STORAGE_CONNECTION_STRING"] = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=https;AccountName=teststorage;AccountKey=dummykeydummykeydummykeydummykeydummykeydummykeydummykeydummykey;EndpointSuffix=core.windows.net")
os.environ["API_KEY"] = os.getenv("API_KEY", "test_api_key_for_tests")
os.environ["ODOO_URL"] = os.getenv("ODOO_URL", "http://test.odoo.local")
os.environ["ODOO_DB"] = os.getenv("ODOO_DB", "test_odoo_db")
os.environ["ODOO_USERNAME"] = os.getenv("ODOO_USERNAME", "test_odoo_user")
os.environ["ODOO_PASSWORD"] = os.getenv("ODOO_PASSWORD", "test_odoo_password")
os.environ["USE_KEY_VAULT"] = os.getenv("USE_KEY_VAULT", "false")


# --- Fixture para proporcionar 'mocker' a nivel de sesión ---
@pytest.fixture(scope="session")
def session_mocker(pytestconfig):
    """
    Proporciona una instancia de mocker de pytest-mock con alcance de sesión.
    """
    from pytest_mock import MockerFixture
    _mocker = MockerFixture(pytestconfig)
    yield _mocker
    _mocker.stopall()


# --- PARCHADO AGRESIVO DE LA DB Y SERVICIOS EXTERNOS (AUTOUSE SESSION SCOPE) ---
@pytest.fixture(autouse=True, scope="session")
def setup_global_mocks_and_db(session_mocker):
    """
    Realiza un parcheo de servicios externos (colas, Azure, etc.) para pruebas,
    pero NO parchea la base de datos ni el engine/session de SQLAlchemy.
    Así, los tests usan la base real definida por DATABASE_URL.
    """
    print("\n--- Configurando mocks globales con pytest-mock (solo servicios externos, no DB) ---")
    
    # 1. Mockear app.core.config.get_settings SOLO para servicios externos y API_KEY
    mock_settings_instance = MagicMock()
    mock_settings_instance.API_KEY = "Miasaludnatural123**"
    mock_settings_instance.ODOO_URL = "https://ironsolutionbd.odoo.com"
    mock_settings_instance.ODOO_DB = "ironsolutionbd"
    mock_settings_instance.ODOO_USERNAME = "sistemas@miasaludnatural.com"
    mock_settings_instance.ODOO_PASSWORD = "Mia123**"
    mock_settings_instance.AZURE_STORAGE_CONNECTION_STRING = ""
    mock_settings_instance.DATABASE_URL = "mssql+pyodbc://ironsolution:universo123**@miasaludnatural.database.windows.net:1433/miasaludnaturaldb?driver=ODBC+Driver+18+for+SQL+Server"
    mock_settings_instance.USE_KEY_VAULT = False
    mock_settings_instance.DEBUG = True
    mock_settings_instance.API_V1_STR = "/api/v1"
    

    session_mocker.patch.object(app_config_module, 'get_settings', return_value=mock_settings_instance)
    if hasattr(app_config_module, '_settings'):
        session_mocker.patch.object(app_config_module, '_settings', mock_settings_instance)
    importlib.reload(app_config_module)
    print("--- app.core.config module re-cargado para aplicar parche a 'get_settings'. ---")

    # 2. Mockear servicios externos (colas, Azure, etc.)
    class MockQueueServiceImplementation:
        def __init__(self):
            print("MockQueueServiceImplementation (app.services.queue_service) instanciado. (Este es un mock, no una conexión real a Azure).")
        def send_message(self, queue_name: str, message_body: str):
            print(f"MockQueueService (app.services.queue_service): Mensaje mockeado enviado a {queue_name}: {message_body[:50]}...")
            pass
        def _ensure_queues_exist(self):
            print("MockQueueService (app.services.queue_service): Verificando colas (mocked).")
            pass
        @property
        def main_queue_name(self): return "mock-main-queue"
        @property
        def campaign_queue_name(self): return "mock-campaign-queue"
        @property
        def contact_queue_name(self): return "mock-contact-queue"
        @property
        def dlq_name(self): return "mock-dlq"
    session_mocker.patch('app.services.queue_service.QueueService', new=MockQueueServiceImplementation)
    session_mocker.patch.object(api_deps_module, '_queue_service_instance', MockQueueServiceImplementation())
    print("--- app.services.queue_service.QueueService y app.api.deps._queue_service_instance mockeados. ---")

    class MockAzureSQLService:
        def __init__(self):
            print("MockAzureSQLService (app.services.azure_sql_service) instanciado. (Este es un mock, no una conexión real a Azure SQL).")
        def get_contact_by_manychat_id(self, manychat_id: str):
            print(f"MockAzureSQLService (app.services.azure_sql_service): get_contact_by_manychat_id llamado para {manychat_id} (mocked).")
            return None
        def get_advisor_by_id(self, advisor_id: int):
            print(f"MockAzureSQLService (app.services.azure_sql_service): get_advisor_by_id llamado para {advisor_id} (mocked).")
            return MagicMock(id=advisor_id, name="Mock Advisor")
        def process_campaign_event(self, event_obj):
            print(f"MockAzureSQLService (app.services.azure_sql_service): process_campaign_event llamado (mocked).")
            pass
    session_mocker.patch('app.services.azure_sql_service.AzureSQLService', new=MockAzureSQLService)
    session_mocker.patch.object(api_deps_module, '_azure_sql_service_instance', MockAzureSQLService())
    print("--- app.services.azure_sql_service.AzureSQLService y app.api.deps._azure_sql_service_instance mockeados. ---")

    # 3. Mockear Azure Key Vault para evitar llamadas de red
    try:
        from azure.keyvault.secrets import SecretClient
        session_mocker.patch('azure.keyvault.secrets.SecretClient.get_secret', return_value=MagicMock(value="mock_secret_value"))
        print("--- Azure Key Vault SecretClient mockeado exitosamente. ---")
    except ImportError as e:
        print(f"--- No se pudo importar azure.keyvault.secrets.SecretClient para mockearlo: {e} ---")
    try:
        from azure.identity import DefaultAzureCredential
        session_mocker.patch('azure.identity.DefaultAzureCredential', return_value=MagicMock())
        print("--- azure.identity.DefaultAzureCredential mockeado exitosamente. ---")
    except ImportError as e:
        print(f"--- No se pudo importar azure.identity.DefaultAzureCredential para mockearlo: {e} ---")
    yield


# --- Fixture para la sesión de base de datos (por test) ---
@pytest.fixture(name="db_session")
def db_session_fixture() -> Generator[Session, None, None]:
    """
    Proporciona una sesión de base de datos real para pruebas.
    No crea ni elimina tablas, solo maneja la sesión.
    """
    from app.db.session import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# --- Fixture para el cliente de prueba de FastAPI ---
@pytest.fixture(name="client")
def client_fixture(db_session: Session, setup_global_mocks_and_db) -> Generator[TestClient, None, None]:
    """
    Proporciona un cliente de prueba de FastAPI.
    Sobrescribe las dependencias de la base de datos y servicios externos.
    El TestClient resultante siempre envía el header x-api-key correcto.
    """
    from app.main import app
    def override_get_db_for_client():
        session = db_session_module.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    def override_get_queue_service():
        return api_deps_module._queue_service_instance
    def override_get_azure_sql_service():
        return api_deps_module._azure_sql_service_instance
    app.dependency_overrides[api_deps_module.get_db] = override_get_db_for_client
    app.dependency_overrides[api_deps_module.get_db_session] = override_get_db_for_client
    app.dependency_overrides[api_deps_module.get_queue_service] = override_get_queue_service
    app.dependency_overrides[api_deps_module.get_azure_sql_service] = override_get_azure_sql_service
    settings = app_config_module.get_settings()
    api_key_for_tests = "Miasaludnatural123**"  # Forzar la API Key correcta
    class APIKeyTestClient(TestClient):
        def request(self, method, url, **kwargs):
            headers = kwargs.pop("headers", {}) or {}
            headers["x-api-key"] = api_key_for_tests
            kwargs["headers"] = headers
            return super().request(method, url, **kwargs)
    with APIKeyTestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- Fixtures de creación de datos ---
# Estas fixtures usan la db_session provista por pytest.
@pytest.fixture
def create_test_contact(db_session: Session):
    def _create_contact(manychat_id: str, **kwargs) -> Contact:
        existing = db_session.query(Contact).filter_by(manychat_id=manychat_id).first()
        if existing:
            # Limpiar en cascada según el DER
            db_session.query(CampaignContact).filter_by(contact_id=existing.id).delete()
            db_session.query(ProductInteraction).filter_by(contact_id=existing.id).delete()
            db_session.query(ContactState).filter_by(contact_id=existing.id).delete()
            db_session.query(Lead).filter(Lead.campaign_contact_id.in_(
                db_session.query(CampaignContact.id).filter_by(contact_id=existing.id)
            )).delete(synchronize_session=False)
            db_session.delete(existing)
            db_session.commit()
        contact_data = {
            "manychat_id": manychat_id,
            "first_name": "Test",
            "last_name": "Contact",
            "phone": "1234567890",
            "email": f"{manychat_id}@example.com",
            "subscription_date": datetime.now(timezone.utc),
            "entry_date": datetime.now(timezone.utc),
            "initial_state": "New Lead",
            "gender": "Unknown",
            **kwargs
        }
        valid_keys = {column.key for column in Contact.__table__.columns}
        valid_keys.update({rel.key for rel in Contact.__mapper__.relationships})
        filtered_contact_data = {k: v for k, v in contact_data.items() if k in valid_keys}
        contact = Contact(**filtered_contact_data)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        return contact
    return _create_contact

@pytest.fixture
def create_test_campaign(db_session: Session):
    def _create_campaign(id: int, name: str, date_start: datetime, **kwargs) -> Campaign:
        existing = db_session.query(Campaign).filter_by(id=id).first()
        if existing:
            # Limpiar en cascada según el DER
            db_session.query(CampaignContact).filter_by(campaign_id=existing.id).delete()
            db_session.delete(existing)
            db_session.commit()
        campaign_data = {
            "id": id,
            "name": name,
            "date_start": date_start,
            "date_end": date_start + timedelta(days=30),
            "budget": 1000.00,
            "status": "Active",
            **kwargs
        }
        valid_keys = {column.key for column in Campaign.__table__.columns}
        valid_keys.update({rel.key for rel in Campaign.__mapper__.relationships})
        filtered_campaign_data = {k: v for k, v in campaign_data.items() if k in valid_keys}
        campaign = Campaign(**filtered_campaign_data)
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)
        return campaign
    return _create_campaign

@pytest.fixture
def create_test_advisor(db_session: Session):
    def _create_advisor(id: int, name: str, odoo_id: str = None, **kwargs) -> Advisor:
        existing = db_session.query(Advisor).filter_by(id=id).first()
        if existing:
            db_session.query(CampaignContact).filter_by(commercial_advisor_id=existing.id).delete()
            db_session.query(CampaignContact).filter_by(medical_advisor_id=existing.id).delete()
            db_session.delete(existing)
            db_session.commit()
        advisor_data = {
            "id": id,
            "name": name,
            "email": f"{name.lower().replace(' ', '')}@example.com",
            "phone": "9876543210",
            "role": "General",
            "status": "Active",
            "genre": "Male",
            "odoo_id": odoo_id if odoo_id else f"odoo_{id}",
            **kwargs
        }
        valid_keys = {column.key for column in Advisor.__table__.columns}
        valid_keys.update({rel.key for rel in Advisor.__mapper__.relationships})
        filtered_advisor_data = {k: v for k, v in advisor_data.items() if k in valid_keys}

        advisor = Advisor(**filtered_advisor_data)
        db_session.add(advisor)
        db_session.commit()
        db_session.refresh(advisor)
        return advisor
    return _create_advisor

@pytest.fixture
def create_test_campaign_contact(db_session: Session):
    def _create_campaign_contact(contact_id: int, campaign_id: int, registration_date: datetime, **kwargs) -> CampaignContact:
        campaign_contact_data = {
            "contact_id": contact_id,
            "campaign_id": campaign_id,
            "registration_date": registration_date,
            **kwargs
        }
        valid_keys = {column.key for column in CampaignContact.__table__.columns}
        valid_keys.update({rel.key for rel in CampaignContact.__mapper__.relationships})
        filtered_cc_data = {k: v for k, v in campaign_contact_data.items() if k in valid_keys}

        campaign_contact = CampaignContact(**filtered_cc_data)
        db_session.add(campaign_contact)
        db_session.commit()
        db_session.refresh(campaign_contact)
        return campaign_contact
    return _create_campaign_contact