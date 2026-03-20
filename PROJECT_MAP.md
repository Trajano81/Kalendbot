# KalendBot — Mapa del Proyecto

Bot inteligente de gestión de calendario para NV Mexico (Asociación Neerlandesa en México).
Coordina 31 eventos anuales con 9 proveedores/contactos vía WhatsApp.

---

## Estructura del Proyecto

```
KalendBot/
├── src/                          # Código fuente
│   ├── agent.py                  # Agente LangChain (create_agent + MemorySaver)
│   ├── cli.py                    # CLI para testing local sin WhatsApp
│   ├── server.py                 # Servidor HTTP (webhook WhatsApp)
│   ├── memory.py                 # ProviderMemoryManager (legacy, MemorySaver lo reemplaza)
│   ├── gateways/                 # Integraciones externas (Evolution API - pendiente)
│   └── tools/                    # 8 herramientas del agente
│       ├── calendar_manager.py   # CRUD calendario (StructuredTool)
│       ├── contact_manager.py    # Gestión contactos (Tool, string input)
│       ├── provider_manager.py   # Gestión proveedores (Tool, string input)
│       ├── conflict_detector.py  # Detección conflictos de fechas (Tool)
│       ├── date_locker.py        # Bloqueo/desbloqueo fechas (StructuredTool)
│       ├── flyer_manager.py      # Flujo de flyers (StructuredTool)
│       ├── group_notifier.py     # Notificaciones grupales (Tool)
│       └── rules_engine.py       # Reglas de negocio: tiers, precedencia, restricciones
│
├── kalendbot-data/               # Datos JSON (fuente de verdad)
│   ├── calendario-2026.json      # 31 eventos con fechas, estados, contactos
│   ├── contactos/                # Personas físicas (1 JSON por contacto)
│   ├── proveedores/              # Organizaciones (1 JSON por proveedor)
│   ├── config/                   # Configuración de reglas de negocio
│   │   ├── tiers-promocion.json  # Tiers de promoción (A/B/C/D)
│   │   ├── precedencia.json      # Reglas de precedencia y compatibilidad
│   │   ├── restricciones.json    # Feriados y reglas implícitas
│   │   └── eventos-externos-2026.json  # Eventos externos relevantes
│   ├── schemas/                  # JSON schemas de validación
│   └── memories/                 # Memorias de conversación (runtime, en .gitignore)
│
├── docs/                         # Documentación de desarrollo
│   ├── issues-cli-testing-001.md # Sesión 1: ISSUE-01 a 05 (CLI phone, recursion, memoria, tools frágiles, RulesEngine)
│   ├── issues-cli-testing-002.md # Sesión 2: OBS-01 a 05 (fuzzy matching, conteo Koen, conflictos OK, estados evento, FAQ)
│   └── issues-cli-testing-003.md # Sesión 3: Validación OBS-01/04/05 fixes — 25/25 tests PASS
│
├── .claude/memory/               # Memoria persistente de Claude Code
│   ├── MEMORY.md                 # Índice de memorias
│   ├── user_profile.md           # Perfil del usuario
│   ├── feedback_no_coauthor.md   # Sin Co-Authored-By en commits
│   ├── project_pending_obs.md    # Trabajo pendiente (sesión 002)
│   └── reference_data_structure.md # Estructura de datos del proyecto
│
├── NV_Mexico_2026_Analisis_Calendario.md  # Análisis inicial del calendario
├── PROJECT_MAP.md                # ← Este archivo
├── .env                          # API keys (en .gitignore)
└── .gitignore
```

---

## Estado del Desarrollo

**Branch:** `development` (8 commits adelante de `main`)

### Completado
- [x] MVP: Agente LangChain con 8 tools
- [x] CLI para testing local
- [x] Migración a LangChain 1.2.12 (create_agent + MemorySaver)
- [x] Fix ISSUE-01/03: CLI pasa contact_id directo al agente
- [x] Fix ISSUE-02/04: Migración a StructuredTool (CalendarManager, DateLocker, FlyerManager)
- [x] Fix ISSUE-05: Eliminación de recursión en RulesEngine

### Pendiente (ver docs/issues-cli-testing-002.md)
- [x] OBS-01: Fuzzy matching en ContactManager (search:nombre, búsqueda parcial case-insensitive)
- [ ] OBS-02: Verificar asignación Nations League a Koen (requiere Excel)
- [x] OBS-04: Sistema de estados (pendiente/confirmado/cancelado) + list_pending filtra pasados/futuros + list_upcoming
- [x] OBS-05: FAQ document para ahorro de tokens (kalendbot-data/config/faq.json)
- [ ] Integración WhatsApp vía Evolution API

---

## Issues y Observaciones

### Sesión 1 → [docs/issues-cli-testing-001.md](docs/issues-cli-testing-001.md)
| ID | Descripción | Severidad | Estado |
|----|-------------|-----------|--------|
| ISSUE-01 | CLI phone simulation rota — contactos simulados nunca matchean | Alta | ✅ Resuelto |
| ISSUE-02 | Recursion limit por tool call loop infinito | Alta | ✅ Resuelto |
| ISSUE-03 | Memoria asignada a contacto incorrecto (`unknown-jsse`) | Alta | ✅ Resuelto |
| ISSUE-04 | Tools con input multi-parámetro son frágiles (Tool → StructuredTool) | Alta | ✅ Resuelto |
| ISSUE-05 | RulesEngine recursión interna en query "all" | Media | ✅ Resuelto |

### Sesión 2 → [docs/issues-cli-testing-002.md](docs/issues-cli-testing-002.md)
| ID | Descripción | Severidad | Estado |
|----|-------------|-----------|--------|
| OBS-01 | Agente no encuentra "Koen" por nombre parcial — falta fuzzy matching | Alta | ✅ Resuelto |
| OBS-02 | Discrepancia conteo eventos Koen (10 vs 9) — verificar Nations League | Media | 🔲 Pendiente |
| OBS-03 | Verificación de conflictos 5 de mayo funciona correctamente | N/A | ✅ OK |
| OBS-04 | list_pending muestra todo sin distinción de estado | Alta | ✅ Resuelto |
| OBS-05 | Consumo excesivo de tokens en preguntas frecuentes | Media | ✅ Resuelto |

---

## Decisiones Clave

| Decisión | Razón |
|----------|-------|
| StructuredTool con Pydantic | Evita parsing JSON manual; OpenAI function calling llena cada campo |
| MemorySaver (LangGraph) | Reemplaza ConversationBufferMemory por contacto; usa thread_id |
| contact_id directo en CLI | Bypass de phone lookup para testing sin WhatsApp |
| recursion_limit: 25 | Previene loops infinitos de tool calls |
| Retry con backoff para 429 | Org con 200K TPM compartidos |

---

## Roadmap de Desarrollo

### Fase 1: Estabilización del agente (actual)
> Objetivo: que el agente funcione correctamente vía CLI antes de conectar WhatsApp.

- [x] OBS-01: Fuzzy matching en ContactManager
- [ ] OBS-02: Verificar asignación Nations League
- [x] OBS-04: Sistema de estados de eventos
- [x] OBS-05: FAQ document para ahorro de tokens
- [ ] Testing CLI sesión 003: validar OBS-01/04/05 fixes + escenarios pendientes

### Fase 2: Integración WhatsApp — Evolution API
> Objetivo: recibir y responder mensajes reales de WhatsApp.

- [ ] Investigar Evolution API: endpoints, autenticación, webhooks
- [ ] Configurar instancia Evolution API (self-hosted o cloud)
- [ ] Implementar gateway WhatsApp (`src/gateways/evolution.py`)
  - Webhook para recibir mensajes entrantes
  - Envío de respuestas al contacto
  - Mapeo teléfono → contact_id (ya preparado en `handle_message`)
- [ ] Conectar `server.py` con el gateway
- [ ] Testing con número real (sandbox o número de prueba)
- [ ] Manejo de media: recibir/enviar imágenes de flyers

### Fase 3: Flujos de negocio completos
> Objetivo: que el bot maneje los flujos reales de NV Mexico.

- [ ] Flujo de confirmación de fechas con proveedores
- [ ] Flujo de solicitud y aprobación de flyers
- [ ] Notificaciones grupales (recordatorios, cambios de fecha)
- [ ] Escalamiento: cuando el bot no puede resolver → notificar a Kmilo/Hanna
- [ ] Reportes: resumen semanal/mensual del estado del calendario

### Fase 4: Producción
> Objetivo: bot operando en el día a día de NV Mexico.

- [ ] Seguridad: validar que solo contactos autorizados interactúen
- [ ] Logging y monitoreo de conversaciones
- [ ] Backup de datos (calendario, memorias)
- [ ] Documentación de uso para el equipo NV Mexico
- [ ] Deploy (servidor, dominio, SSL para webhook)
