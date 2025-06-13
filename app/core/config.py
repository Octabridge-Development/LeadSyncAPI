# app/core/config.py
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import Field, AnyHttpUrl
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from app.core.logging import logger # Importar el logger para usarlo aquí

# Configuración centralizada, ahora la única fuente de verdad para toda la app.
class Settings(BaseSettings):
    # --- Configuración General ---
    DEBUG: bool = Field(True, alias="DEBUG")
    API_KEY: str = Field(..., alias="API_KEY")
    API_V1_STR: str = Field("/api/v1", alias="API_V1_STR")
    PORT: int = Field(8000, alias="PORT") # Puerto para el servidor Uvicorn

    # --- Odoo ---
    ODOO_URL: AnyHttpUrl = Field(..., alias="ODOO_URL")
    ODOO_DB: str = Field(..., alias="ODOO_DB")
    ODOO_USERNAME: str = Field(..., alias="ODOO_USERNAME")
    ODOO_PASSWORD: str = Field(..., alias="ODOO_PASSWORD")
    ODOO_RATE_LIMIT: float = Field(1.0, alias="ODOO_RATE_LIMIT")

    # --- Azure ---
    AZURE_STORAGE_CONNECTION_STRING: str = Field(..., alias="AZURE_STORAGE_CONNECTION_STRING")
    DATABASE_URL: str = Field(..., alias="DATABASE_URL")
    USE_KEY_VAULT: bool = Field(False, alias="USE_KEY_VAULT")
    KEY_VAULT_NAME: str = Field("", alias="KEY_VAULT_NAME")

    # --- INICIO DE LA CORRECCIÓN: Variables de Logging centralizadas ---
    LOG_LEVEL: str = Field("INFO", alias="LOG_LEVEL")
    LOG_FORMAT: str = Field("json", alias="LOG_FORMAT")
    APPINSIGHTS_INSTRUMENTATION_KEY: Optional[str] = Field(None, alias="APPINSIGHTS_INSTRUMENTATION_KEY")
    # --- FIN DE LA CORRECCIÓN ---
    
    class Config:
        # Pydantic v1 style config class is deprecated, use model_config dict instead
        env_file = os.getenv("ENV_FILE", ".env")
        env_file_encoding = "utf-8"

    def load_secrets_from_key_vault(self):
        """Carga secretos desde Azure Key Vault si está habilitado."""
        if self.USE_KEY_VAULT and self.KEY_VAULT_NAME:
            logger.info(f"Cargando secretos desde Azure Key Vault: {self.KEY_VAULT_NAME}...")
            try:
                credential = DefaultAzureCredential()
                key_vault_url = f"https://{self.KEY_VAULT_NAME}.vault.azure.net"
                client = SecretClient(vault_url=key_vault_url, credential=credential)

                # Sobrescribir configuraciones con secretos del Key Vault
                self.API_KEY = client.get_secret("API-KEY").value
                self.ODOO_PASSWORD = client.get_secret("ODOO-PASSWORD").value
                self.AZURE_STORAGE_CONNECTION_STRING = client.get_secret("AZURE-STORAGE-CONNECTION-STRING").value
                self.DATABASE_URL = client.get_secret("DATABASE-URL").value
                
                # Cargar la clave de App Insights si existe en el vault
                try:
                    self.APPINSIGHTS_INSTRUMENTATION_KEY = client.get_secret("APPINSIGHTS-INSTRUMENTATION-KEY").value
                except Exception:
                    logger.warning("La clave 'APPINSIGHTS-INSTRUMENTATION-KEY' no se encontró en Key Vault. Se usará el valor del .env si existe.")

                logger.info("Secretos cargados exitosamente desde Key Vault.")
            except Exception as e:
                logger.error(f"Fallo al cargar secretos desde Key Vault: {e}", exc_info=True)
                raise IOError("No se pudieron cargar los secretos de Azure Key Vault.")
        else:
            logger.info("Azure Key Vault no está habilitado. Se usarán las variables de entorno locales.")

@lru_cache()
def get_settings() -> Settings:
    """
    Crea y retorna una instancia única (cacheada) de la configuración.
    Carga los secretos de Key Vault si está configurado.
    """
    logger.info("Inicializando configuración de la aplicación...")
    settings = Settings()
    try:
        settings.load_secrets_from_key_vault()
    except IOError as e:
        # Detener la aplicación si Key Vault está habilitado pero falla
        logger.critical(f"Error fatal de configuración: {e}")
        # En un entorno real, esto debería causar que la aplicación no se inicie.
        # Por simplicidad, aquí solo logueamos el error crítico.
        raise
        
    logger.info("Configuración cargada exitosamente.")
    return settings