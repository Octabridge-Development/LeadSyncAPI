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
        Crea o actualiza un contacto en Odoo basado en los datos del objeto Contact de tu DB.
        Retorna el ID del contacto en Odoo (como string).
        """
        try:
            # Mapeo de campos de tu modelo Contact a los de Odoo (res.partner)
            odoo_vals = {
                'name': f"{contact_db_obj.first_name or ''} {contact_db_obj.last_name or ''}".strip(),
                'email': contact_db_obj.email, # Este campo vendrá de ManyChat si lo mapeas en tu schema Pydantic
                'phone': contact_db_obj.phone, # Número de WhatsApp/Teléfono
                'x_manychat_id': contact_db_obj.manychat_id, # Campo personalizado en Odoo, ¡fundamental!
                'type': 'contact',
                # Agrega aquí cualquier otro mapeo de campo personalizado necesario
                # Por ejemplo, si tienes un campo 'x_canal_entrada' en Odoo para 'canal_entrada'
                # 'x_canal_entrada': contact_db_obj.channel.name if contact_db_obj.channel else None,
                # Considera si quieres mapear el 'initial_state' de ManyChat o 'ultimo_estado' de ContactState
                # 'x_manychat_initial_state': contact_db_obj.initial_state,
            }
            # Limpiar valores None y strings vacíos para evitar enviar datos no deseados a Odoo
            odoo_vals = {k: v for k, v in odoo_vals.items() if v is not None and v != ''}

            partner_id = None

            # 1. Prioridad: Buscar por odoo_contact_id si ya lo tenemos guardado
            if contact_db_obj.odoo_contact_id:
                try:
                    # OdooRPC search devuelve una lista de IDs
                    partner_ids_by_odoo_id = self.execute(
                        'res.partner', 'search', [('id', '=', int(contact_db_obj.odoo_contact_id))]
                    )
                    if partner_ids_by_odoo_id:
                        partner_id = partner_ids_by_odoo_id[0]
                        logger.info(f"Contacto existente en Odoo encontrado por odoo_contact_id: {partner_id}")
                except ValueError:
                    logger.warning(f"odoo_contact_id '{contact_db_obj.odoo_contact_id}' no es un entero válido para búsqueda por ID.")
                except RPCError as e:
                    logger.warning(f"RPCError al buscar por odoo_contact_id {contact_db_obj.odoo_contact_id}: {e}", exc_info=True)

            # 2. Segunda Prioridad: Buscar por x_manychat_id (campo personalizado en Odoo)
            if not partner_id and odoo_vals.get('x_manychat_id'):
                partner_ids_by_manychat = self.execute(
                    'res.partner', 'search', [('x_manychat_id', '=', odoo_vals['x_manychat_id'])]
                )
                if partner_ids_by_manychat:
                    partner_id = partner_ids_by_manychat[0]
                    logger.info(f"Contacto existente en Odoo encontrado por x_manychat_id: {partner_id}")

            # 3. Tercera Prioridad: Buscar por Email y/o Phone (si no se encontró por IDs únicos)
            if not partner_id:
                search_domain = []
                if odoo_vals.get('email'):
                    search_domain.append(('email', '=', odoo_vals['email']))
                if odoo_vals.get('phone'):
                    search_domain.append(('phone', '=', odoo_vals['phone']))
                
                if search_domain: # Solo buscar si hay email o phone
                    if len(search_domain) > 1: # Si hay ambos, usar OR
                        search_domain = ['|'] + search_domain
                    
                    partner_ids_by_attrs = self.execute(
                        'res.partner', 'search', search_domain
                    )
                    if partner_ids_by_attrs:
                        partner_id = partner_ids_by_attrs[0]
                        logger.info(f"Contacto existente en Odoo encontrado por email/phone: {partner_id}")

            if partner_id:
                # Actualizar el contacto existente
                self.execute(
                    'res.partner', 'write', [partner_id], odoo_vals
                )
                logger.info(f"Contacto Odoo {partner_id} actualizado exitosamente.")
            else:
                # Si no se encontró, crear un nuevo contacto
                logger.info("Creando nuevo contacto en Odoo.")
                partner_id = self.execute(
                    'res.partner', 'create', odoo_vals
                )
                logger.info(f"Nuevo contacto Odoo creado con ID: {partner_id}")

            return str(partner_id) # Retornar como string para consistencia con odoo_contact_id en DB

        except RPCError as e:
            logger.error(f"Error OdooRPC al crear/actualizar contacto: {str(e)}", exc_info=True)
            raise OdooRateLimitError(f"Error Odoo RPC: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error inesperado al crear/actualizar contacto en Odoo: {str(e)}", exc_info=True)
            raise OdooRateLimitError(f"Error inesperado al sincronizar con Odoo: {str(e)}") from e

    def create_or_update_contact(self, contact):
        """
        Sincroniza un contacto con Odoo. Crea o actualiza según el manychat_id.
        """
        partner_model = self.client.env['res.partner']
        # Buscar contacto existente por el campo personalizado de ManyChat
        existing = partner_model.search([('x_studio_manychatid_customer', '=', contact.manychat_id)])
        vals = {
            'name': f"{contact.first_name or ''} {contact.last_name or ''}".strip(),
            'email': contact.email,
            'phone': contact.phone,
            'x_studio_manychatid_customer': contact.manychat_id,
            # Agrega aquí otros campos relevantes si es necesario
        }
        if existing:
            partner_model.write(existing, vals)
            return existing[0]
        else:
            new_id = partner_model.create(vals)
            return new_id

# Instancia singleton para reutilizar la conexión
from app.core.config import get_settings
settings = get_settings()
odoo_service = OdooService(
    url=str(settings.ODOO_URL),
    db=settings.ODOO_DB,
    username=settings.ODOO_USERNAME,
    password=settings.ODOO_PASSWORD
)