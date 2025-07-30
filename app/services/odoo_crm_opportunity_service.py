# app/services/odoo_crm_opportunity_service.py

import xmlrpc.client
import asyncio
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from app.core.config import get_settings # Asume que tienes un módulo de configuración
from app.core.logging import logger # Asume que tienes un logger configurado

# Excepción personalizada para errores específicos de Odoo
class OdooServiceError(Exception):
    """Excepción para errores al interactuar con el servicio Odoo."""
    pass

# Manejo de reintentos con Tenacity para fallos de red o temporales
# Intentará 3 veces, esperando exponencialmente (2s, 4s, 8s) y registrando antes de cada reintento
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(
        (xmlrpc.client.Fault, ConnectionRefusedError, TimeoutError, asyncio.TimeoutError)
    ),
    before_sleep=before_sleep_log(logger, logger.warning)
)
class OdooCRMOpportunityService:
    async def get_opportunity_by_id(self, opportunity_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene una oportunidad por su ID en Odoo y muestra todos los campos relevantes, incluyendo el ManyChatID.
        """
        fields = ['id', 'name', 'stage_id', 'x_studio_manychatid_api', 'user_id', 'partner_id']
        try:
            result = await self._execute_odoo_call(
                'crm.lead', 'read', [opportunity_id], fields=fields
            )
            logger.info(f"Oportunidad Odoo por ID {opportunity_id}: {result}")
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error al obtener oportunidad Odoo por ID {opportunity_id}: {e}")
            return None
    def __init__(self):
        settings = get_settings()
        self.url = settings.ODOO_URL
        self.db = settings.ODOO_DB
        self.username = settings.ODOO_USERNAME
        self.password = settings.ODOO_PASSWORD

        # Validar que las credenciales Odoo estén presentes
        missing = []
        if not self.url:
            missing.append("ODOO_URL")
        if not self.db:
            missing.append("ODOO_DB")
        if not self.username:
            missing.append("ODOO_USERNAME")
        if not self.password:
            missing.append("ODOO_PASSWORD")
        if missing:
            raise RuntimeError(f"Faltan variables de entorno Odoo requeridas: {', '.join(missing)}. Este servicio solo debe usarse si la integración Odoo está configurada.")

        # Conexión XML-RPC para autenticación y llamadas comunes
        self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self.uid: Optional[int] = None # User ID, se obtiene en la autenticación

        # Conexión para operaciones de modelos (lectura/escritura)
        self.models: Optional[xmlrpc.client.ServerProxy] = None # Se inicializa después de la autenticación

        self.last_odoo_call_time: float = 0.0 # Para controlar la tasa de llamadas

    async def _authenticate(self) -> int:
        """Autentica con Odoo y guarda el UID."""
        if self.uid is None:
            logger.info("Autenticando con Odoo...")
            try:
                self.uid = self.common.authenticate(self.db, self.username, self.password, {})
                if not self.uid:
                    raise OdooServiceError("Fallo de autenticación con Odoo: UID no obtenido.")
                self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
                logger.info(f"Autenticación Odoo exitosa para usuario: {self.username}, UID: {self.uid}")
            except Exception as e:
                logger.error(f"Error durante la autenticación Odoo: {e}", exc_info=True)
                raise OdooServiceError(f"No se pudo autenticar con Odoo: {e}")
        return self.uid

    async def _execute_odoo_call(self, model: str, method: str, *args, **kwargs) -> Any:
        """
        Ejecuta una llamada a la API de Odoo, controlando la tasa de solicitudes.
        """
        await self._authenticate() # Asegurar autenticación antes de cada llamada
        
        # Control de tasa de llamadas (1 req/s)
        current_time = time.monotonic()
        time_since_last_call = current_time - self.last_odoo_call_time
        if time_since_last_call < 1.0: # Si la última llamada fue hace menos de 1 segundo
            sleep_time = 1.0 - time_since_last_call
            logger.debug(f"Odoo rate limit: Esperando {sleep_time:.2f}s antes de la próxima llamada.")
            await asyncio.sleep(sleep_time)
        self.last_odoo_call_time = time.monotonic() # Actualizar el tiempo de la última llamada

        if not self.models:
            raise OdooServiceError("Cliente de modelos Odoo no inicializado. ¿Fallo de autenticación?")

        logger.debug(f"Llamando a Odoo: model='{model}', method='{method}'")
        try:
            result = self.models.execute_kw(
                self.db, self.uid, self.password, model, method, args, kwargs
            )
            return result
        except xmlrpc.client.Fault as fault:
            logger.error(f"Fallo de Odoo RPC: {fault.faultCode} - {fault.faultString}", exc_info=True)
            raise OdooServiceError(f"Error de Odoo RPC: {fault.faultString}")
        except Exception as e:
            logger.error(f"Error inesperado en llamada a Odoo: {e}", exc_info=True)
            raise OdooServiceError(f"Error inesperado al comunicarse con Odoo: {e}")

    async def find_opportunity_by_manychat_id(self, manychat_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca una oportunidad en Odoo por el campo 'manychat_id' personalizado.
        Retorna la oportunidad completa o None si no la encuentra.
        """
        logger.info(f"Buscando oportunidad Odoo por ManyChat ID: {manychat_id}")
        # Asume que 'manychat_id' es un campo personalizado en el modelo 'crm.lead'
        # o que el external_id se usa de alguna forma.
        # En Odoo, esto se gestiona comúnmente con un campo custom x_manychat_id o similar.
        # Si no existe, tendrás que crearlo en Odoo en el modelo crm.lead.
        domain = [('x_studio_manychatid_api', '=', manychat_id)] # Usar el nombre real del campo en Odoo
        fields = ['id', 'name', 'stage_id', 'x_studio_manychatid_api', 'user_id', 'partner_id'] # Campos a obtener

        try:
            # Buscar una oportunidad. Limitamos a 1 ya que manychat_id debería ser único.
            opportunities = await self._execute_odoo_call(
                'crm.lead', 'search_read', domain, fields=fields, limit=1
            )
            logger.info(f"Resultado crudo de búsqueda Odoo por ManyChatID {manychat_id}: {opportunities}")
            if opportunities:
                logger.info(f"Oportunidad Odoo encontrada para ManyChat ID {manychat_id}: {opportunities[0]['id']}")
                return opportunities[0]
            logger.info(f"No se encontró oportunidad Odoo para ManyChat ID: {manychat_id}")
            return None
        except OdooServiceError as e:
            logger.error(f"Error al buscar oportunidad Odoo por ManyChat ID {manychat_id}: {e}")
            raise

    async def create_or_update_opportunity(
        self,
        manychat_id: str,
        contact_name: str,             # Nombre del contacto que será usado como nombre de la oportunidad
        stage_odoo_id: int,
        advisor_comercial_id: Optional[int] = None,  # ID del asesor comercial
        advisor_medico_id: Optional[int] = None,     # ID del asesor médico
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        source_id: Optional[int] = None,             # ID del canal de entrada
        channel_name: Optional[str] = None,          # Nombre del canal de entrada (instagram, tiktok, etc)
        fecha_entrada: Optional[datetime] = None,    # Fecha de entrada
        fecha_ultimo_estado: Optional[datetime] = None  # Fecha del último estado
    ) -> int:
        """
        Crea una nueva oportunidad en Odoo o actualiza una existente.
        Retorna el ID de la oportunidad en Odoo.
        """
        existing_opportunity = await self.find_opportunity_by_manychat_id(manychat_id)

        # Validar que contact_name sea un string y no un objeto Contact
        if contact_name is not None and not isinstance(contact_name, str):
            # Si es un objeto con first_name y last_name, construir el nombre completo
            if hasattr(contact_name, 'first_name') and hasattr(contact_name, 'last_name'):
                contact_name = f"{contact_name.first_name} {getattr(contact_name, 'last_name', '')}".strip()
            else:
                contact_name = str(contact_name)

        # Usar el nombre del canal si está disponible, si no, usar el ID (legacy)
        canal_entrada_value = channel_name if channel_name else source_id

        opportunity_data = {
            'name': contact_name,  # Usamos el nombre del contacto como nombre de la oportunidad
            'stage_id': stage_odoo_id,
            'x_studio_manychatid_api': manychat_id,
            'type': 'opportunity',
            'email_from': contact_email,
            'phone': contact_phone,
            'x_studio_fecha_entrada': fecha_entrada.strftime('%Y-%m-%d') if fecha_entrada else datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            'x_studio_ultimo_estado_fecha': fecha_ultimo_estado.strftime('%Y-%m-%d') if fecha_ultimo_estado else datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            'x_studio_asesor_medico': advisor_medico_id,
            'x_studio_asesor_comercial': advisor_comercial_id,
            'x_studio_canal_entrada': canal_entrada_value,  # Ahora puede ser el nombre del canal
        }
        # No asignar user_id/advisor
        # Eliminar claves con valor None para evitar errores de XML-RPC
        opportunity_data = {k: v for k, v in opportunity_data.items() if v is not None}

        if existing_opportunity:
            # Actualizar oportunidad existente
            opportunity_id = existing_opportunity['id']
            # No actualizar la fecha de entrada en updates
            opportunity_data.pop('x_studio_fecha_entrada', None)
            logger.info(f"Actualizando oportunidad Odoo {opportunity_id} para ManyChat ID: {manychat_id}")
            try:
                await self._execute_odoo_call(
                    'crm.lead', 'write', [opportunity_id], opportunity_data
                )
                logger.info(f"Oportunidad Odoo {opportunity_id} actualizada correctamente.")
                # Log de la oportunidad después de actualizar
                await self.get_opportunity_by_id(opportunity_id)
                return opportunity_id
            except OdooServiceError as e:
                logger.error(f"Error al actualizar oportunidad Odoo {opportunity_id}: {e}")
                raise
        else:
            # Crear nueva oportunidad
            logger.info(f"Creando nueva oportunidad Odoo para ManyChat ID: {manychat_id}")
            logger.info(f"Payload enviado a Odoo (crm.lead.create): {opportunity_data}")
            try:
                new_opportunity_id = await self._execute_odoo_call(
                    'crm.lead', 'create', opportunity_data
                )
                if not new_opportunity_id:
                    raise OdooServiceError(f"Odoo no devolvió ID al crear oportunidad para ManyChat ID {manychat_id}.")
                logger.info(f"Nueva oportunidad Odoo creada con ID: {new_opportunity_id} para ManyChat ID: {manychat_id}")
                # Log de la oportunidad recién creada
                await self.get_opportunity_by_id(new_opportunity_id)
                # Forzar update del campo ManyChatID tras la creación (workaround)
                try:
                    await self._execute_odoo_call(
                        'crm.lead', 'write', [new_opportunity_id], {'x_studio_manychatid_api': manychat_id}
                    )
                    logger.info(f"Campo ManyChatID actualizado por workaround en Odoo ID: {new_opportunity_id}")
                    # Log de la oportunidad después del workaround
                    await self.get_opportunity_by_id(new_opportunity_id)
                except Exception as e:
                    logger.warning(f"No se pudo forzar el update del campo ManyChatID en Odoo ID: {new_opportunity_id}: {e}")
                return new_opportunity_id
            except OdooServiceError as e:
                logger.error(f"Error al crear nueva oportunidad Odoo para ManyChat ID {manychat_id}: {e}")
                raise

    async def update_opportunity_stage(self, manychat_id: str, new_stage_odoo_id: int) -> bool:
        """
        Actualiza el stage de una oportunidad en Odoo.
        Retorna True si la actualización fue exitosa, False en caso contrario (ej. no encontrada).
        """
        opportunity = await self.find_opportunity_by_manychat_id(manychat_id)
        if not opportunity:
            logger.warning(f"No se encontró oportunidad Odoo con ManyChat ID {manychat_id} para actualizar stage.")
            return False
        
        opportunity_id = opportunity['id']
        current_stage_id = opportunity['stage_id'][0] if isinstance(opportunity['stage_id'], list) else opportunity['stage_id']

        if current_stage_id == new_stage_odoo_id:
            logger.info(f"Oportunidad {opportunity_id} ya está en el stage {new_stage_odoo_id}. No se requiere actualización.")
            return True

        logger.info(f"Actualizando stage de oportunidad Odoo {opportunity_id} a {new_stage_odoo_id} para ManyChat ID: {manychat_id}")
        try:
            await self._execute_odoo_call(
                'crm.lead', 'write', [opportunity_id], {'stage_id': new_stage_odoo_id}
            )
            logger.info(f"Stage de oportunidad {opportunity_id} actualizado exitosamente a {new_stage_odoo_id}.")
            return True
        except OdooServiceError as e:
            logger.error(f"Error al actualizar stage de oportunidad Odoo {opportunity_id}: {e}")
            raise


# Instancia global solo si Odoo está configurado correctamente
def get_odoo_crm_opportunity_service():
    try:
        return OdooCRMOpportunityService()
    except RuntimeError as e:
        logger.warning(f"OdooCRMOpportunityService no inicializado: {e}")
        return None

# Instancia global para importación directa
try:
    odoo_crm_opportunity_service = OdooCRMOpportunityService()
except RuntimeError as e:
    logger.warning(f"OdooCRMOpportunityService no inicializado: {e}")
    odoo_crm_opportunity_service = None