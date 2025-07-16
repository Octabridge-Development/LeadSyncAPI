import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict # Importa SettingsConfigDict
from functools import lru_cache
from pydantic import Field, AnyHttpUrl # AnyHttpUrl se usa para Odoo_URL

# Para Key Vault, aunque no es el foco ahora, si lo activas, asegúrate de que estas libs estén instaladas
# from azure.identity import DefaultAzureCredential
# from azure.keyvault.secrets import SecretClient

class Settings(BaseSettings):
    # --- Configuración General ---
    DEBUG: bool = Field(True, alias="DEBUG")
    API_KEY: str = Field(..., alias="API_KEY")
    API_V1_STR: str = Field("/api/v1", alias="API_V1_STR")
    PORT: int = Field(8000, alias="PORT")


    # --- Azure ---
    AZURE_STORAGE_CONNECTION_STRING: str = Field(..., alias="AZURE_STORAGE_CONNECTION_STRING")
    DATABASE_URL: str = Field(..., alias="DATABASE_URL")
    USE_KEY_VAULT: bool = Field(False, alias="USE_KEY_VAULT")
    KEY_VAULT_NAME: str = Field("", alias="KEY_VAULT_NAME")

    # --- Logging ---
    LOG_LEVEL: str = Field("INFO", alias="LOG_LEVEL")
    LOG_FORMAT: str = Field("json", alias="LOG_FORMAT")
    APPINSIGHTS_INSTRUMENTATION_KEY: Optional[str] = Field(None, alias="APPINSIGHTS_INSTRUMENTATION_KEY")
    
    # --- Odoo ---
    ODOO_URL: Optional[str] = Field(None, alias="ODOO_URL")
    ODOO_DB: Optional[str] = Field(None, alias="ODOO_DB")
    ODOO_USERNAME: Optional[str] = Field(None, alias="ODOO_USERNAME")
    ODOO_PASSWORD: Optional[str] = Field(None, alias="ODOO_PASSWORD")

    # --- CAMBIO CLAVE AQUÍ: Usar model_config para Pydantic v2 ---
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"), # Lee el archivo .env especificado por ENV_FILE o por defecto .env
        env_file_encoding="utf-8",
        extra='ignore' # Ignora variables en el .env que no estén definidas en la clase Settings
    )
    # -----------------------------------------------------------

    def load_secrets_from_key_vault(self):
        """Carga secretos desde Azure Key Vault si está habilitado."""
        if self.USE_KEY_VAULT and self.KEY_VAULT_NAME:
            # Importaciones condicionales para evitar errores si no se usan las libs de Azure
            try:
                from azure.identity import DefaultAzureCredential
                from azure.keyvault.secrets import SecretClient
            except ImportError:
                print("ERROR: Las librerías 'azure-identity' o 'azure-keyvault-secrets' no están instaladas.")
                print("Instala con: pip install azure-identity azure-keyvault-secrets")
                raise

            print(f"INFO: Cargando secretos desde Azure Key Vault: {self.KEY_VAULT_NAME}...")
            try:
                credential = DefaultAzureCredential()
                key_vault_url = f"https://{self.KEY_VAULT_NAME}.vault.azure.net"
                client = SecretClient(vault_url=key_vault_url, credential=credential)

                # Usar setattr para asignar directamente a los campos de la instancia
                # Los nombres de los secretos en Key Vault deben coincidir con estos (ej. "API-KEY")
                self.API_KEY = client.get_secret("API-KEY").value
                self.AZURE_STORAGE_CONNECTION_STRING = client.get_secret("AZURE-STORAGE-CONNECTION-STRING").value
                self.DATABASE_URL = client.get_secret("DATABASE-URL").value
                
                try:
                    self.APPINSIGHTS_INSTRUMENTATION_KEY = client.get_secret("APPINSIGHTS-INSTRUMENTATION-KEY").value
                except Exception:
                    print("WARN: La clave 'APPINSIGHTS-INSTRUMENTATION-KEY' no se encontró en Key Vault.")

                print("INFO: Secretos cargados exitosamente desde Key Vault.")
            except Exception as e:
                print(f"ERROR: Fallo al cargar secretos desde Key Vault: {e}")
                raise IOError("No se pudieron cargar los secretos de Azure Key Vault.")
        else:
            print("INFO: Azure Key Vault no está habilitado.")

@lru_cache()
def get_settings() -> Settings:
    """
    Crea y retorna una instancia única de la configuración.
    """
    print("INFO: Inicializando configuración de la aplicación...")
    settings = Settings()
    # Solo cargar secretos de Key Vault si USE_KEY_VAULT es True
    if getattr(settings, "USE_KEY_VAULT", False):
        settings.load_secrets_from_key_vault()
        
    print("INFO: Configuración cargada exitosamente.")
    return settings