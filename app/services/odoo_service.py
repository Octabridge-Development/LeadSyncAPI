from odoorpc import ODOO
from odoorpc.error import RPCError
from tenacity import retry, wait_exponential, stop_after_attempt, before_sleep_log
import time
import logging
from typing import Any, Optional, Dict
from app.core.config import get_settings
from app.core.logging import logger
from app.db.models import Contact # <--- **IMPORTA TU MODELO CONTACT**

class OdooRateLimitError(Exception):
    """Excepción personalizada para rate limiting y errores de Odoo."""
    pass

class OdooService:
    def __init__(self, url, db, username, password):
        self._client: Optional[ODOO] = None
        self.last_request_time: float = 0
        self.rate_limit_delay = 1  # Puedes ajustar esto según tu config/env
        self.url = url
        self.db = db
        self.username = username
        self.password = password

    @property
    def client(self) -> ODOO:
        if not self._client:
            self._connect()
        return self._client

    def _connect(self):
        protocol = 'jsonrpc+ssl' if self.url.startswith('https') else 'jsonrpc'
        import urllib.parse
        parsed = urllib.parse.urlparse(self.url)
        host = parsed.hostname
        port = parsed.port or (443 if protocol == 'jsonrpc+ssl' else 8069)
        try:
            self._client = ODOO(
                host=host,
                protocol=protocol,
                port=port,
                version='18.0'  # Ajusta la versión según tu Odoo
            )
            self._client.login(
                db=self.db,
                login=self.username,
                password=self.password
            )
            logger.info(f"Conexión exitosa con Odoo en {host}")
        except RPCError as e:
            logger.error(f"Error de conexión con Odoo: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error inesperado al conectar con Odoo: {str(e)}", exc_info=True)
            raise

    def _enforce_rate_limit(self):
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
            logger.error(f"Error OdooRPC al ejecutar {model}.{method}: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error inesperado al ejecutar {model}.{method}: {str(e)}", exc_info=True)
            raise OdooRateLimitError("Error en comunicación con Odoo") from e

    def create_or_update_odoo_contact(self, contact_db_obj: Contact) -> str: # <--- **NUEVO MÉTODO**
        """
        Crea o actualiza un contacto en Odoo basado en el manychatID (x_studio_manychatid_customer).
        Si existe, actualiza el teléfono/celular; si no, crea el contacto.
        """
        try:
            odoo_vals = {
                'name': f"{contact_db_obj.first_name or ''} {contact_db_obj.last_name or ''}".strip(),
                'email': contact_db_obj.email,
                'phone': contact_db_obj.phone,
                'x_studio_manychatid_customer': contact_db_obj.manychat_id,
                'type': 'contact',
            }
            odoo_vals = {k: v for k, v in odoo_vals.items() if v is not None and v != ''}

            partner_id = None

            # Buscar por manychatID personalizado de Odoo
            if contact_db_obj.manychat_id:
                partner_ids = self.execute(
                    'res.partner', 'search', [('x_studio_manychatid_customer', '=', contact_db_obj.manychat_id)]
                )
                if partner_ids:
                    partner_id = partner_ids[0]
                    logger.info(f"Contacto existente en Odoo encontrado por x_studio_manychatid_customer: {partner_id}")

            if partner_id:
                # Solo actualizar teléfono/celular y otros datos relevantes
                self.execute(
                    'res.partner', 'write', [partner_id], odoo_vals
                )
                logger.info(f"Contacto Odoo {partner_id} actualizado exitosamente (teléfono/celular y datos relevantes).")
            else:
                logger.info("Creando nuevo contacto en Odoo.")
                partner_id = self.execute(
                    'res.partner', 'create', odoo_vals
                )
                logger.info(f"Nuevo contacto Odoo creado con ID: {partner_id}")

            return str(partner_id)

        except RPCError as e:
            logger.error(f"Error OdooRPC al crear/actualizar contacto: {str(e)}", exc_info=True)
            raise OdooRateLimitError(f"Error Odoo RPC: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error inesperado al crear/actualizar contacto en Odoo: {str(e)}", exc_info=True)
            raise OdooRateLimitError(f"Error inesperado al sincronizar con Odoo: {str(e)}") from e

# Instancia singleton para reutilizar la conexión
from app.core.config import get_settings
settings = get_settings()
odoo_service = OdooService(
    url=str(settings.ODOO_URL),
    db=settings.ODOO_DB,
    username=settings.ODOO_USERNAME,
    password=settings.ODOO_PASSWORD
)