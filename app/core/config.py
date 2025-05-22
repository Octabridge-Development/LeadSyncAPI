from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import Field, AnyHttpUrl

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

@lru_cache()
def get_settings():
    """Devuelve una instancia única de Settings (patrón singleton)."""
    return Settings()