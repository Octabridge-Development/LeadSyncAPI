import azure.functions as func
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Importar la app después del logging
try:
    from app.main import app

    # Crear Function App
    app_func = func.AsgiFunctionApp(
        app=app,
        http_auth_level=func.AuthLevel.ANONYMOUS
    )

    logging.info("Azure Function App initialized successfully")

except Exception as e:
    logging.error(f"Error initializing Function App: {str(e)}")
    raise