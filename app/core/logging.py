import logging
import sys
import os

# Lee el nivel de log y formato desde variables de entorno
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()  # Nivel de log: DEBUG, INFO, WARNING, etc.
LOG_FORMAT = os.getenv("LOG_FORMAT", "plain")  # Formato: 'plain' o 'json'

# Formateador personalizado para logs en formato JSON
class JsonFormatter(logging.Formatter):
    def format(self, record):
        import json
        log_record = {
            'level': record.levelname,
            'time': self.formatTime(record, self.datefmt),
            'name': record.name,
            'message': record.getMessage(),
        }
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_record)

# Configura el logging global de la aplicación
# Llama a esta función al inicio para que todos los logs usen este formato
def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    if LOG_FORMAT == "json":
        formatter = JsonFormatter()  # Usa formato JSON
    else:
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(name)s: %(message)s')  # Formato plano
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    root.handlers = [handler]

# Inicializa el logging al importar el módulo
setup_logging()