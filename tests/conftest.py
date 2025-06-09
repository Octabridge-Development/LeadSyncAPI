# tests/conftest.py
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
from app.db.models import Contact, CampaignContact, Advisor, Campaign

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
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AZURE_STORAGE_CONNECTION_STRING"] = "DefaultEndpointsProtocol=https;AccountName=teststorage;AccountKey=dummykeydummykeydummykeydummykeydummykeydummykeydummykeydummykey;EndpointSuffix=core.windows.net"
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
def setup_global_mocks_and_db(session_mocker): # Ya no necesita devolver nada, parchea directamente
    """
    Realiza un parcheo agresivo del motor de DB y de los servicios externos
    para asegurar que las pruebas sean aisladas y usen la configuración correcta.
    """
    print("\n--- Configurando mocks globales con pytest-mock ---")

    # 1. Mockear app.core.config.get_settings (PRIORIDAD ALTA: debe ser lo primero)
    mock_settings_instance = MagicMock()
    mock_settings_instance.DATABASE_URL = "sqlite:///:memory:"
    mock_settings_instance.API_KEY = os.getenv("API_KEY", "test_api_key_for_tests")
    # Asignar la URL como un string simple
    mock_settings_instance.ODOO_URL = "http://test.odoo.local" 
    mock_settings_instance.ODOO_DB = os.getenv("ODOO_DB", "test_odoo_db")
    mock_settings_instance.ODOO_USERNAME = os.getenv("ODOO_USERNAME", "test_odoo_user")
    mock_settings_instance.ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "test_odoo_password")
    mock_settings_instance.AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=teststorage;AccountKey=dummykeydummykeydummykeydummykeydummykeydummykeydummykeydummykey;EndpointSuffix=core.windows.net"
    mock_settings_instance.USE_KEY_VAULT = False
    mock_settings_instance.DEBUG = True # Importante para logs de prueba
    # Añadimos API_V1_STR al mock de settings para resolver el AssertionError
    mock_settings_instance.API_V1_STR = "/api/v1" # Sin trailing slash
    
    session_mocker.patch.object(app_config_module, 'get_settings', return_value=mock_settings_instance)
    # Si app.core.config usa un patrón singleton con una variable global como _settings,
    # también es buena práctica parchear esa variable para forzar su reinicio o usar el mock.
    if hasattr(app_config_module, '_settings'):
        session_mocker.patch.object(app_config_module, '_settings', mock_settings_instance)

    # --- AHORA: Recargar el módulo app.core.config para que tome el mock ---
    # Esto es crucial para asegurar que `get_settings()` en `app.core.config` devuelva el mock
    # para cualquier módulo que lo importe después de este punto.
    importlib.reload(app_config_module)
    print("--- app.core.config module re-cargado para aplicar parche a 'get_settings'. ---")
    
    # 2. Mockear sqlalchemy.create_engine para controlar parámetros específicos de SQLite
    original_create_engine = create_engine
    
    def mocked_create_engine(url, **kwargs):
        if url == "sqlite:///:memory:":
            kwargs.pop("pool_size", None)
            kwargs.pop("max_overflow", None)
            kwargs.pop("pool_recycle", None)
            if "connect_args" not in kwargs:
                kwargs["connect_args"] = {}
            # Asegura check_same_thread=False para compatibilidad con hilos en pruebas
            kwargs["connect_args"]["check_same_thread"] = False 
            kwargs["connect_args"].pop("prepared_statement_cache_size", None)
        return original_create_engine(url, **kwargs)

    session_mocker.patch('sqlalchemy.create_engine', side_effect=mocked_create_engine)
    print("--- sqlalchemy.create_engine mockeado para SQLite. ---")

    # AHORA, creamos el engine y SessionLocal de prueba usando los mocks ya establecidos.
    # Esto asegura que cualquier 'create_engine' use nuestro mock, y las settings sean las de prueba.
    print("--- Creando engine y SessionLocal de prueba para parcheo directo ---")
    test_engine = create_engine(
        mock_settings_instance.DATABASE_URL,
        connect_args={"check_same_thread": False} 
    )
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    print("--- Engine y SessionLocal de prueba creados. ---")

    # 3. Parchear directamente los objetos globales 'engine', 'SessionLocal' y 'get_db' en app.db.session
    # ESTO ES CRÍTICO. Asegura que cuando app.db.session se importa, sus variables globales
    # apunten a nuestras instancias de prueba, y que get_db devuelva sesiones de la SessionLocal de prueba.
    session_mocker.patch.object(db_session_module, 'engine', test_engine)
    session_mocker.patch.object(db_session_module, 'SessionLocal', test_session_local)
    # Parcheamos get_db para que siempre use la SessionLocal de prueba
    session_mocker.patch.object(db_session_module, 'get_db', side_effect=test_session_local)
    print("--- app.db.session.engine, SessionLocal y get_db parcheados. ---")

    # 4. Mockear el QueueService de Azure Storage y sus instancias singleton
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

    # Parchear la clase QueueService directamente en app.services.queue_service
    session_mocker.patch('app.services.queue_service.QueueService', new=MockQueueServiceImplementation)
    # Parchear la instancia singleton _queue_service_instance directamente en app.api.deps
    session_mocker.patch.object(api_deps_module, '_queue_service_instance', MockQueueServiceImplementation())
    print("--- app.services.queue_service.QueueService y app.api.deps._queue_service_instance mockeados. ---")

    # 5. Mockear AzureSQLService y su instancia singleton
    class MockAzureSQLService:
        def __init__(self):
            print("MockAzureSQLService (app.services.azure_sql_service) instanciado. (Este es un mock, no una conexión real a Azure SQL).")
        def get_contact_by_manychat_id(self, manychat_id: str):
            print(f"MockAzureSQLService (app.services.azure_sql_service): get_contact_by_manychat_id llamado para {manychat_id} (mocked).")
            # Devolver un mock de Contact si se espera que exista en ciertos tests
            if manychat_id.startswith("manychat_id_existente"):
                mock_contact = MagicMock(id=1, manychat_id=manychat_id, first_name="Mock", last_name="Contact")
                return mock_contact
            return None 
        # Añade aquí otros métodos que tu aplicación llame en AzureSQLService
        def get_advisor_by_id(self, advisor_id: int):
            print(f"MockAzureSQLService (app.services.azure_sql_service): get_advisor_by_id llamado para {advisor_id} (mocked).")
            return MagicMock(id=advisor_id, name="Mock Advisor") # Simular un Advisor existente

        def process_campaign_event(self, event_obj):
            print(f"MockAzureSQLService (app.services.azure_sql_service): process_campaign_event llamado (mocked).")
            pass


    session_mocker.patch('app.services.azure_sql_service.AzureSQLService', new=MockAzureSQLService)
    # Parchear la instancia singleton _azure_sql_service_instance directamente en app.api.deps
    session_mocker.patch.object(api_deps_module, '_azure_sql_service_instance', MockAzureSQLService())
    print("--- app.services.azure_sql_service.AzureSQLService y app.api.deps._azure_sql_service_instance mockeados. ---")

    # 6. Mockear Azure Key Vault para evitar llamadas de red
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
# Ahora usa las instancias de engine y SessionLocal generadas y parcheadas directamente en db_session_module.
@pytest.fixture(name="db_session")
def db_session_fixture(setup_global_mocks_and_db) -> Generator[Session, None, None]:
    """
    Proporciona una sesión de base de datos para pruebas.
    Crea las tablas, las limpia después de cada prueba.
    """
    # Accedemos al engine y SessionLocal a través del módulo app.db.session,
    # que ya fue parcheado por setup_global_mocks_and_db.
    engine = db_session_module.engine
    SessionLocal = db_session_module.SessionLocal
    
    # IMPORTANTE: Asegurarse de que Base.metadata.create_all se llama aquí,
    # en la instancia de DB que usará el test.
    Base.metadata.create_all(bind=engine) 
    session = SessionLocal() # Creamos una nueva sesión para cada test
    try:
        yield session
    finally:
        session.close()
        # Es buena práctica borrar las tablas para cada test para asegurar aislamiento.
        # Para SQLite en memoria, esto también ayuda a garantizar una base de datos limpia.
        Base.metadata.drop_all(bind=engine)

# --- Fixture para el cliente de prueba de FastAPI ---
@pytest.fixture(name="client")
def client_fixture(db_session: Session, setup_global_mocks_and_db) -> Generator[TestClient, None, None]:
    """
    Proporciona un cliente de prueba de FastAPI.
    Sobrescribe las dependencias de la base de datos y servicios externos.
    """
    # IMPORTAMOS LA APLICACIÓN DE FASTAPI AQUÍ.
    # Esto asegura que app.main se inicialice *después* de que todos los mocks y parcheos globales
    # (incluyendo los de app.db.session y app.api.deps) estén en su lugar.
    from app.main import app 

    # Sobrescribir get_db (y get_db_session) para que proporcione una NUEVA sesión de SessionLocal por cada solicitud
    # Ya está parcheado a nivel de módulo, pero podemos re-afirmarlo aquí si es necesario.
    def override_get_db_for_client():
        # Usamos la SessionLocal parcheada del módulo db_session_module.
        session = db_session_module.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    # Sobrescribir get_queue_service para inyectar nuestro mock.
    def override_get_queue_service():
        # Devuelve la instancia mockeada que fue parcheada directamente en app.api.deps._queue_service_instance
        return api_deps_module._queue_service_instance

    # Sobrescribir get_azure_sql_service para inyectar nuestro mock.
    def override_get_azure_sql_service():
        # Devuelve la instancia mockeada que fue parcheada directamente en app.api.deps._azure_sql_service_instance
        return api_deps_module._azure_sql_service_instance

    app.dependency_overrides[api_deps_module.get_db] = override_get_db_for_client
    app.dependency_overrides[api_deps_module.get_db_session] = override_get_db_for_client # Alias en deps.py
    app.dependency_overrides[api_deps_module.get_queue_service] = override_get_queue_service
    app.dependency_overrides[api_deps_module.get_azure_sql_service] = override_get_azure_sql_service
    
    # Obtener la API_KEY de las settings (que ya están configuradas para test)
    settings = app_config_module.get_settings() # Accede a las settings mockeadas
    api_key_for_tests = settings.API_KEY

    # Definir los headers con la API Key
    test_headers = {
        "x-api-key": api_key_for_tests
    }

    # Pasar los headers al TestClient
    with TestClient(app, headers=test_headers) as test_client:
        yield test_client
    
    # Limpiar las sobrescrituras al final del test
    app.dependency_overrides.clear()


# --- Fixtures de creación de datos ---
# Estas fixtures usan la db_session provista por pytest.
@pytest.fixture
def create_test_contact(db_session: Session):
    def _create_contact(manychat_id: str, **kwargs) -> Contact:
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
def create_test_advisor(db_session: Session):
    def _create_advisor(id: int, name: str, odoo_id: str = None, **kwargs) -> Advisor:
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
def create_test_campaign(db_session: Session):
    def _create_campaign(id: int, name: str, date_start: datetime, **kwargs) -> Campaign:
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