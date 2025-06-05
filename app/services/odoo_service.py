from odoorpc import ODOO
from odoorpc.error import RPCError
from tenacity import retry, wait_exponential, stop_after_attempt, before_sleep_log
import time
import logging
from typing import Any, Optional
from app.core.config import get_settings
from app.core.logging import logger

class OdooRateLimitError(Exception):
    """Excepción personalizada para rate limiting y errores de Odoo."""
    pass

class OdooService:
    def __init__(self):
        self._client: Optional[ODOO] = None
        self.last_request_time: float = 0
        self.rate_limit_delay = get_settings().ODOO_RATE_LIMIT

    @property
    def client(self) -> ODOO:
        if not self._client:
            self._connect()
        return self._client

    def _connect(self):
        settings = get_settings()
        # OdooRPC solo acepta 'jsonrpc' o 'jsonrpc+ssl' como protocolo
        protocol = 'jsonrpc+ssl' if settings.ODOO_URL.scheme == 'https' else 'jsonrpc'
        try:
            self._client = ODOO(
                host=settings.ODOO_URL.host,
                protocol=protocol,
                port=settings.ODOO_URL.port or 443,
                version='18.0'
            )
            self._client.login(
                db=settings.ODOO_DB,
                login=settings.ODOO_USERNAME,
                password=settings.ODOO_PASSWORD
            )
            logger.info(f"Conexión exitosa con Odoo 18 en {settings.ODOO_URL.host}")
        except RPCError as e:
            logger.error(f"Error de conexión con Odoo: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al conectar con Odoo: {str(e)}")
            raise

    def _enforce_rate_limit(self):
        # Aplica un delay para cumplir con el rate limit configurado
        elapsed = time.perf_counter() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.perf_counter()

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """
        Ejecuta un método sobre un modelo de Odoo con rate limiting y retry.
        """
        try:
            self._enforce_rate_limit()
            return self.client.execute(model, method, *args, **kwargs)
        except RPCError as e:
            logger.error(f"Error OdooRPC: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")
            raise OdooRateLimitError("Error en comunicación con Odoo") from e

# Instancia singleton para reutilizar la conexión
odoo_service = OdooService()