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
10. [Avances y Estado Actual](#avances-y-estado-actual)

## Visión General

MiaSalud Integration API es una solución robusta para integrar ManyChat (chatbot) con Odoo 18 y Azure SQL. Permite registrar y sincronizar contactos y asignaciones de campañas en ambos sistemas, procesando más de 1000 eventos por hora. Utiliza FastAPI, Azure Storage Queues y workers asíncronos para desacoplar el procesamiento y garantizar resiliencia y escalabilidad.

## Arquitectura y Flujo

1. **ManyChat** envía eventos (contactos y asignaciones de campaña) vía webhooks a la API.
2. **API FastAPI** recibe los eventos y los encola en Azure Storage Queue.
3. **Workers** procesan los mensajes de la cola y actualizan Azure SQL y Odoo.
4. **Sincronización**: El estado de sincronización con Odoo se gestiona en Azure SQL.
5. **Errores**: Los mensajes fallidos van a una Dead Letter Queue (DLQ) para análisis.

## Cambios recientes y mejoras

- Eliminado el campo `ultimo_estado` de los esquemas y endpoints. Ahora el estado se gestiona únicamente con `state` o `estado_inicial` según el flujo.
- El endpoint de contacto y el de asignación de campaña solo requieren el campo de estado actual (`state` o `estado_inicial`).
- El campo `last_state` en la tabla `Campaign_Contact` se sincroniza automáticamente usando el valor de `state` recibido.
- Si los campos de asesor (`comercial_id`, `medico_id`) vienen como `null`, `""` o `0`, se guardan como `NULL` en la base de datos, evitando errores de integridad referencial.
- La tabla `Channel` fue limpiada y ahora solo contiene los canales principales: WhatsApp, TikTok, Instagram y Messenger.
- Las respuestas de los endpoints son consistentes y devuelven información clara sobre el estado de la operación.
- Ejemplos de payloads y documentación de endpoints actualizados para reflejar los cambios.

## Componentes Clave

- **API (FastAPI):**
  - `/api/v1/manychat/webhook/contact`: Recibe eventos de contacto de ManyChat.
  - `/api/v1/manychat/webhook/campaign-contact-assign`: Recibe asignaciones de campaña y asesores desde ManyChat.
  - `/api/v1/manychat/campaign-contacts/update-by-manychat-id`: Actualiza registros de CampaignContact.
  - CRUD para contactos, campañas, canales y asesores.
  - Endpoints de consulta y sincronización con Odoo (`/api/v1/odoo/contacts/`).
  - Health checks: `/health`, `/api/v1/reports/health`.

- **Workers:**
  - Procesan colas de Azure (`manychat-contact-queue`, `manychat-campaign-queue`).
  - Actualizan Azure SQL y sincronizan con Odoo.
  - Ejecutables vía `python -m workers.contact_processor` y `python -m workers.campaign_processor`.
  - El worker de campaign_contact sincroniza automáticamente el campo `last_state` con el estado más reciente de ContactState.

- **Azure Storage Queues:**
  - `manychat-contact-queue`: Contactos de ManyChat.
  - `manychat-campaign-queue`: Asignaciones de campaña.
  - `dead-letter-queue`: Mensajes con errores.

- **Azure SQL:**
  - Persistencia principal de contactos, campañas, asesores, canales y relaciones.
  - Tabla `Channel` contiene solo los canales principales: WhatsApp, TikTok, Instagram, Messenger.

- **Odoo:**
  - Sincronización de contactos y campañas vía JSON-RPC.

## Ejemplo de Payloads y Endpoints

### Webhook de Contacto
**POST** `/api/v1/manychat/webhook/contact`
```json
{
  "manychat_id": "MC20250722",
  "nombre_lead": "Ana",
  "apellido_lead": "Martínez",
  "whatsapp": "+521234567890",
  "email_lead": "ana.martinez@example.com",
  "datetime_suscripcion": "2025-07-22T17:14:51.085Z",
  "datetime_actual": "2025-07-22T17:14:51.085Z",
  "canal_entrada": "WhatsApp",
  "estado_inicial": "Nuevo"
}
```

### Webhook de Asignación de Campaña
**POST** `/api/v1/manychat/webhook/campaign-contact-assign`
```json
{
  "manychat_id": "MC20250722",
  "campaign_id": 1034,
  "state": "Asignado a Comercial",
  "registration_date": "2025-07-22T17:16:06.644Z",
  "comercial_id": null,
  "medico_id": null,
  "fecha_asignacion": "2025-07-22T17:16:06.644Z",
  "category": "manychat",
  "summary": "Cliente interesado en producto X"
}
```

- Si no hay asesor, puedes enviar `null`, `""` o `0` en los campos de asesor y se guardarán como `NULL` en la base de datos.

### CRUD de Canales
**POST** `/api/v1/channels/`
```json
{
  "name": "WhatsApp",
  "description": "Canal de WhatsApp"
}
```

## Validaciones y Seguridad
- Todos los endpoints protegidos requieren el header `X-API-KEY`.
- Si los campos de asesor no son válidos, se almacenan como `NULL`.
- La validación de la API Key y otras dependencias se realiza de forma centralizada en `app/api/deps.py`.

## Workers y Procesamiento Asíncrono
- Ejecuta los workers con:
  ```bash
  python -m workers.contact_processor
  python -m workers.campaign_processor
  ```
- Los workers procesan colas de Azure y sincronizan con Odoo y Azure SQL.
- El worker de campaign_contact sincroniza automáticamente el campo `last_state` con el estado más reciente de ContactState.

## Canales Disponibles

La tabla `Channel` contiene actualmente:
- WhatsApp
- TikTok
- Instagram
- Messenger

## Notas de Migración y Refactorización
- Eliminada la lógica de sincronización de contactos con Odoo (solo oportunidades CRM).
- Refactorización de workers y servicios para un flujo más limpio y desacoplado.
- Documentación y ejemplos actualizados para reflejar la arquitectura y flujos actuales.

---

Este README fue actualizado para reflejar la arquitectura, endpoints y flujos actuales del proyecto MiaSalud Integration API.