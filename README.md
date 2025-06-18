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

MiaSalud Integration API es una solución robusta para integrar ManyChat (chatbot) con Odoo 18 y Azure SQL. Permite registrar y sincronizar contactos y asignaciones de campañas en ambos sistemas, procesando más de 1000 eventos por hora. Utiliza FastAPI, Azure Storage Queues y workers asíncronos para desacoplar el procesamiento y garantizar resiliencia y escalabilidad.

## Arquitectura y Flujo

1. **ManyChat** envía eventos (contactos y asignaciones de campaña) vía webhooks a la API.
2. **API FastAPI** recibe los eventos y los encola en Azure Storage Queue.
3. **Workers** procesan los mensajes de la cola y actualizan Azure SQL y Odoo.
4. **Sincronización**: El estado de sincronización con Odoo se gestiona en Azure SQL (`odoo_sync_status`).
5. **Errores**: Los mensajes fallidos van a una Dead Letter Queue (DLQ) para análisis.

## Componentes Clave

- **API (FastAPI):**
  - `/api/v1/manychat/webhook/contact`: Recibe eventos de contacto de ManyChat.
  - `/api/v1/manychat/webhook/campaign-assignment`: Recibe asignaciones de campaña.
  - `/api/v1/manychat/campaign-contacts/update-by-manychat-id`: Actualiza registros de CampaignContact.
  - CRUD para contactos, campañas, canales y asesores.
  - Endpoints de consulta y sincronización con Odoo (`/api/v1/odoo/contacts/`).
  - Health checks: `/health`, `/api/v1/reports/health`.

- **Workers:**
  - Procesan colas de Azure (`manychat-contact-queue`, `manychat-campaign-queue`).
  - Actualizan Azure SQL y sincronizan con Odoo.
  - Ejecutables vía `python -m workers.contact_processor` y `python -m workers.campaign_processor`.

- **Azure Storage Queues:**
  - `manychat-contact-queue`: Contactos de ManyChat.
  - `manychat-campaign-queue`: Asignaciones de campaña.
  - `dead-letter-queue`: Mensajes con errores.

- **Azure SQL:**
  - Persistencia principal de contactos, campañas, asesores y relaciones.

- **Odoo:**
  - Sincronización de contactos y campañas vía JSON-RPC.

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

## Endpoints Principales

- `POST /api/v1/manychat/webhook/contact`  
  Recibe eventos de contacto desde ManyChat y los encola para procesamiento asíncrono.
- `POST /api/v1/manychat/webhook/campaign-assignment`  
  Recibe asignaciones de campaña y asesores desde ManyChat y los encola para procesamiento asíncrono.
- `PUT /api/v1/manychat/campaign-contacts/update-by-manychat-id`  
  Actualiza campos de CampaignContact usando el ManyChat ID y, opcionalmente, el campaign_id.
- `GET /api/v1/odoo/contacts/`  
  Consulta contactos en Odoo.
- CRUD para `/api/v1/contacts/`, `/api/v1/campaigns/`, `/api/v1/channels/`, `/api/v1/advisors/`.
- Health: `/health`, `/api/v1/reports/health`

## Ejemplo de Flujo

1. **Nuevo contacto:**
   - ManyChat → `/manychat/webhook/contact` → Azure Queue → Worker → Azure SQL + Odoo
2. **Asignación de campaña:**
   - ManyChat → `/manychat/webhook/campaign-assignment` → Azure Queue → Worker → Azure SQL
3. **Actualización de CampaignContact:**
   - ManyChat → `/manychat/campaign-contacts/update-by-manychat-id` → Azure SQL

## Ejemplo de Uso de Endpoints

### Webhook de Contacto
**POST** `/api/v1/manychat/webhook/contact`
```json
{
  "manychat_id": "MC99999",
  "nombre_lead": "Ana",
  "apellido_lead": "García",
  "whatsapp": "+521234567891",
  "datetime_suscripcion": "2025-06-10T10:00:00Z",
  "datetime_actual": "2025-06-10T10:05:00Z",
  "ultimo_estado": "Nuevo Lead",
  "canal_entrada": "Facebook",
  "estado_inicial": "Nuevo"
}
```

### Webhook de Asignación de Campaña
**POST** `/api/v1/manychat/webhook/campaign-assignment`
```json
{
  "manychat_id": "MC99999",
  "campaign_id": 85,
  "comercial_id": "700",
  "medico_id": "101",
  "datetime_actual": "2025-06-10T10:10:00Z",
  "ultimo_estado": "Asignado a campaña",
  "tipo_asignacion": "medico"
}
```

### Actualización de CampaignContact
**PUT** `/api/v1/manychat/campaign-contacts/update-by-manychat-id`
```json
{
  "manychat_id": "MC99999",
  "campaign_id": 85,
  "medical_advisor_id": 101,
  "medical_assignment_date": "2025-06-10T11:00:00Z",
  "last_state": "Asignado a médico"
}
```

### CRUD de Contactos
**POST** `/api/v1/contacts/`
```json
{
  "manychat_id": "MC12345",
  "first_name": "Juan",
  "last_name": "Pérez",
  "phone": "+521234567890",
  "channel_id": 1
}
```

### CRUD de Campañas
**POST** `/api/v1/campaigns/`
```json
{
  "name": "Campaña Invierno 2025",
  "date_start": "2025-06-12T14:49:28.163Z",
  "date_end": "2025-12-31T23:59:59.000Z",
  "budget": 50000,
  "status": "Activa",
  "channel_id": 1
}
```

### CRUD de Canales
**POST** `/api/v1/channels/`
```json
{
  "name": "Facebook Messenger",
  "description": "Canal oficial de Facebook"
}
```

### CRUD de Asesores
**POST** `/api/v1/advisors/`
```json
{
  "name": "Dra. Laura",
  "email": "laura@ejemplo.com",
  "phone": "+521234567891"
}
```

## Seguridad
- Todos los endpoints protegidos requieren el header `X-API-KEY`.
- Las credenciales deben gestionarse por variables de entorno o Azure Key Vault.

## Workers y Procesamiento Asíncrono
- Ejecuta los workers con:
  ```bash
  python -m workers.contact_processor
  python -m workers.campaign_processor
  ```
- Los workers procesan colas de Azure y sincronizan con Odoo y Azure SQL.

## Monitoreo y Health
- Health checks: `/health`, `/api/v1/reports/health`
- Logs estructurados y métricas en `app/utils/monitoring.py`

## Docker y Despliegue
- Usa `docker-compose.yml` para desarrollo y pruebas locales.
- Usa `docker/docker-compose.prod.yml` para producción.
- Para App Service en Azure, usa:
  ```bash
  gunicorn wsgi:app --config gunicorn.conf.py
  ```
- Para workers en Azure Container Instances:
  ```bash
  docker build -f docker/Dockerfile.workers -t miasalud/workers:latest .
  ```

## Testing
- Ejecuta los tests con:
  ```bash
  pytest
  ```
- Los tests usan variables de entorno desde `.env` o CI/CD.

---

Este README fue actualizado para reflejar la arquitectura, endpoints y flujos actuales del proyecto MiaSalud Integration API.