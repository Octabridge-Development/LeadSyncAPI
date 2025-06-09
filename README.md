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

## Monitoreo y Scripts

### Monitoreo

El directorio [`monitoring/`](monitoring/) contiene scripts para monitorear el estado de las colas y otros recursos críticos. Por ejemplo, [`queue_monitor.py`](monitoring/queue_monitor.py) permite verificar el estado y la cantidad de mensajes pendientes en las colas de Azure Storage.

#### Ejemplo de uso:
```bash
python monitoring/queue_monitor.py
```

### Scripts Auxiliares

El directorio [`scripts/`](scripts/) incluye utilidades para facilitar tareas comunes de desarrollo y despliegue. Algunos ejemplos:
- `docker-setup.sh`: Inicializa el entorno Docker.
- `docker-test.sh`: Ejecuta los tests en el entorno Docker.
- `docker-deploy.sh`: Despliega la aplicación usando Docker.
- `start-workers.sh`: Inicia los workers manualmente.
- (Revisa cada script para más detalles sobre su uso.)

## Workers

El directorio [`workers/`](workers/) contiene procesos de fondo:
- [`queue_processor.py`](workers/queue_processor.py): Procesa eventos de la cola principal.
- [`scheduled_sync.py`](workers/scheduled_sync.py): Realiza sincronizaciones periódicas entre sistemas.
- [`campaign_processor.py`](workers/campaign_processor.py): Procesa campañas de marketing.
- [`contact_processor.py`](workers/contact_processor.py): Procesa contactos de manera asíncrona.

Para ejecutar un worker manualmente:
```bash
python -m workers.queue_processor
python -m workers.scheduled_sync
```

## Health Check

El endpoint `/health` verifica el estado de:
- Base de datos
- Conexión a Odoo
- Estado de las colas de Azure

Devuelve un JSON detallado con el estado de cada dependencia. Útil para integración con sistemas de monitoreo y orquestadores.

## Testing y Cobertura

Para ejecutar los tests y generar un reporte de cobertura:
```bash
pytest --cov=app tests/
```
El reporte se mostrará en consola. Para generar un reporte HTML:
```bash
pytest --cov=app --cov-report=html tests/
```
El resultado estará en el directorio `htmlcov/`.

## Despliegue en Azure Functions

La carpeta [`azure_function/`](azure_function/) contiene la configuración necesaria para desplegar la API como Azure Function. Si agregas nuevas dependencias, recuerda actualizar el archivo `requirements.txt` correspondiente y revisar los archivos `function.json` y `host.json` para reflejar los nuevos endpoints o triggers.