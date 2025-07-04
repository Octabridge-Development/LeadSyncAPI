# app/core/logging.py
import logging
import sys
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
from opencensus.ext.azure.log_exporter import AzureLogHandler
from app.core.config import get_settings # <-- IMPORTANTE: Se importa la configuración

# 1. Obtenemos la configuración centralizada
settings = get_settings()

# 2. Usamos las variables desde el objeto de settings
LOG_LEVEL = settings.LOG_LEVEL.upper()
LOG_FORMAT = settings.LOG_FORMAT

# Configuración de structlog para logging estructurado
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(LOG_LEVEL)),
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Middleware para correlación de requests
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        structlog.contextvars.clear_contextvars()
        return response

# Inicializa logging estándar para compatibilidad
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=LOG_LEVEL,
)

logger = structlog.get_logger()

# 3. La configuración de Azure Insights también usa el objeto settings
if settings.APPINSIGHTS_INSTRUMENTATION_KEY:
    handler = AzureLogHandler(
        connection_string=f'InstrumentationKey={settings.APPINSIGHTS_INSTRUMENTATION_KEY}'
    )
    logging.getLogger().addHandler(handler)
    logger.info("✅ Logging para Application Insights configurado desde la configuración central.")