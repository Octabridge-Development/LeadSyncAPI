# app/db/base.py

# Este archivo sirve como un punto central para asegurar que todos los modelos
# de SQLAlchemy sean conocidos por la metadata antes de crear las tablas.

# Importa la Base de tu sesión
from app.db.session import Base

# Importa el módulo de modelos completo.
# Esto asegura que todas las clases de modelos (Address, Contact, etc.)
# se carguen y, al heredar de Base, se registren con Base.metadata.
# NO necesitas importar cada modelo individualmente aquí.
from app.db import models # <--- ESTE ES EL CAMBIO CLAVE

# Las siguientes líneas han sido comentadas/eliminadas ya que el import del módulo completo es suficiente
# from app.db.models import (
#     Address,
#     Advisor,
#     Campaign,
#     CampaignContact,
#     Channel,
#     Client,
#     ClientDetail,
#     Contact,
#     ContactState,
#     Lead,
#     LeadDetail,
#     OrderProduct,
#     Product,
#     ProductInteraction,
#     SyncLog
# )