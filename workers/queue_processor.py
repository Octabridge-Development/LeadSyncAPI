import asyncio
import json
from sqlalchemy.orm import Session
from typing import Optional

# Importar los servicios y esquemas que utilizará el worker
from app.services.queue_service import QueueService 
from app.services.azure_sql_service import AzureSQLService
from app.services.odoo_service import OdooService, OdooRateLimitError # Importa OdooRateLimitError
from app.schemas.manychat import ManyChatContactEvent, ManyChatCampaignAssignmentEvent
from app.db.models import Contact # Necesario para interactuar con el modelo Contact directamente
from app.core.logging import logger
from app.db.session import get_db_session_worker # Para obtener una sesión de DB para el worker

# Instancias de servicio globales (o singleton si tu diseño lo prefiere).
# En un entorno de Azure Functions "serverless" (disparadas por cola),
# estas instancias se crearán por cada invocación de la función, lo cual es normal.
azure_sql_service_instance = AzureSQLService()
odoo_service_instance = OdooService()

async def process_manychat_contact_message(message_body: str):
    """
    Procesa un mensaje de contacto de ManyChat de la cola.
    Flujo:
    1. Decodifica el mensaje a un evento ManyChatContactEvent.
    2. Guarda/Actualiza el contacto en Azure SQL (a través de AzureSQLService).
    3. Recupera el objeto Contact persistente de Azure SQL.
    4. Sincroniza el contacto con Odoo (a través de OdooService), si no está ya sincronizado.
    5. Actualiza el estado de sincronización en Azure SQL.
    """
    db_session: Optional[Session] = None
    db_session_gen = None # Inicializar a None para el bloque finally

    try:
        # 1. Decodificar el mensaje JSON a un objeto Pydantic
        event_data_dict = json.loads(message_body)
        manychat_event = ManyChatContactEvent(**event_data_dict)

        logger.info(f"Worker: Procesando mensaje de contacto para ManyChat ID: {manychat_event.manychat_id}")

        # 2. Guardar/Actualizar el contacto en Azure SQL
        # La función `process_contact_event` de AzureSQLService ya maneja
        # la apertura/cierre de su propia sesión DB y realiza el upsert.
        # No necesitamos el retorno directo aquí para el siguiente paso,
        # ya que recuperaremos el objeto de DB en la misma sesión del worker.
        await azure_sql_service_instance.process_contact_event(manychat_event)
        
        # 3. Recuperar el objeto Contact persistente de Azure SQL
        # Es crucial que el objeto 'Contact' que se pasa a OdooService.create_or_update_odoo_contact
        # sea una instancia persistente de SQLAlchemy, no solo el Pydantic ManyChatContactEvent.
        # Por eso, lo recuperamos explícitamente dentro de la sesión del worker.
        
        # Abrir una sesión de DB para este worker (si se necesita acceso directo a la DB)
        db_session_gen = get_db_session_worker()
        db_session = next(db_session_gen)
        
        # Instanciar el repositorio de Contacto usando la sesión del worker
        contact_repo_for_worker = ContactRepository(db_session)
        
        # Recuperar el contacto recién creado/actualizado para asegurar que tenemos la última versión,
        # incluyendo el ID de la DB y el estado de sincronización.
        manychat_contact_db = contact_repo_for_worker.get_by_manychat_id(manychat_event.manychat_id)
        
        if not manychat_contact_db:
            logger.error(f"Worker: Contacto con manychat_id {manychat_event.manychat_id} no encontrado en Azure SQL después del procesamiento inicial. No se puede sincronizar con Odoo.")
            return # Salir si no se puede recuperar el contacto

        logger.info(f"Worker: Contacto ManyChat ID {manychat_contact_db.manychat_id} guardado/actualizado en Azure SQL. Estado de sincronización actual: {manychat_contact_db.odoo_sync_status}")

        # 4. Sincronizar con Odoo si el estado no es ya 'synced' o si hubo un error previo
        # Esto permite reintentar sincronizaciones fallidas si el estado es 'error' o 'pending'.
        if manychat_contact_db.odoo_sync_status != 'synced':
            try:
                # Sincronizar con Odoo
                odoo_partner_id_str = odoo_service_instance.create_or_update_odoo_contact(manychat_contact_db)
                
                # 5. Actualizar el estado de sincronización en Azure SQL
                azure_sql_service_instance.update_odoo_sync_status(
                    manychat_contact_db.manychat_id, 'synced', odoo_partner_id_str
                )
                logger.info(f"Worker: Contacto ManyChat ID {manychat_contact_db.manychat_id} sincronizado a Odoo con Partner ID {odoo_partner_id_str}.")
            except (OdooRateLimitError, RPCError) as e:
                # Captura errores específicos de Odoo o de RPC para reintentos o manejo específico
                logger.error(f"Worker: Error (Odoo Service) al sincronizar contacto {manychat_event.manychat_id} con Odoo: {e}", exc_info=True)
                azure_sql_service_instance.update_odoo_sync_status(
                    manychat_contact_db.manychat_id, 'error' # Marca como error para posible reintento manual o automático
                )
            except Exception as e:
                # Captura cualquier otro error inesperado durante la sincronización con Odoo
                logger.error(f"Worker: Error inesperado al sincronizar contacto {manychat_event.manychat_id} con Odoo: {e}", exc_info=True)
                azure_sql_service_instance.update_odoo_sync_status(
                    manychat_contact_db.manychat_id, 'error'
                )
        else:
            logger.info(f"Worker: Contacto ManyChat ID {manychat_contact_db.manychat_id} ya marcado como 'synced' en Azure SQL. Omitiendo sincronización con Odoo.")

    except json.JSONDecodeError as e:
        logger.error(f"Worker: Error al decodificar JSON del mensaje de la cola: {e}")
    except Exception as e:
        logger.critical(f"Worker: Error crítico general al procesar mensaje de contacto: {e}", exc_info=True)
    finally:
        # Asegurarse de cerrar la sesión de DB del worker si se abrió
        if db_session_gen: # Si el generador fue creado
            try:
                # Intentar avanzar el generador una vez más para ejecutar el bloque `finally`
                next(db_session_gen) 
            except StopIteration:
                pass # Es normal que el generador termine aquí
        if db_session: # Asegurarse de cerrar la sesión subyacente si se obtuvo
            db_session.close()


async def process_manychat_campaign_message(message_body: str):
    """
    Procesa un mensaje de asignación de campaña de ManyChat de la cola
    y lo guarda en Azure SQL (sin sincronizar con Odoo directamente).
    """
    try:
        event_data_dict = json.loads(message_body)
        manychat_campaign_event = ManyChatCampaignAssignmentEvent(**event_data_dict)

        logger.info(f"Worker: Procesando evento de campaña ManyChat ID: {manychat_campaign_event.manychat_id}, Campaña: {manychat_campaign_event.campaign_id}")

        # El AzureSQLService maneja la interacción con la DB internamente para campañas.
        await azure_sql_service_instance.process_campaign_event(manychat_campaign_event)

        logger.info(f"Worker: Evento de campaña ManyChat ID {manychat_campaign_event.manychat_id} procesado y guardado en Azure SQL.")

    except json.JSONDecodeError as e:
        logger.error(f"Worker: Error al decodificar JSON del mensaje de la cola de campaña: {e}")
    except Exception as e:
        logger.critical(f"Worker: Error crítico general al procesar mensaje de campaña: {e}", exc_info=True)
    finally:
        # No hay una sesión de DB explícitamente abierta aquí en el worker para cerrar,
        # ya que AzureSQLService.process_campaign_event utiliza get_db_session() internamente.
        pass

# Funciones para iniciar los consumidores (útil si los ejecutas como scripts o en un entorno de fondo)
async def start_manychat_contact_worker():
    """
    Función principal para iniciar el consumidor de mensajes de la cola de contactos de ManyChat.
    """
    queue_service = QueueService() # La instancia debe estar configurada (ej. con AZURE_STORAGE_CONNECTION_STRING)
    # Asegúrate que el nombre de la cola esté configurado en QueueService o aquí
    queue_service.contact_queue_name = "manychat-contact-queue" 

    logger.info(f"Iniciando consumidor de cola ManyChat Contact: {queue_service.contact_queue_name}")
    try:
        await queue_service.receive_messages(
            queue_name=queue_service.contact_queue_name,
            message_handler=process_manychat_contact_message
        )
    except Exception as e:
        logger.critical(f"Fallo en el inicio del consumidor de ManyChat Contact: {e}", exc_info=True)

async def start_manychat_campaign_worker():
    """
    Función principal para iniciar el consumidor de mensajes de la cola de campañas de ManyChat.
    """
    queue_service = QueueService()
    # Asegúrate que el nombre de la cola esté configurado en QueueService o aquí
    queue_service.campaign_queue_name = "manychat-campaign-queue" 

    logger.info(f"Iniciando consumidor de cola ManyChat Campaign: {queue_service.campaign_queue_name}")
    try:
        await queue_service.receive_messages(
            queue_name=queue_service.campaign_queue_name,
            message_handler=process_manychat_campaign_message
        )
    except Exception as e:
        logger.critical(f"Fallo en el inicio del consumidor de ManyChat Campaign: {e}", exc_info=True)