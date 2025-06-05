# Documentación del Proyecto MiaSalud Integration API

## Índice
1. [Visión General](#visión-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Estructura del Proyecto](#estructura-del-proyecto)
4. [Componentes Clave](#componentes-clave)
5. [Configuración del Entorno](#configuración-del-entorno)
6. [Guía de Desarrollo](#guía-de-desarrollo)
7. [Despliegue](#despliegue)
8. [Requirements](#requirements)
9. [Desarrollo con Docker](#desarrollo-con-docker)

## Visión General

MiaSalud Integration API es una solución escalable y robusta para integrar ManyChat (plataforma de chatbot) con Odoo 18 y Azure SQL, superando las limitaciones de soluciones anteriores (como el límite de 300 consultas/hora en Google Sheets). La aplicación utiliza FastAPI con Python 3.11 y está diseñada siguiendo mejores prácticas de arquitectura para garantizar escalabilidad, resiliencia y observabilidad.

### Objetivo Principal

Registrar en tiempo real cada interacción de los leads de ManyChat tanto en Odoo (modelos personalizados `manychat.contact` y `manychat.state`) como en Azure SQL, procesando más de 1000 eventos por hora.

## Arquitectura del Sistema

La arquitectura implementa un patrón de desacoplamiento basado en colas para manejar cargas variables manteniendo la estabilidad. El sistema sigue los siguientes principios:

### Flujo de Datos

1. **Recepción de eventos**: ManyChat envía eventos vía webhook HTTP a la API FastAPI.
2. **Desacoplamiento**: Los eventos se colocan en una cola de Azure Storage para procesamiento asíncrono.
3. **Procesamiento ordenado**: Un worker procesa los mensajes secuencialmente respetando límites de API.
4. **Persistencia dual**: Cada evento se registra tanto en Odoo (mediante JSON-RPC) como en Azure SQL.
5. **Manejo de errores**: Los mensajes con problemas se envían a una cola de letra muerta (DLQ) para análisis.

### Características Clave

- **Control de tasas**: Respeta el límite de 1 req/s de Odoo SaaS
- **Procesamiento resiliente**: Reintentos automáticos con backoff exponencial
- **Observabilidad integrada**: Logging estructurado y métricas
- **Idempotencia**: Previene duplicación de datos en caso de reintentos
- **Seguridad**: Manejo seguro de credenciales mediante Azure Key Vault (opcional)

## Estructura del Proyecto

```
miasalud-integration/
│
├── app/                            # Código principal de la aplicación
│   ├── api/                        # Definición de endpoints API
│   │   ├── __init__.py
│   │   ├── deps.py                 # Dependencias comunes para endpoints
│   │   └── v1/                     # Versión 1 de la API
│   │       ├── __init__.py
│   │       ├── router.py           # Router principal 
│   │       └── endpoints/          # Endpoints organizados por dominio
│   │           ├── __init__.py
│   │           ├── manychat.py     # Endpoints para webhooks de ManyChat
│   │           ├── odoo.py         # Endpoints para webhooks de Odoo
│   │           └── reports.py      # Endpoints para reportes
│   │
│   ├── core/                       # Configuración central de la aplicación
│   │   ├── __init__.py
│   │   ├── config.py               # Configuración centralizada
│   │   ├── security.py             # Funciones de autenticación
│   │   └── logging.py              # Configuración de logging
│   │
│   ├── db/                         # Capa de acceso a datos
│   │   ├── __init__.py
│   │   ├── models.py               # Modelos SQLAlchemy
│   │   ├── repositories.py         # Patrón repositorio para CRUD
│   │   └── session.py              # Configuración de conexión a BD
│   │
│   ├── services/                   # Servicios de negocio
│   │   ├── __init__.py
│   │   ├── azure_sql_service.py    # Servicios para Azure SQL
│   │   ├── manychat_service.py     # Servicios para ManyChat
│   │   ├── odoo_service.py         # Servicios para Odoo
│   │   └── queue_service.py        # Servicios para gestión de colas
│   │
│   ├── schemas/                    # Esquemas Pydantic 
│   │   ├── __init__.py
│   │   ├── common.py               # Esquemas compartidos
│   │   ├── manychat.py             # Esquemas para ManyChat
│   │   └── odoo.py                 # Esquemas para Odoo
│   │
│   ├── utils/                      # Utilidades generales
│   │   ├── __init__.py
│   │   ├── idempotency.py          # Funciones para garantizar idempotencia
│   │   ├── monitoring.py           # Configuración de monitoreo
│   │   └── retry.py                # Lógica de reintentos
│   │
│   └── main.py                     # Punto de entrada principal
│
├── azure_function/                 # Configuración para Azure Functions
│   ├── __init__.py
│   ├── function.json              # Configuración de la función
│   └── host.json                  # Configuración del host
│
├── tests/                          # Pruebas automatizadas
│   ├── __init__.py
│   ├── conftest.py                 # Configuración de pruebas
│   ├── test_api/                   # Pruebas de API
│   ├── test_services/              # Pruebas de servicios
│   └── test_workers/               # Pruebas de workers
│
├── workers/                        # Procesos de trabajo en segundo plano
│   ├── __init__.py
│   ├── queue_processor.py          # Procesador de cola principal
│   └── scheduled_sync.py           # Sincronización periódica
│
├── .env                            # Variables de entorno (local)
├── .env.example                    # Plantilla de variables de entorno
├── requirements.txt                # Dependencias del proyecto
└── README.md                       # Documentación general
```

## Componentes Clave

### 1. Módulo API (app/api)

- **router.py**: Define y organiza todas las rutas de la API.
- **endpoints/manychat.py**: Recibe eventos de webhooks de ManyChat, valida la autenticación y coloca los eventos en cola.
- **endpoints/odoo.py**: Gestiona webhooks desde Odoo para sincronización bidireccional.
- **endpoints/reports.py**: Proporciona endpoints para consultas y reportes sobre los datos.

### 2. Configuración (app/core)

- **config.py**: Gestiona la configuración de la aplicación, cargando variables desde archivos .env o Azure Key Vault.
- **security.py**: Implementa verificación de API keys y autenticación para webhooks.
- **logging.py**: Configura el sistema de logging estructurado para toda la aplicación.

### 3. Acceso a Datos (app/db)

- **models.py**: Define los modelos SQLAlchemy que mapean las tablas de la base de datos Azure SQL.
- **repositories.py**: Implementa el patrón repositorio para abstraer operaciones CRUD.
- **session.py**: Configura la conexión a la base de datos con pool de conexiones.

### 4. Servicios (app/services)

- **queue_service.py**: Gestiona la interacción con Azure Storage Queues.
- **odoo_service.py**: Proporciona métodos para interactuar con Odoo JSON-RPC con control de tasa.
- **manychat_service.py**: Contiene lógica para procesar eventos de ManyChat.
- **azure_sql_service.py**: Contiene lógica específica para operaciones complejas en Azure SQL.

### 5. Esquemas (app/schemas)

- **manychat.py**: Define la estructura de los eventos de ManyChat.
- **odoo.py**: Define la estructura de los datos para Odoo.
- **common.py**: Contiene esquemas compartidos entre diferentes partes de la aplicación.

### 6. Utilidades (app/utils)

- **retry.py**: Implementa lógica de reintentos con backoff exponencial.
- **monitoring.py**: Configura instrumentación para métricas y trazas.
- **idempotency.py**: Previene procesamiento duplicado de mensajes.

### 7. Procesadores (workers)

- **queue_processor.py**: Consume mensajes de la cola y los procesa respetando límites de API.
- **scheduled_sync.py**: Ejecuta sincronización periódica entre sistemas para garantizar consistencia.

### 8. Azure Functions (azure_function)

- **function.json**: Configura los disparadores y enlaces de la Azure Function.
- **host.json**: Configuración general para el host de Azure Functions.

## Configuración del Entorno

### Archivo .env

El archivo `.env` contiene todas las variables de configuración necesarias:

```
DEBUG=true

# API Configuration
API_KEY=tu-api-key-aquí
API_V1_STR=/api/v1

# Odoo Connection
ODOO_HOST=tu-instancia.odoo.com
ODOO_PORT=443
ODOO_PROTOCOL=jsonrpc+ssl
ODOO_DB=nombre-database
ODOO_USER=usuario
ODOO_PASSWORD=contraseña

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=cuenta;AccountKey=clave;EndpointSuffix=core.windows.net

# Azure SQL Database
DATABASE_URL=mssql+pyodbc://usuario:password@servidor.database.windows.net:1433/basedatos?driver=ODBC+Driver+17+for+SQL+Server

# Key Vault (opcional)
USE_KEY_VAULT=false
# KEY_VAULT_NAME=nombre-keyvault
```

### Azure Storage Queues

Para el sistema de colas, se requieren dos colas en Azure Storage:

1. `manychat-events-queue`: Cola principal para eventos a procesar
2. `dead-letter-queue`: Cola para mensajes con errores de procesamiento

## Guía de Desarrollo

### Requisitos Previos

1. Python 3.11 o superior
2. Cuenta de Azure con:
   - Azure SQL Database
   - Azure Storage Account
   - Azure Functions (para despliegue)
3. Instancia de Odoo 18 con acceso API

### Configuración del Entorno de Desarrollo

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/tu-organizacion/miasalud-integration.git
   cd miasalud-integration
   ```

2. **Crear entorno virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**:
   ```bash
   cp .env.example .env
   # Editar .env con las credenciales adecuadas
   ```

5. **Ejecutar servidor de desarrollo**:
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Ejecutar worker en otra terminal**:
   ```bash
   python -m workers.queue_processor
   ```

### Ejecutar pruebas

```bash
pytest tests/
```

## Despliegue

### Desplegar como Azure Functions

1. **Preparar la aplicación**:
   ```bash
   # Asegúrate de que azure_function/ está configurado correctamente
   ```

2. **Desplegar usando Azure CLI**:
   ```bash
   az login
   az functionapp deployment source config-zip -g MiasaludRemarketing -n miasalud-azure-manychat-remarketing --src dist/function.zip
   ```

3. **Configurar variables de entorno en Azure**:
   ```bash
   az functionapp config appsettings set --name miasalud-azure-manychat-remarketing --resource-group MiasaludRemarketing --settings "AZURE_STORAGE_CONNECTION_STRING=valor" "ODOO_HOST=valor" ...
   ```

4. **Configurar las colas**:
   Asegúrate de que las colas `manychat-events-queue` y `dead-letter-queue` existan en la cuenta de Azure Storage.

## Requirements

El archivo `requirements.txt` debe contener las siguientes dependencias:

```
# API Framework
fastapi>=0.100.0
uvicorn>=0.22.0
pydantic>=2.0.0
python-dotenv>=1.0.0
python-multipart>=0.0.6

# Database
sqlalchemy>=2.0.0
pyodbc>=4.0.39
pymssql>=2.2.7

# Azure
azure-storage-queue>=12.6.0
azure-identity>=1.13.0
azure-keyvault-secrets>=4.7.0
opencensus-ext-azure>=1.1.9

# Odoo
odoorpc>=0.8.0

# Utils
httpx>=0.24.1
tenacity>=8.2.2
python-jose>=3.3.0
passlib>=1.7.4
email-validator>=2.0.0

# Testing
pytest>=7.3.1
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.10.0
```

Este archivo de requirements incluye todas las dependencias necesarias para:
- Desarrollo con FastAPI
- Conexión a Azure SQL mediante SQLAlchemy y pyodbc
- Interacción con Azure Storage Queues
- Comunicación con Odoo vía JSON-RPC
- Seguridad, autenticación y validación
- Pruebas automatizadas

## Desarrollo con Docker 🐳

### Quick Start

```bash
# Setup inicial
./scripts/docker-setup.sh

# Verificar que todo funciona
./scripts/docker-test.sh

# Ver logs en tiempo real
docker-compose logs -f api

# Ejecutar tests
docker-compose run --rm api pytest

# Reconstruir imagen
docker-compose build api

# Entrar al contenedor
docker-compose exec api bash
```

### Entorno de Desarrollo

El entorno de desarrollo está configurado para proporcionar:
- Hot-reload para desarrollo rápido
- PostgreSQL para desarrollo local
- Workers procesando eventos en background
- Volúmenes montados para edición en tiempo real

### Entorno de Producción

Para desplegar en producción:

```bash
# Desplegar servicios
docker-compose -f docker/docker-compose.prod.yml up -d

# Verificar estado
docker-compose -f docker/docker-compose.prod.yml ps

# Ver logs
docker-compose -f docker/docker-compose.prod.yml logs -f
```

Características del entorno de producción:
- Imágenes optimizadas (< 500MB)
- Health checks configurados
- Logs centralizados
- TLS habilitado
- Reinicio automático en caso de fallos

### Verificación del Sistema

Para verificar que todo funciona correctamente:

1. Health check debe retornar 200:
```bash
curl -f http://localhost:8000/health
```

2. Probar el endpoint principal:
```bash
curl -X POST "http://localhost:8000/api/v1/manychat/webhook/contact" \
     -H "Content-Type: application/json" \
     -H "X-API-KEY: your-api-key" \
     -d '{"manychat_id": "test", "nombre_lead": "Test", "datetime_actual": "2024-05-01"}'
```

3. Verificar logs de workers:
```bash
docker-compose logs -f workers
```

## Criterios de Éxito 🎯

### Funcionalidad Básica
- [ ] `docker-compose up` arranca todos los servicios
- [ ] API responde en `http://localhost:8000`
- [ ] Health check retorna 200
- [ ] Base de datos acepta conexiones
- [ ] Workers procesan eventos correctamente

### Testing
- [ ] `./scripts/docker-test.sh` pasa todos los tests
- [ ] Endpoints POST retornan 202
- [ ] Base de datos persiste datos entre reinicios
- [ ] Hot-reload funciona en desarrollo

### Producción
- [ ] `docker-compose.prod.yml` funciona
- [ ] Imágenes optimizadas (< 500MB)
- [ ] Health checks configurados
- [ ] Logs centralizados

## Guía de Verificación

1. Verificar servicios:
```bash
docker-compose ps
```

2. Verificar logs:
```bash
docker-compose logs -f
```

3. Verificar conexión a base de datos:
```bash
docker-compose exec api python -c "from app.db.session import check_database_connection; check_database_connection()"
```

4. Verificar workers:
```bash
docker-compose logs workers | grep "Processing"
```


Endpoints Funcionales (API FastAPI)
Tu API FastAPI ahora expone endpoints específicos para recibir webhooks de ManyChat, asegurando la autenticación mediante una clave API (X-API-KEY).

URL Base de la API (Local): http://localhost:8000

Autenticación Requerida: Para todas las peticiones a los endpoints /api/v1/manychat/webhook/*, es obligatorio incluir un encabezado X-API-KEY con tu clave secreta.

Tu Clave API: Miasaludnatural123**

¡Excelente! Es fundamental documentar todo el progreso y las soluciones para referencia futura. Aquí tienes un resumen detallado de lo que hemos avanzado y confirmado:

Documentación de Avance: Configuración y Prueba de Webhooks ManyChat en LeadSyncAPI
Hemos configurado, depurado y validado el flujo completo para la recepción de webhooks de ManyChat, su procesamiento asíncrono a través de colas de Azure Storage, y la persistencia de datos en Azure SQL Database.

1. Endpoints Funcionales (API FastAPI)
Tu API FastAPI ahora expone endpoints específicos para recibir webhooks de ManyChat, asegurando la autenticación mediante una clave API (X-API-KEY).

URL Base de la API (Local): http://localhost:8000

Autenticación Requerida: Para todas las peticiones a los endpoints /api/v1/manychat/webhook/*, es obligatorio incluir un encabezado X-API-KEY con tu clave secreta.

Tu Clave API: Miasaludnatural123**
2. Cuerpos de los JSON para Peticiones (Ejemplos Probados Exitosamente)
A continuación, se detallan los cuerpos JSON y los encabezados utilizados para probar exitosamente cada endpoint.

2.1. Webhook de Contactos (manychat-contact-queue)
Este endpoint recibe eventos relacionados con actualizaciones de contacto de ManyChat y los encola para procesamiento posterior.

URL del Endpoint: http://localhost:8000/api/v1/manychat/webhook/contact
Método HTTP: POST
Headers de la Petición:
Content-Type: application/json
X-API-KEY: Miasaludnatural123**
Cuerpo JSON de Ejemplo (Probado y Confirmado):
JSON

{
    "manychat_id": "test_contact_456",
    "nombre_lead": "Test Contact Data",
    "datetime_actual": "2025-06-05T12:41:36Z", // Ejemplo de fecha/hora (cambia cada vez)
    "ultimo_estado": "Nuevo",
    "id": "1234567890_manychat_id",
    "first_name": "Test",
    "last_name": "Data",
    "phone": "+56912345678",
    "email": "test.data@example.com"
}
Respuesta Exitosa Esperada (Ejemplo de la API):
JSON

{
    "status": "accepted",
    "message": "Webhook received and event queued",
    "manychat_id": "test_contact_456",
    "queue": "manychat-contact-queue"
}
Flujo de Procesamiento Confirmado:
La API recibe el evento.
Lo envía a la cola de Azure Storage: manychat-contact-queue.
El worker contact_processor.py consume el mensaje.
AzureSQLService guarda los datos del contacto en la tabla dbo.Contact de Azure SQL Database.
El mensaje es eliminado exitosamente de la cola.
2.2. Webhook de Asignación de Campañas (manychat-campaign-queue)
Este endpoint gestiona la asignación de contactos a campañas, encolando los eventos para su procesamiento.

URL del Endpoint: http://localhost:8000/api/v1/manychat/webhook/campaign-assignment
Método HTTP: POST
Headers de la Petición:
Content-Type: application/json
X-API-KEY: Miasaludnatural123**
Cuerpo JSON de Ejemplo (Probado y Confirmado):
JSON

{
    "manychat_id": "test_contact_456",
    "campaign_id": "CAMP-ABC-123",
    "comercial_id": "COM-XYZ-001",
    "datetime_actual": "2025-06-05T12:45:00Z", // Ejemplo de fecha/hora (cambia cada vez)
    "ultimo_estado": "Asignado",
    "tipo_asignacion": "Automatica"
}
Respuesta Exitosa Esperada (Ejemplo de la API):
JSON

{
    "status": "accepted",
    "message": "Evento de campaña encolado exitosamente",
    "manychat_id": "test_contact_456",
    "campaign_id": "CAMP-ABC-123",
    "queue": "manychat-campaign-queue"
}
Flujo de Procesamiento Confirmado:
La API recibe el evento.
Lo envía a la cola de Azure Storage: manychat-campaign-queue.
El worker campaign_assignment_processor.py consume el mensaje.
AzureSQLService guarda los datos de la asignación de campaña en la tabla dbo.Campaign_Contact de Azure SQL Database (asumiendo que las IDs de campaña y comercial/asesor existen en sus tablas correspondientes).
El mensaje es eliminado exitosamente de la cola.
3. Documentación Interactiva de la API (Swagger UI / OpenAPI)
No puedo generar capturas de pantalla directamente, pero tu API FastAPI proporciona una excelente documentación interactiva de forma automática.

Cómo Acceder:
Asegúrate de que tu API FastAPI está ejecutándose localmente (por ejemplo, con uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload).
Abre tu navegador web y navega a la siguiente URL: http://localhost:8000/docs
Qué Verás:
Verás una interfaz de Swagger UI (o redoc si usas /redoc) que lista todos tus endpoints.
Podrás expandir cada endpoint para ver su método HTTP, la URL completa, la descripción y los esquemas JSON esperados (Request Body) y las posibles respuestas (Response).
La sección de "Schemas" en la parte inferior te mostrará la estructura detallada de los modelos Pydantic, como ManyChatContactEvent y ManyChatCampaignAssignmentEvent, incluyendo qué campos son obligatorios.
Puedes usar la función "Try it out" (Pruébalo) directamente en la interfaz de Swagger para enviar peticiones. Necesitarás hacer clic en "Authorize" en la parte superior derecha para introducir tu clave API (Miasaludnatural123**) en el campo X-API-KEY.
4. Resumen de la Arquitectura Probada
El sistema implementado y verificado ahora sigue el siguiente flujo de datos para eventos de ManyChat:

ManyChat Webhook (→) FastAPI API (→) Azure Storage Queue (→) Workers (→) Azure SQL Database

ManyChat Webhook: Envía eventos (contacto, campaña) a tu API.
FastAPI API:
Recibe las peticiones POST.
Requiere autenticación por X-API-KEY.
Valida los cuerpos JSON contra esquemas Pydantic.
Encola los eventos en colas dedicadas de Azure Storage.
Azure Storage Queue:
manychat-contact-queue: Para eventos de contacto.
manychat-campaign-queue: Para eventos de asignación de campaña.
Workers (Consumidores):
contact_processor.py: Consume de manychat-contact-queue, procesa el contacto y lo guarda en dbo.Contact.
campaign_assignment_processor.py: Consume de manychat-campaign-queue, procesa la asignación y la guarda en dbo.Campaign_Contact.
Azure SQL Database: Almacena los datos persistentes de contactos y asignaciones.
Además, hemos asegurado que los secretos (como la cadena de conexión de Azure Storage) estén gestionados correctamente mediante el uso del archivo .env (localmente) y que este archivo esté excluido del control de versiones de Git a través de .gitignore, habiendo limpiado el historial del repositorio.