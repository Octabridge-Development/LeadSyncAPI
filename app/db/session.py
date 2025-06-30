from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from contextlib import contextmanager
from app.core.config import get_settings
from typing import Generator

# --- 1. Base Declarativa para Modelos SQLAlchemy ---
# Todos tus modelos de base de datos (tablas) deben heredar de 'Base'.
# Ejemplo: class Contact(Base): __tablename__ = "Contacts"
Base = declarative_base()

# --- 2. Configuración del Motor de SQLAlchemy ---
# El 'engine' es el punto de conexión real a tu base de datos.
# Configuraciones del pool de conexiones para mejor rendimiento y estabilidad:
settings = get_settings() # Obtiene la instancia de configuración

# Determina si es una base de datos SQLite en memoria
# Esto es CRÍTICO para los tests.
is_sqlite_in_memory = settings.DATABASE_URL == "sqlite:///:memory:"

# Argumentos base para create_engine
engine_args = {
    "url": settings.DATABASE_URL,
    "echo": settings.DEBUG,
}

# Añade condicionalmente los argumentos de pool si NO es SQLite en memoria
if not is_sqlite_in_memory:
    engine_args.update({
        "pool_size": 20,
        "max_overflow": 0, # No permite conexiones adicionales más allá de pool_size
        "pool_recycle": 3600, # Recicla (cierra y reabre) conexiones cada 3600 segundos (1 hora)
                              # Esto previene problemas de timeout con la base de datos.
    })

# Configura connect_args.
connect_args = {
    "timeout": 30, # Tiempo de espera para establecer una conexión
}

# 'prepared_statement_cache_size' es específico de ciertos dialectos (como SQL Server)
# y puede causar TypeError con SQLite.
if not is_sqlite_in_memory:
    connect_args["prepared_statement_cache_size"] = 0

# Para SQLite, 'check_same_thread=False' es a menudo necesario para multithreading con FastAPI
if is_sqlite_in_memory:
    connect_args["check_same_thread"] = False

engine_args["connect_args"] = connect_args

# Crea el motor con los argumentos preparados
engine = create_engine(**engine_args)


# --- 3. Configuración del Constructor de Sesiones ---
# 'SessionLocal' es una "fábrica" que crea nuevas sesiones de base de datos.
# autocommit=False: Debes hacer commit explícitamente para guardar los cambios.
# autoflush=False: Los objetos no se "flushean" automáticamente a la base de datos antes de un commit.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 4. Context Manager para Sesiones de Base de Datos (Recomendado) ---
# Usa esta función con la sentencia 'with' para garantizar que la sesión se abra
# y cierre correctamente, incluso si ocurren errores.
@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Proporciona una sesión de base de datos y la cierra automáticamente al finalizar.
    Asegura que se realice un rollback si ocurre alguna excepción y luego re-lanza la excepción.
    Uso: with get_db_session() as db: ...
    """
    db = SessionLocal()
    try:
        yield db  # Proporciona la sesión para que se use
    except Exception:
        db.rollback() # Si hay un error, deshace cualquier cambio pendiente
        raise        # Re-lanza la excepción original
    finally:
        db.close()  # Siempre cierra la sesión, liberando la conexión al pool

# --- 5. Función de Utilidad para Frameworks (e.g., FastAPI) ---
# Esta función es ideal para usarla como una "dependencia" en frameworks web.
def get_db() -> Generator[Session, None, None]:
    """
    Proporciona una sesión de base de datos para dependencias de frameworks (como FastAPI).
    La sesión se cierra automáticamente después de que el endpoint ha sido procesado.
    Uso (en FastAPI): db: Session = Depends(get_db)
    """
    with get_db_session() as db:
        yield db

# --- 6. Función específica para Workers ---
# Esta función es para ser usada explícitamente por tus workers asíncronos.
def get_db_session_worker() -> Generator[Session, None, None]: # <--- FUNCIÓN AÑADIDA
    """
    Proporciona una sesión de base de datos para los procesos de worker.
    Reutiliza get_db_session para asegurar el manejo transaccional adecuado.
    """
    with get_db_session() as db:
        yield db

# --- 7. Función para Verificar la Conexión a la Base de Datos ---
# Útil para comprobar si tu aplicación puede conectarse al inicio.
def check_database_connection():
    """
    Verifica la conexión a la base de datos ejecutando una consulta simple.
    Imprime el estado de la conexión.
    """
    print("\n🔄 Intentando conectar a la base de datos...")
    try:
        with engine.connect() as connection:
            # Ejecuta una consulta simple para probar la conexión
            result = connection.execute(text("SELECT 1 AS test_connection"))
            print(f"✅ ¡Conexión exitosa! Resultado: {result.fetchone().test_connection}")
            return True
    except Exception as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        # Considera usar un sistema de logging aquí para errores en producción
        return False
    finally:
        print("🔚 Intento de conexión finalizado.")

# --- Ejemplo de Uso (Solo para probar el archivo directamente) ---
if __name__ == "__main__":
    # 1. Comprobar la conexión al inicio
    if check_database_connection():
        print("\nLa aplicación puede comunicarse con la base de datos.")
    else:
        print("\n¡ADVERTENCIA! No se pudo conectar a la base de datos.")

    # 2. Ejemplo de cómo usar 'get_db_session' (la forma recomendada para la mayoría de las operaciones)
    print("\n--- Demostración de 'get_db_session' ---")
    try:
        with get_db_session() as db_session:
            print("Sesión de base de datos obtenida con éxito (get_db_session).")
            # Aquí harías tus operaciones con la base de datos, por ejemplo:
            # result = db_session.execute(text("SELECT GETDATE() AS CurrentDateTime"))
            # print(f"Fecha y hora actual de la DB: {result.scalar()}")
            print("Simulando una operación dentro de la sesión...")
            # Si se necesita un commit explícito después de cambios (INSERT, UPDATE, DELETE):
            # db_session.commit()
        print("Sesión cerrada automáticamente (gracias al 'with' y 'finally').")
    except Exception as e:
        print(f"Ocurrió un error al usar get_db_session: {e}")

    # 3. Ejemplo de cómo usar 'get_db' (típicamente en un framework web como FastAPI)
    print("\n--- Demostración de 'get_db' (como dependencia de FastAPI) ---")
    db_generator = get_db()
    try:
        # En FastAPI, el framework llama a next(db_generator) para obtener la sesión
        db_for_fastapi = next(db_generator)
        print("Sesión de base de datos obtenida para FastAPI (get_db).")
        # Aquí usarías 'db_for_fastapi' en tu endpoint de FastAPI
        print("Simulando una operación en un endpoint de FastAPI...")
    finally:
        # FastAPI se encarga de llamar a next(db_generator) de nuevo para cerrar la sesión
        try:
            next(db_generator) # Esto ejecuta el bloque 'finally' de get_db
        except StopIteration:
            pass # Es normal que next() lance StopIteration al finalizar el generador
        print("Sesión de FastAPI cerrada automáticamente.")

    # --- CAMBIO ADICIONAL: Demostración de 'get_db_session_worker' ---
    # 4. Ejemplo de cómo usar 'get_db_session_worker' (para procesos de fondo o workers)
    print("\n--- Demostración de 'get_db_session_worker' ---")
    db_worker_generator = get_db_session_worker()
    try:
        db_for_worker = next(db_worker_generator)
        print("Sesión de base de datos obtenida para Worker (get_db_session_worker).")
        print("Simulando una operación en un Worker...")
    except Exception as e:
        print(f"Ocurrió un error al usar get_db_session_worker: {e}")
    finally:
        try:
            next(db_worker_generator) # Esto ejecuta el bloque 'finally' de get_db_session_worker
        except StopIteration:
            pass # Es normal que next() lance StopIteration al finalizar el generador
        print("Sesión de Worker cerrada automáticamente.")