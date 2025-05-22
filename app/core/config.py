from pydantic import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    DEBUG: bool = True
    API_KEY: str = ""
    API_V1_STR: str = "/api/v1"
    ODOO_HOST: str = ""
    ODOO_PORT: int = 443
    ODOO_PROTOCOL: str = "jsonrpc+ssl"
    ODOO_DB: str = ""
    ODOO_USER: str = ""
    ODOO_PASSWORD: str = ""
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    DATABASE_URL: str = ""
    USE_KEY_VAULT: bool = False
    KEY_VAULT_NAME: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    return Settings()