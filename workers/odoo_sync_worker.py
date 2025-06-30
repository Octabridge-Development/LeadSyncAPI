"""
odoo_sync_worker.py
-------------------
Worker para sincronizar contactos pendientes desde Azure SQL a Odoo.
Busca contactos con odoo_sync_status = 'pending', los sincroniza con Odoo y actualiza el estado a 'success' o 'error'.
"""
import os
import time
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy import or_
from app.db.models import Contact
from app.services.odoo_service import OdooService
from app.db.session import Base

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("odoo_sync_worker")

# Configuración de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL no está definido en el entorno.")
    raise RuntimeError("DATABASE_URL no está definido en el entorno.")
logger.info(f"DATABASE_URL: {DATABASE_URL}")
try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # Probar conexión
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("Conexión a la base de datos exitosa.")
except Exception as e:
    logger.error(f"Error al conectar a la base de datos: {e}")
    raise

# Configuración de Odoo
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")
logger.info(f"ODOO_URL: {ODOO_URL}, ODOO_DB: {ODOO_DB}, ODOO_USERNAME: {ODOO_USERNAME}")
if not all([ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD]):
    logger.error("Faltan variables de entorno para Odoo.")
    raise RuntimeError("Faltan variables de entorno para Odoo.")
odoo_service = OdooService(ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)

SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", 10))  # segundos entre ciclos
logger.info(f"SYNC_INTERVAL: {SYNC_INTERVAL} segundos")


def sync_pending_contacts():
    session = SessionLocal()
    success_count = 0
    error_count = 0
    updated_count = 0
    try:
        # Procesar contactos con estado 'pending' o 'error'
        pending_contacts = session.query(Contact).filter(
            or_(Contact.odoo_sync_status == "pending", Contact.odoo_sync_status == "error")
        ).all()
        logger.info(f"Contactos pendientes de sincronizar: {len(pending_contacts)}")
        if not pending_contacts:
            logger.info("No hay contactos pendientes de sincronizar.")
        for contact in pending_contacts:
            try:
                logger.info(f"Sincronizando contacto ID {contact.id} (manychat_id={contact.manychat_id}) a Odoo...")
                odoo_id = odoo_service.create_or_update_odoo_contact(contact)
                # Verificar si fue update o create
                if contact.odoo_contact_id and str(contact.odoo_contact_id) == str(odoo_id):
                    contact.odoo_sync_status = "updated"
                    updated_count += 1
                    logger.info(f"Contacto ID {contact.id} actualizado en Odoo (odoo_id={odoo_id})")
                else:
                    contact.odoo_contact_id = odoo_id
                    contact.odoo_sync_status = "success"
                    success_count += 1
                    logger.info(f"Contacto ID {contact.id} creado en Odoo (odoo_id={odoo_id})")
            except Exception as e:
                contact.odoo_sync_status = "error"
                error_count += 1
                logger.error(f"Error al sincronizar contacto ID {contact.id}: {e}")
            session.commit()
            time.sleep(1)  # Rate limit Odoo
        logger.info(f"Resumen ciclo: success={success_count}, updated={updated_count}, error={error_count}")
    except Exception as e:
        logger.error(f"Error general en sync_pending_contacts: {e}")
    finally:
        session.close()


def main():
    logger.info("Iniciando worker de sincronización Odoo → Contactos...")
    while True:
        sync_pending_contacts()
        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    main()
