# Este archivo contiene la configuración centralizada del proyecto.
# Utiliza Pydantic para manejar variables de entorno y Azure Key Vault para secretos sensibles.
# Proporciona la clase Settings y la función get_settings para acceder a la configuración.

from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import Field, AnyHttpUrl
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Configuración centralizada usando Pydantic v2
class Settings(BaseSettings):
    DEBUG: bool = Field(True, alias="DEBUG")  # Modo debug
    API_KEY: str = Field("", alias="API_KEY")  # API Key para proteger endpoints
    API_V1_STR: str = Field("/api/v1", alias="API_V1_STR")  # Prefijo de la API
    # Odoo
    ODOO_URL: AnyHttpUrl = Field(..., alias="ODOO_URL")  # URL completa de Odoo (https://...)
    ODOO_DB: str = Field(..., alias="ODOO_DB")  # Nombre de la base de datos Odoo
    ODOO_USERNAME: str = Field(..., alias="ODOO_USERNAME")  # Usuario de Odoo
    ODOO_PASSWORD: str = Field(..., alias="ODOO_PASSWORD")  # Contraseña de Odoo
    ODOO_RATE_LIMIT: float = Field(1.0, alias="ODOO_RATE_LIMIT")  # 1 req/segundo
    # Azure y otros campos existentes...
    AZURE_STORAGE_CONNECTION_STRING: str = Field("", alias="AZURE_STORAGE_CONNECTION_STRING")
    DATABASE_URL: str = Field("", alias="DATABASE_URL")
    USE_KEY_VAULT: bool = Field(False, alias="USE_KEY_VAULT")
    KEY_VAULT_NAME: str = Field("", alias="KEY_VAULT_NAME")

    # Configuración para cargar desde .env
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }

    def load_secrets_from_key_vault(self):
        """Carga secretos desde Azure Key Vault si está habilitado."""
        if self.USE_KEY_VAULT:
            credential = DefaultAzureCredential()
            key_vault_url = f"https://{self.KEY_VAULT_NAME}.vault.azure.net"
            client = SecretClient(vault_url=key_vault_url, credential=credential)

            # Sobrescribir configuraciones con secretos del Key Vault
            self.API_KEY = client.get_secret("API-KEY").value
            self.ODOO_PASSWORD = client.get_secret("ODOO-PASSWORD").value
            self.AZURE_STORAGE_CONNECTION_STRING = client.get_secret("AZURE-STORAGE-CONNECTION-STRING").value
            self.DATABASE_URL = client.get_secret("DATABASE-URL").value

@lru_cache()
def get_settings():
    settings = Settings()
    settings.load_secrets_from_key_vault()
    return settings