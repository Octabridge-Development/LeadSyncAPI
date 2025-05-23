# Este archivo configura la sesión de SQLAlchemy para interactuar con la base de datos.
# Proporciona la clase SessionLocal para manejar conexiones.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app.core.config import get_settings

# Crear el motor de SQLAlchemy
engine = create_engine(get_settings().DATABASE_URL, pool_pre_ping=True)

# Crear una fábrica de sesiones
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db():
    """
    Dependencia para obtener una sesión de base de datos.
    Cierra la sesión automáticamente después de su uso.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()