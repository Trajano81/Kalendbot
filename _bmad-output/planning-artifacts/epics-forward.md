---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/project-context.md'
  - '_bmad-output/planning-artifacts/epics-retrospective.md'
epicType: forward
premortem_applied: true
---

# Kalendbot - Epic Breakdown (Forward)

## Overview

Épicas de trabajo futuro para KalendBot, construyendo sobre las 6 épicas retroactivas completadas (20 FRs, 7 NFRs). Refinado via Pre-mortem Analysis: Epic 8 (Testing) disuelto como ACs embebidos, Epic 11 reducido (abstracción diferida por YAGNI), Story 7.3 dividida en stories atómicas, dependencia 9→10.2 resuelta.

## Requirements Inventory

### Functional Requirements

FR21: WhatsApp bot via WAHA — webhook handler FastAPI, routing de mensajes 1-a-1, soporte media (archivos, imágenes)
FR22: Comandos WhatsApp — equivalentes de /export_excel, /export_jpeg, /export_instructions via prefijo ! o comandos naturales
FR23: WhatsApp grupo dual — publicar en grupo WA además de Telegram (dispatcher ya soporta "both")
FR24: Tests unitarios — cada tool con fixtures JSON de prueba en tests/fixtures/
FR25: Tests de integración — handle_message con mock de LLM (FAQ bypass, identificación contacto, fallback)
FR26: Tests de regresión — 1 test mínimo por cada ISSUE/OBS resuelto (11 issues totales)
FR27: Reminder check diario — verificar eventos próximos y disparar recordatorios automáticos
FR28: Delivery de recordatorios — enviar por gateway configurado (Telegram o WhatsApp)
FR29: Historial de recordatorios — registro de qué se envió, a quién, cuándo, y si fue exitoso
FR30: Edición de contacto_ids — agregar/quitar contactos asociados a un evento
FR31: Campo canales — canal de comunicación preferido por contacto (telegram/whatsapp)
FR32: texto_social — generación/edición de texto social para publicación de eventos
FR33: Gestión de instancias recurrentes — agregar/eliminar instancias individuales de eventos recurrentes
FR34: Abstracción de data layer — DIFERIDO (YAGNI: 30 eventos y 9 contactos no justifican abstracción)
FR35: Persistencia de MemorySaver — migrar de in-memory a SQLite o PostgreSQL checkpointer

### NonFunctional Requirements

NFR8: Concurrent write safety — file locking para escrituras simultáneas (WhatsApp multi-usuario)
NFR9: Whitelist de contactos — solo teléfonos autorizados en kalendbot-data/config/whitelist.json
NFR10: Rate limiting — máx 3 mensajes para contactos unknown-*, luego ignorar
NFR11: Test coverage obligatorio — todos los tools testeados antes de conectar WhatsApp (embebido como AC en Epic 7)
NFR12: 5 roles completos — migrar de 4 roles actuales (admin/tester/contacto/readonly) a 5 (admin/content_manager/proveedor/readonly/blocked) según PRD

### Additional Requirements

- evolution.py es código legacy/referencia — WAHA es el provider oficial de WhatsApp
- Infraestructura WAHA ya existe: waha_provider.py, whatsapp_provider.py (Protocol), dispatcher.py
- whatsapp_bot.py existe pero incompleto — necesita completarse como equivalente de telegram_bot.py
- El dispatcher ya soporta envío dual (Telegram + WhatsApp) via channel="both"
- Tests fixtures en tests/fixtures/ — NO usar datos reales de producción
- Framework pytest para todos los tests automatizados
- Pre-mortem: testing embebido como ACs, no como épica separada

### UX Design Requirements

N/A — proyecto conversational-first sin UI visual propia.

### FR Coverage Map

FR21: Epic 7 — WhatsApp bot webhook handler y routing
FR22: Epic 7 — Comandos export via WhatsApp
FR23: Epic 7 — Verificación grupo dual (código existente)
FR24: Epic 7 (Story 7.1) — Tests unitarios como fundación
FR25: Epic 7 (Story 7.1) — Tests integración embebidos
FR26: Epic 7 (Story 7.1) — Tests regresión embebidos
FR27: Epic 9 — Reminder check diario
FR28: Epic 9 — Delivery de recordatorios
FR29: Epic 9 — Historial de recordatorios
FR30: Epic 10 — Edición contacto_ids
FR31: Epic 10 — Campo canales preferido
FR32: Epic 10 — texto_social
FR33: Epic 10 — Gestión instancias recurrentes
FR34: DIFERIDO — YAGNI para 30 eventos/9 contactos
FR35: Epic 11 — Persistencia MemorySaver

NFR8:  Epic 11 — Concurrent write safety (file locking)
NFR9:  Epic 7 — Whitelist contactos
NFR10: Epic 7 — Rate limiting
NFR11: Epic 7 (Story 7.1) — Coverage obligatorio pre-WhatsApp
NFR12: Epic 7 — 5 roles completos según PRD

## Epic List

### Epic 7: Gateway Flexible (Telegram/WhatsApp)
Los usuarios acceden al bot por Telegram, WhatsApp (WAHA), o ambos según configuración. Incluye test suite fundacional como prerequisito, seguridad unificada (whitelist, rate limit, 5 roles), feature parity entre gateways.
**FRs cubiertos:** FR21, FR22, FR23, FR24, FR25, FR26
**NFRs cubiertos:** NFR9, NFR10, NFR11, NFR12
**Prioridad:** Alta
**Archivos clave:** `src/gateways/whatsapp_bot.py`, `src/gateways/dispatcher.py`, `src/agent.py`, `tests/`

### ~~Epic 8: Testing Comprehensivo~~ — DISUELTO
Testing embebido como ACs dentro de cada story. Test suite fundacional absorbido en Epic 7 Story 7.1.

### Epic 9: Recordatorios Automatizados (Sin Agente)
Proceso autónomo (cron/scheduler) que verifica eventos próximos y envía recordatorios por el gateway configurado, sin consumir tokens LLM. Usa canal default del gateway, no canal_preferido por contacto (resuelve dependencia con Epic 10).
**FRs cubiertos:** FR27, FR28, FR29
**Prioridad:** Media
**Archivos clave:** `src/reminders/` (nuevo), `src/gateways/dispatcher.py`, `src/gateways/templates.py`

### Epic 10: Campos Fase 2
Extensión del sistema de edición para campos complejos: contacto_ids (agregar/quitar contactos de eventos), canales preferidos, texto social para publicaciones, y gestión de instancias individuales de eventos recurrentes.
**FRs cubiertos:** FR30, FR31, FR32, FR33
**Prioridad:** Baja
**Archivos clave:** `src/tools/calendar_manager.py`, `kalendbot-data/config/instrucciones-edicion.json`

### Epic 11: Hardening Pre-producción
Persistencia real de MemorySaver (SQLite) y concurrent write safety (file locking) para soportar multi-usuario en producción. Abstracción de data layer diferida por YAGNI.
**FRs cubiertos:** FR35
**NFRs cubiertos:** NFR8
**Prioridad:** Media
**Archivos clave:** `src/agent.py` (MemorySaver)

---

## Epic 7: Gateway Flexible (Telegram/WhatsApp)

**Goal:** Los usuarios acceden al bot por Telegram, WhatsApp (WAHA), o ambos. Test suite fundacional como prerequisito, seguridad unificada, feature parity entre gateways.

### Story 7.1: Test Suite Fundacional

Como desarrollador,
quiero una suite de tests que cubra las 9 tools existentes, integración de handle_message, y regresión de los 11 issues resueltos,
para que tenga una red de seguridad antes de agregar nuevos gateways.

**Acceptance Criteria:**

**Given** fixtures en tests/fixtures/ (calendario-test.json ~5 eventos, 3 contactos de prueba)
**When** se ejecuta `pytest tests/ -v`
**Then** tests unitarios cubren las 9 tools con input válido e inválido
**And** tests de integración verifican FAQ bypass, identificación de contacto, fallback unknown-*
**And** tests de regresión cubren mínimo 1 test por cada ISSUE-01 a 05 y OBS-01 a 06
**And** todos los tests pasan antes de proceder con stories siguientes

**FRs cubiertos:** FR24, FR25, FR26
**NFRs cubiertos:** NFR11
**Archivos:** `tests/`, `tests/fixtures/`, `tests/test_tools.py`, `tests/test_integration.py`, `tests/test_regressions.py`

### Story 7.2: Migración a 5 Roles

Como administrador del sistema,
quiero que el sistema soporte los 5 roles del PRD (admin, content_manager, proveedor, readonly, blocked),
para que los permisos estén alineados con el modelo operativo de NV Mexico.

**Acceptance Criteria:**

**Given** los 4 roles actuales (admin, tester, contacto, readonly) en agent.py
**When** se migra al modelo de 5 roles del PRD
**Then** admin mantiene acceso total
**And** content_manager gestiona flyers + consultas + notificar grupo
**And** proveedor consulta todo + modifica solo sus eventos (filtrado por contacto_ids)
**And** readonly solo consultas
**And** blocked causa que el bot ignore mensajes completamente
**And** los ROLE_SUFFIX_* se actualizan en el system prompt
**And** tests de roles existentes siguen pasando

**FRs cubiertos:** FR21 (modelo de permisos)
**NFRs cubiertos:** NFR12
**Archivos:** `src/agent.py`

### Story 7.3: Whitelist de Contactos Autorizados

Como administrador del sistema,
quiero una whitelist de teléfonos autorizados,
para que solo contactos conocidos puedan interactuar con el bot.

**Acceptance Criteria:**

**Given** whitelist.json en kalendbot-data/config/
**When** un mensaje llega de un teléfono no autorizado
**Then** el mensaje se ignora y se loggea el intento
**And** la whitelist se carga al arranque y se valida como JSON
**And** aplica tanto para Telegram como para WhatsApp

**NFRs cubiertos:** NFR9
**Archivos:** `kalendbot-data/config/whitelist.json` (nuevo), `src/agent.py`

### Story 7.4: Rate Limiting para Contactos Desconocidos

Como administrador del sistema,
quiero rate limiting para contactos no identificados,
para que el bot no sea abusado por números desconocidos.

**Acceptance Criteria:**

**Given** un contacto con ID unknown-*
**When** envía más de 3 mensajes
**Then** los mensajes subsiguientes se ignoran
**And** se loggea warning con el teléfono truncado
**And** el contador se reinicia por sesión del bot

**NFRs cubiertos:** NFR10
**Archivos:** `src/agent.py`

### Story 7.5: WhatsApp Bot Handler con WAHA

Como usuario de WhatsApp,
quiero enviar mensajes al bot y recibir respuestas via WhatsApp,
para que pueda gestionar el calendario desde mi canal preferido.

**Acceptance Criteria:**

**Given** whatsapp_bot.py con FastAPI webhook handler
**When** un usuario envía un mensaje de texto via WhatsApp
**Then** el bot procesa el mensaje via handle_message y responde por el mismo canal
**And** los mensajes de grupo se ignoran (modelo informativo only)
**And** mensajes sin texto (stickers, audio) se ignoran con log
**And** whitelist y rate limiting se aplican antes de procesar
**And** tests unitarios del webhook handler pasan

**FRs cubiertos:** FR21
**Archivos:** `src/gateways/whatsapp_bot.py`, `src/gateways/waha_provider.py`

### Story 7.6: Comandos de Exportación via WhatsApp

Como usuario aprobado de WhatsApp,
quiero solicitar exportaciones del calendario,
para que reciba archivos Excel, JPEG e instrucciones directamente en mi chat.

**Acceptance Criteria:**

**Given** un usuario registrado con permisos de exportación
**When** envía un comando de export (! prefijo o lenguaje natural via agente)
**Then** CalendarExporter genera el archivo y se envía via waha_provider.send_file/send_image
**And** errores de generación retornan mensaje descriptivo al usuario
**And** feature parity con los comandos /export_* de Telegram

**FRs cubiertos:** FR22
**Archivos:** `src/gateways/whatsapp_bot.py`, `src/tools/calendar_exporter.py`

### Story 7.7: Verificación de Grupo Dual

Como administrador del calendario,
quiero verificar que el envío dual a grupo (Telegram + WhatsApp) funciona correctamente,
para que las notificaciones lleguen al canal configurado.

**Acceptance Criteria:**

**Given** dispatcher.py y group_notifier.py ya soportan envío dual
**When** se ejecutan tests de verificación del comportamiento existente
**Then** con solo TELEGRAM_GROUP_CHAT_ID → envía solo a Telegram
**And** con solo WHATSAPP_GROUP_CHAT_ID → envía solo a WhatsApp
**And** con ambos → envía a ambos
**And** sin ninguno → loggea warning y retorna mock
**And** tests del dispatcher cubren los 4 escenarios

**FRs cubiertos:** FR23
**Archivos:** `src/tools/group_notifier.py`, `src/gateways/dispatcher.py`, `tests/test_dispatcher.py`

### Story 7.8: Entry Point Unificado con Docker Compose

Como operador del sistema,
quiero un solo container que arranque Telegram, WhatsApp o ambos según configuración,
para que el despliegue sea simple y no haya duplicación de schedulers ni conflictos de escritura.

**Acceptance Criteria:**

**Given** un entry point unificado (`src/main.py`) que reemplaza los arranques separados
**When** `TELEGRAM_BOT_TOKEN` está configurado
**Then** se inicia el polling de Telegram
**And** cuando `WAHA_API_KEY` está configurado, se inicia FastAPI para webhooks WhatsApp
**And** cuando ambos están configurados, ambos corren en el mismo proceso
**And** cuando ninguno está configurado, se loggea error y el proceso termina
**And** un solo scheduler de recordatorios corre (no duplicados)
**And** Docker Compose define 2 services: `kalendbot` (build local) y `waha` (imagen WAHA)
**And** el webhook de WhatsApp solo es accesible dentro de la red Docker (puerto no expuesto)
**And** `kalendbot-data/` se monta como volumen para persistir datos

**Archivos:** `src/main.py` (nuevo), `Dockerfile`, `docker-compose.yml`

---

## Epic 9: Recordatorios Automatizados (Sin Agente)

**Goal:** Proceso autónomo que envía recordatorios sin consumir tokens LLM, usando el gateway configurado (no canal_preferido por contacto — eso depende de Epic 10).

### Story 9.1: Reminder Check Diario

Como administrador del calendario,
quiero que un proceso automático revise eventos próximos y genere recordatorios,
para que los contactos sean notificados sin intervención manual ni tokens LLM.

**Acceptance Criteria:**

**Given** un scheduler (cron o script programado) ejecutándose diariamente
**When** hay eventos dentro del rango de días configurado (ej: 7 días, 3 días, 1 día)
**Then** se genera una lista de recordatorios pendientes con evento, contactos, y template
**And** el proceso lee calendario-2026.json directamente sin pasar por el agente
**And** los templates se renderizan desde src/gateways/templates.py

**FRs cubiertos:** FR27
**Archivos:** `src/reminders/checker.py` (nuevo), `src/gateways/templates.py`

### Story 9.2: Delivery de Recordatorios

Como contacto del calendario,
quiero recibir recordatorios del bot,
para que no se me olviden los eventos próximos.

**Acceptance Criteria:**

**Given** recordatorios pendientes del check diario
**When** el sistema envía cada recordatorio
**Then** usa el gateway configurado (Telegram si TELEGRAM_BOT_TOKEN, WhatsApp si WAHA_API_KEY)
**And** si el envío falla, se loggea el error sin detener los demás envíos
**And** cada contacto asociado al evento recibe su recordatorio individual
**And** cuando Epic 10 implemente canal_preferido, el delivery se adapta sin cambios de interfaz

**FRs cubiertos:** FR28
**Archivos:** `src/reminders/sender.py` (nuevo), `src/gateways/dispatcher.py`

### Story 9.3: Historial de Recordatorios

Como administrador del calendario,
quiero un registro de qué recordatorios se enviaron, a quién y cuándo,
para que pueda verificar que el sistema funciona y diagnosticar fallos.

**Acceptance Criteria:**

**Given** cada envío de recordatorio (exitoso o fallido)
**When** se completa el delivery
**Then** se registra en un JSON de historial: evento_id, contacto_id, canal, timestamp, status (ok/error)
**And** el historial es consultable por el agente via tool o directamente
**And** no se duplican recordatorios ya enviados para el mismo evento+contacto+fecha

**FRs cubiertos:** FR29
**Archivos:** `src/reminders/history.py` (nuevo), `kalendbot-data/reminders/` (nuevo)

---

## Epic 10: Campos Fase 2

**Goal:** Extensión del sistema de edición para campos complejos que requieren lógica especial.

### Story 10.1: Edición de contacto_ids

Como administrador del calendario,
quiero agregar o quitar contactos asociados a un evento via chat,
para que pueda gestionar quién está vinculado a cada evento.

**Acceptance Criteria:**

**Given** un evento con contacto_ids existentes
**When** solicito agregar o quitar un contacto del evento
**Then** batch_preview muestra el cambio propuesto (contacto_ids antes/después)
**And** se valida que el contacto existe en kalendbot-data/contactos/
**And** el diagnóstico de impacto muestra efectos en recordatorios y permisos
**And** batch_confirm aplica el cambio tras aprobación

**FRs cubiertos:** FR30
**Archivos:** `src/tools/calendar_manager.py`

### Story 10.2: Canal Preferido y Texto Social

Como administrador del calendario,
quiero configurar el canal preferido de cada contacto y editar el texto social de eventos,
para que las comunicaciones usen el canal correcto y los eventos tengan texto para publicación.

**Acceptance Criteria:**

**Given** campo canal_preferido en el JSON del contacto y texto_social en el evento
**When** solicito editar estos campos
**Then** canal_preferido acepta valores: telegram, whatsapp
**And** texto_social acepta texto libre para publicación en redes/grupo
**And** ambos campos pasan por el flujo batch_preview/confirm estándar
**And** una vez implementado, Epic 9 (recordatorios) usa canal_preferido automáticamente via dispatcher

**FRs cubiertos:** FR31, FR32
**Archivos:** `src/tools/calendar_manager.py`, `kalendbot-data/config/instrucciones-edicion.json`

### Story 10.3: Gestión de Instancias Recurrentes

Como administrador del calendario,
quiero agregar o eliminar instancias individuales de eventos recurrentes,
para que pueda ajustar el calendario sin afectar la recurrencia base.

**Acceptance Criteria:**

**Given** un evento con recurrencia definida
**When** solicito agregar o eliminar una instancia específica
**Then** las instancias se gestionan como excepciones sobre la recurrencia base
**And** instancias eliminadas no aparecen en exportaciones ni recordatorios
**And** instancias agregadas se incluyen con los atributos del evento padre
**And** el cambio pasa por batch_preview/confirm con diagnóstico de impacto

**FRs cubiertos:** FR33
**Archivos:** `src/tools/calendar_manager.py`, `src/tools/calendar_exporter.py`

---

## Epic 11: Hardening Pre-producción

**Goal:** Persistencia real de MemorySaver y concurrent write safety para soportar multi-usuario en producción. Abstracción de data layer diferida (YAGNI — 30 eventos y 9 contactos no lo justifican).

### Story 11.1: Persistencia de MemorySaver

Como usuario que interactúa en múltiples sesiones,
quiero que mi historial de conversación persista entre reinicios del bot,
para que no pierda el contexto cuando el servidor se reinicia.

**Acceptance Criteria:**

**Given** MemorySaver actual es in-memory (se pierde al reiniciar)
**When** se migra a un checkpointer persistente
**Then** se usa SQLite como checkpointer (LangGraph SqliteSaver)
**And** el thread_id por contacto se mantiene como identificador
**And** la migración es transparente — handle_message no cambia su interfaz
**And** fallback a MemorySaver in-memory si SQLite no está disponible

**FRs cubiertos:** FR35
**Archivos:** `src/agent.py`

### Story 11.2: Concurrent Write Safety

Como sistema multi-usuario,
quiero que las escrituras concurrentes a datos no corrompan los archivos,
para que WhatsApp multi-usuario funcione de forma segura.

**Acceptance Criteria:**

**Given** múltiples usuarios enviando mensajes simultáneamente
**When** dos escrituras intentan modificar el mismo JSON
**Then** file locking (fcntl/portalocker) previene escrituras simultáneas
**And** los timeouts de lock se configuran en env vars
**And** un lock bloqueado loggea warning con el contacto que espera

**NFRs cubiertos:** NFR8
**Archivos:** `src/tools/calendar_manager.py`, helpers de file I/O
