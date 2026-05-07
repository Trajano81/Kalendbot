---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/project-context.md'
  - '.claude/plans/mossy-meandering-micali.md'
epicType: retrospective
---

# Kalendbot - Epic Breakdown (Retrospectivo)

## Overview

Este documento registra las épicas y stories del trabajo ya completado en KalendBot, proporcionando una línea base para tracking, sprint planning y retrospectivas futuras. Todas las épicas tienen estado DONE.

## Requirements Inventory

### Functional Requirements

FR1: Agente conversacional LangChain con GPT-4o-mini que procesa mensajes en español
FR2: CalendarManager — CRUD de 30 eventos con estados (pendiente/confirmado/cancelado)
FR3: ContactManager — búsqueda fuzzy de contactos por nombre parcial
FR4: ProviderManager — consulta de organizaciones/partners por ID
FR5: ConflictDetector — validación de fechas contra feriados, eventos y reglas implícitas
FR6: DateLocker — bloqueo/desbloqueo de fechas de eventos
FR7: FlyerManager — flujo de flyers (request→approve→remind) con Rocco como observer
FR8: GroupNotifier — publicación en grupo de Telegram
FR9: RulesEngine — consulta de reglas de negocio (tiers, precedencia, restricciones, instrucciones)
FR10: CalendarExporter — exportación a Excel (.xlsx) con template V3 multi-idioma (dut/eng/spa/por)
FR11: JPEG export — renderizado HTML+Chrome con logos y diseño de referencia
FR12: show_in_export — control de visibilidad de eventos en exportaciones
FR13: Recurring event expansion — instancias individuales desde eventos recurrentes
FR14: Telegram bot — registro de usuarios, aprobación admin, comandos /export_*
FR15: RBAC — 4 roles (admin/tester/contacto/readonly) con system prompt dinámico
FR16: Field-level permissions — campos owner vs admin en edición
FR17: Batch field editing — preview→confirm→undo con diagnóstico de impacto
FR18: 22 campos editables con validación por tipo (date, bool, int, enum, precio, text)
FR19: FAQ bypass — respuestas sin LLM para preguntas frecuentes
FR20: MemorySaver — persistencia de conversación por contacto (thread_id)

### NonFunctional Requirements

NFR1: Rate limit handling — retry con backoff exponencial (3 intentos)
NFR2: Tool outputs siempre retornan str (nunca dict/list/None)
NFR3: JSON I/O con encoding UTF-8 y ensure_ascii=False
NFR4: Recursion limit 25 en el agente
NFR5: Logging con getLogger("kalendbot.*"), nunca print()
NFR6: Error handling descriptivo en tools (strings, no excepciones)
NFR7: Data Dir configurable via KALENDBOT_DATA_DIR env var

### Additional Requirements

- Gateway-agnostic: schemas Pydantic independientes del canal de entrada
- Una tool por archivo en src/tools/ con export en __init__.py
- StructuredTool con Pydantic BaseModel para tools multi-parámetro
- Imports absolutos (from src.tools import ALL_TOOLS)
- Helpers privados (_prefijo) dentro del mismo archivo

### UX Design Requirements

N/A — proyecto conversational-first sin UI visual propia.

### FR Coverage Map

FR1:  Epic 1 — Agente LangChain conversacional con GPT-4o-mini
FR2:  Epic 2 — CalendarManager CRUD de eventos
FR3:  Epic 2 — ContactManager búsqueda fuzzy
FR4:  Epic 2 — ProviderManager consulta partners
FR5:  Epic 2 — ConflictDetector validación de fechas
FR6:  Epic 2 — DateLocker bloqueo/desbloqueo
FR7:  Epic 2 — FlyerManager flujo completo
FR8:  Epic 2 — GroupNotifier publicaciones grupo
FR9:  Epic 2 — RulesEngine reglas de negocio
FR10: Epic 3 — CalendarExporter Excel V3 multi-idioma
FR11: Epic 3 — JPEG export HTML+Chrome
FR12: Epic 3 — show_in_export visibilidad
FR13: Epic 3 — Recurring event expansion
FR14: Epic 4 — Telegram bot completo
FR15: Epic 5 — RBAC 4 roles con system prompt dinámico
FR16: Epic 5 — Field-level permissions (owner vs admin)
FR17: Epic 6 — Batch editing preview/confirm/undo
FR18: Epic 6 — 22 campos con validación por tipo
FR19: Epic 1 — FAQ bypass pre-agente
FR20: Epic 1 — MemorySaver persistencia por contacto

NFR1-NFR7: Epic 1 — Aplicados transversalmente en la plataforma del agente

## Epic List

### Epic 1: Plataforma del Agente Conversacional
El agente LangChain procesa mensajes en español, persiste conversaciones por contacto, y responde FAQs sin consumir tokens. Es la base sobre la que operan todas las tools y gateways.
**FRs cubiertos:** FR1, FR19, FR20
**NFRs cubiertos:** NFR1-NFR7
**Estado:** DONE
**Archivos clave:** `src/agent.py`, `src/cli.py`

### Epic 2: Tools de Dominio del Calendario
8 herramientas especializadas que permiten al agente consultar eventos, buscar contactos/proveedores, detectar conflictos, bloquear fechas, gestionar flyers, notificar al grupo y consultar reglas de negocio.
**FRs cubiertos:** FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9
**Estado:** DONE
**Archivos clave:** `src/tools/calendar_manager.py`, `src/tools/contact_manager.py`, `src/tools/provider_manager.py`, `src/tools/conflict_detector.py`, `src/tools/date_locker.py`, `src/tools/flyer_manager.py`, `src/tools/group_notifier.py`, `src/tools/rules_engine.py`

### Epic 3: Exportación Multi-formato y Multi-idioma
Los usuarios exportan el calendario a Excel (.xlsx) y JPEG en 4 idiomas, con expansión de eventos recurrentes, resolución de venues desde proveedores, y control de visibilidad por evento.
**FRs cubiertos:** FR10, FR11, FR12, FR13
**Estado:** DONE
**Archivos clave:** `src/tools/calendar_exporter.py`

### Epic 4: Acceso Multi-usuario via Telegram
Los usuarios acceden al bot via Telegram con registro por contacto compartido, aprobación de admin, comandos /export_excel, /export_jpeg, /export_instructions, soporte de grupo y recordatorios programados.
**FRs cubiertos:** FR14
**Estado:** DONE
**Archivos clave:** `src/gateways/telegram_bot.py`

### Epic 5: Control de Acceso y Permisos por Rol
Cada usuario opera dentro de su rol (admin/tester/contacto/readonly) con system prompt dinámico que restringe automáticamente las acciones disponibles. Los campos de eventos tienen permisos a nivel de field (owner vs admin).
**FRs cubiertos:** FR15, FR16
**Estado:** DONE
**Archivos clave:** `src/agent.py` (ROLE_SUFFIX_*), `src/tools/calendar_manager.py` (_check_field_permission)

### Epic 6: Edición de Campos con Diagnóstico de Impacto
Los usuarios modifican cualquier campo de un evento via chat con preview de cambios, diagnóstico de impacto en procesos downstream (recordatorios, conflictos, flyers, grupo, export), y capacidad de deshacer la última edición.
**FRs cubiertos:** FR17, FR18
**Estado:** DONE (uncommitted)
**Archivos clave:** `src/tools/calendar_manager.py` (batch_preview, batch_confirm, undo_last), `kalendbot-data/config/instrucciones-edicion.json`

---

## Epic 1: Plataforma del Agente Conversacional

**Goal:** Establecer la base conversacional del sistema — el agente LangChain que procesa español, persiste conversaciones por contacto, y responde FAQs sin consumir tokens LLM.

### Story 1.1: Agente Conversacional con LangChain y GPT-4o-mini

Como administrador del calendario,
quiero un agente conversacional que procese mis mensajes en español usando GPT-4o-mini,
para que pueda gestionar el calendario de eventos mediante lenguaje natural.

**Acceptance Criteria:**

- El agente utiliza LangChain con GPT-4o-mini como LLM
- Procesa mensajes en español correctamente
- Tiene system prompt con contexto del dominio KalendBot
- Aplica recursion limit de 25 (NFR4)
- Rate limit handling con backoff exponencial de 3 intentos (NFR1)
- Logging via getLogger("kalendbot.*") sin print() (NFR5)
- Tool outputs retornan siempre str (NFR2)
- JSON I/O con UTF-8 y ensure_ascii=False (NFR3)
- Error handling descriptivo en strings (NFR6)
- Data Dir configurable via KALENDBOT_DATA_DIR (NFR7)

**FRs cubiertos:** FR1
**NFRs cubiertos:** NFR1-NFR7
**Archivos:** `src/agent.py`, `src/cli.py`

### Story 1.2: FAQ Bypass Pre-Agente

Como usuario frecuente,
quiero que las preguntas frecuentes se respondan instantáneamente sin pasar por el LLM,
para que obtenga respuestas rápidas y se reduzca el consumo de tokens.

**Acceptance Criteria:**

- Sistema de FAQ detecta preguntas frecuentes antes de invocar al agente
- Respuestas predefinidas se entregan sin consumir tokens GPT
- Si la pregunta no matchea FAQ, se pasa al agente normalmente
- El matching evita falsos positivos (strings parciales que no son FAQ)

**FRs cubiertos:** FR19
**Archivos:** `src/agent.py`

### Story 1.3: Persistencia de Conversación por Contacto

Como usuario que interactúa en múltiples sesiones,
quiero que el bot recuerde el contexto de mi conversación anterior,
para que no tenga que repetir información entre sesiones.

**Acceptance Criteria:**

- MemorySaver persiste el historial de conversación por thread_id
- Cada contacto tiene su propio thread_id independiente
- El historial se recupera correctamente al iniciar nueva sesión
- La persistencia funciona tanto en CLI como en Telegram

**FRs cubiertos:** FR20
**Archivos:** `src/agent.py`

---

## Epic 2: Tools de Dominio del Calendario

**Goal:** Proveer al agente de 8 herramientas especializadas que cubren todo el dominio operativo del calendario — desde CRUD de eventos hasta reglas de negocio.

### Story 2.1: Consulta y Gestión de Eventos

Como administrador del calendario,
quiero consultar, listar y gestionar los 30 eventos del calendario con sus estados,
para que pueda tener visibilidad completa de la programación.

**Acceptance Criteria:**

- CalendarManager soporta acciones: list, get, update sobre eventos
- Los eventos tienen estados: pendiente, confirmado, cancelado
- Se pueden filtrar eventos por estado, fecha, o nombre
- Los datos se leen/escriben desde calendario-2026.json
- Tool output siempre retorna str (NFR2)

**FRs cubiertos:** FR2
**Archivos:** `src/tools/calendar_manager.py`

### Story 2.2: Búsqueda de Contactos y Proveedores

Como administrador del calendario,
quiero buscar contactos por nombre parcial y consultar proveedores/organizaciones,
para que pueda asociar personas y entidades a los eventos.

**Acceptance Criteria:**

- ContactManager implementa búsqueda fuzzy por nombre parcial
- ProviderManager consulta organizaciones/partners por ID
- La búsqueda fuzzy tolera errores tipográficos y nombres parciales
- Los resultados incluyen toda la información relevante del contacto/proveedor

**FRs cubiertos:** FR3, FR4
**Archivos:** `src/tools/contact_manager.py`, `src/tools/provider_manager.py`

### Story 2.3: Detección de Conflictos y Bloqueo de Fechas

Como administrador del calendario,
quiero validar fechas contra feriados/eventos existentes y bloquear/desbloquear fechas,
para que pueda evitar conflictos de programación y reservar fechas.

**Acceptance Criteria:**

- ConflictDetector valida fechas contra feriados nacionales
- ConflictDetector valida contra eventos existentes en el calendario
- ConflictDetector aplica reglas implícitas de conflicto
- DateLocker permite bloquear fechas para un evento específico
- DateLocker permite desbloquear fechas previamente bloqueadas
- Se reportan todos los conflictos encontrados con detalle

**FRs cubiertos:** FR5, FR6
**Archivos:** `src/tools/conflict_detector.py`, `src/tools/date_locker.py`

### Story 2.4: Gestión de Flyers y Notificaciones de Grupo

Como administrador del calendario,
quiero gestionar el flujo de flyers (request→approve→remind) y publicar en el grupo de Telegram,
para que los eventos tengan material promocional y se comuniquen al grupo.

**Acceptance Criteria:**

- FlyerManager soporta flujo completo: request, approve, remind
- Rocco está configurado como observer del flujo de flyers
- GroupNotifier publica mensajes en el grupo de Telegram
- Los estados de flyer se persisten correctamente en el JSON del evento

**FRs cubiertos:** FR7, FR8
**Archivos:** `src/tools/flyer_manager.py`, `src/tools/group_notifier.py`

### Story 2.5: Consulta de Reglas de Negocio

Como administrador del calendario,
quiero consultar las reglas de negocio (tiers, precedencia, restricciones, instrucciones),
para que las decisiones del calendario se basen en las políticas establecidas.

**Acceptance Criteria:**

- RulesEngine consulta reglas por tópico: tiers, precedencia, restricciones, instrucciones
- Las reglas se cargan desde archivos de configuración JSON
- Las respuestas incluyen el contexto completo de la regla consultada
- El tópico "instrucciones" retorna las instrucciones de edición de campos

**FRs cubiertos:** FR9
**Archivos:** `src/tools/rules_engine.py`

---

## Epic 3: Exportación Multi-formato y Multi-idioma

**Goal:** Permitir la exportación del calendario a Excel (.xlsx) y JPEG en 4 idiomas, con expansión de recurrentes, resolución de venues, y control de visibilidad.

### Story 3.1: Exportación Excel V3 Multi-idioma

Como administrador del calendario,
quiero exportar el calendario a Excel (.xlsx) en 4 idiomas (holandés, inglés, español, portugués),
para que los diferentes stakeholders reciban el calendario en su idioma.

**Acceptance Criteria:**

- CalendarExporter genera archivo .xlsx con template V3
- Soporta 4 idiomas: dut (holandés), eng (inglés), spa (español), por (portugués)
- Los headers y contenido se traducen según el idioma seleccionado
- Los venues se resuelven desde los datos de proveedores
- El archivo se genera correctamente y es válido para Excel

**FRs cubiertos:** FR10
**Archivos:** `src/tools/calendar_exporter.py`

### Story 3.2: Exportación JPEG con Diseño de Referencia

Como administrador del calendario,
quiero exportar el calendario como imagen JPEG con logos y diseño profesional,
para que pueda compartirlo visualmente en redes y grupos.

**Acceptance Criteria:**

- CalendarExporter genera JPEG mediante renderizado HTML+Chrome
- La imagen incluye logos según el diseño de referencia
- El layout es legible y profesionalmente diseñado
- Chrome headless se usa para el renderizado HTML→JPEG

**FRs cubiertos:** FR11
**Archivos:** `src/tools/calendar_exporter.py`

### Story 3.3: Control de Visibilidad y Eventos Recurrentes

Como administrador del calendario,
quiero controlar qué eventos aparecen en las exportaciones y expandir eventos recurrentes,
para que las exportaciones reflejen exactamente lo que debe mostrarse.

**Acceptance Criteria:**

- Campo show_in_export controla la visibilidad de cada evento en exportaciones
- Eventos con show_in_export=false se excluyen de Excel y JPEG
- Eventos recurrentes se expanden en instancias individuales con fechas específicas
- Las instancias expandidas heredan los atributos del evento padre
- La expansión respeta el rango de fechas del calendario

**FRs cubiertos:** FR12, FR13
**Archivos:** `src/tools/calendar_exporter.py`

---

## Epic 4: Acceso Multi-usuario via Telegram

**Goal:** Proveer acceso multi-usuario al bot via Telegram con registro por contacto, aprobación de admin, comandos de exportación, soporte de grupo y mensajería programada.

### Story 4.1: Registro de Usuarios y Aprobación Admin

Como nuevo usuario de Telegram,
quiero registrarme compartiendo mi contacto y ser aprobado por el admin,
para que pueda acceder al bot con mi rol asignado.

**Acceptance Criteria:**

- El bot acepta contactos compartidos para registro de nuevos usuarios
- El admin recibe notificación de solicitud de registro
- El admin puede aprobar o rechazar usuarios
- Al aprobar, se asigna un rol (admin/tester/contacto/readonly)
- El usuario registrado se vincula con su contacto en kalendbot-data

**FRs cubiertos:** FR14 (registro y aprobación)
**Archivos:** `src/gateways/telegram_bot.py`

### Story 4.2: Comandos de Exportación via Telegram

Como usuario aprobado de Telegram,
quiero usar comandos /export_excel, /export_jpeg y /export_instructions,
para que pueda recibir las exportaciones directamente en el chat.

**Acceptance Criteria:**

- Comando /export_excel genera y envía el archivo .xlsx al chat
- Comando /export_jpeg genera y envía la imagen al chat
- Comando /export_instructions envía las instrucciones de edición
- Los comandos respetan los permisos del rol del usuario
- Se manejan errores de generación con mensajes descriptivos

**FRs cubiertos:** FR14 (comandos export)
**Archivos:** `src/gateways/telegram_bot.py`

### Story 4.3: Soporte de Grupo y Mensajería

Como administrador del calendario,
quiero que el bot funcione en grupos de Telegram y pueda enviar mensajes programados,
para que el grupo reciba actualizaciones y recordatorios automáticos.

**Acceptance Criteria:**

- El bot funciona en chats individuales y en grupos de Telegram
- En grupos, el bot responde a mensajes dirigidos a él
- Se pueden programar recordatorios para envío automático
- Los mensajes de grupo se formatean correctamente para Telegram

**FRs cubiertos:** FR14 (grupo y mensajería)
**Archivos:** `src/gateways/telegram_bot.py`

---

## Epic 5: Control de Acceso y Permisos por Rol

**Goal:** Cada usuario opera dentro de su rol con restricciones automáticas via system prompt dinámico, y los campos de eventos tienen permisos diferenciados por rol.

### Story 5.1: System Prompt Dinámico por Rol

Como administrador del sistema,
quiero que cada usuario reciba un system prompt adaptado a su rol,
para que las acciones disponibles se restrinjan automáticamente según sus permisos.

**Acceptance Criteria:**

- 4 roles definidos: admin, tester, contacto, readonly
- Cada rol tiene un ROLE_SUFFIX específico que se añade al system prompt
- El rol admin tiene acceso completo a todas las tools
- El rol readonly no puede modificar datos
- El rol contacto solo accede a eventos donde es owner
- El rol tester tiene acceso amplio para pruebas

**FRs cubiertos:** FR15
**Archivos:** `src/agent.py` (ROLE_SUFFIX_*)

### Story 5.2: Permisos de Campo por Rol (Owner vs Admin)

Como administrador del sistema,
quiero que ciertos campos de eventos solo sean editables por el owner o admin,
para que la integridad de datos críticos esté protegida por permisos a nivel de campo.

**Acceptance Criteria:**

- _check_field_permission valida permisos antes de cada edición
- Campos owner-only: solo editables por el contacto owner del evento
- Campos admin-only: solo editables por usuarios con rol admin
- Intentos de edición sin permiso retornan mensaje descriptivo
- La validación se aplica en batch_preview antes de mostrar el preview

**FRs cubiertos:** FR16
**Archivos:** `src/tools/calendar_manager.py` (_check_field_permission)

---

## Epic 6: Edición de Campos con Diagnóstico de Impacto

**Goal:** Los usuarios modifican campos de eventos via chat con preview, diagnóstico de impacto en procesos downstream, confirmación explícita, y capacidad de deshacer.

### Story 6.1: Preview de Cambios con Diagnóstico de Impacto

Como administrador del calendario,
quiero ver un preview de los cambios propuestos con diagnóstico de impacto antes de confirmar,
para que pueda evaluar las consecuencias de cada edición antes de aplicarla.

**Acceptance Criteria:**

- batch_preview acepta cambios en formato pipe-separated (campo|valor)
- El preview muestra valor actual vs valor propuesto para cada campo
- El diagnóstico de impacto evalúa efectos en: recordatorios, conflictos, flyers, grupo, export
- Se validan los 22 campos editables por tipo (date, bool, int, enum, precio, text)
- Se aplican permisos de campo antes de generar el preview
- Cambios inválidos se reportan con mensaje descriptivo

**FRs cubiertos:** FR17, FR18
**Archivos:** `src/tools/calendar_manager.py` (batch_preview), `kalendbot-data/config/instrucciones-edicion.json`

### Story 6.2: Confirmación y Aplicación de Cambios

Como administrador del calendario,
quiero confirmar los cambios previsualizados para que se apliquen al evento,
para que los cambios solo se persistan después de mi aprobación explícita.

**Acceptance Criteria:**

- batch_confirm aplica los cambios previamente previsualizados
- Solo se pueden confirmar cambios que pasaron el preview exitosamente
- Los cambios se persisten en el JSON del evento
- Se guarda snapshot del estado anterior para posible undo
- Se retorna confirmación con resumen de campos modificados

**FRs cubiertos:** FR17
**Archivos:** `src/tools/calendar_manager.py` (batch_confirm)

### Story 6.3: Deshacer Última Edición

Como administrador del calendario,
quiero deshacer la última edición aplicada a un evento,
para que pueda revertir cambios erróneos sin intervención manual en los archivos.

**Acceptance Criteria:**

- undo_last revierte el evento al estado anterior a la última edición
- Solo se puede deshacer la edición más reciente (1 nivel)
- Se muestra resumen de qué campos fueron revertidos
- Si no hay edición previa para deshacer, se informa al usuario
- El undo se persiste inmediatamente en el JSON

**FRs cubiertos:** FR17
**Archivos:** `src/tools/calendar_manager.py` (undo_last)
