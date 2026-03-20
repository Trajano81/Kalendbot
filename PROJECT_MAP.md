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
│   └── issues-cli-testing-002.md # Sesión 2: OBS-01 a 05 (fuzzy matching, conteo Koen, conflictos OK, estados evento, FAQ)
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
- [ ] OBS-01: Fuzzy matching en ContactManager (búsqueda por nombre parcial)
- [ ] OBS-02: Verificar asignación Nations League a Koen (requiere Excel)
- [ ] OBS-04: Sistema de estados de eventos (pendiente/confirmado/cancelado)
- [ ] OBS-05: FAQ document para ahorro de tokens
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
| OBS-01 | Agente no encuentra "Koen" por nombre parcial — falta fuzzy matching | Alta | 🔲 Pendiente |
| OBS-02 | Discrepancia conteo eventos Koen (10 vs 9) — verificar Nations League | Media | 🔲 Pendiente |
| OBS-03 | Verificación de conflictos 5 de mayo funciona correctamente | N/A | ✅ OK |
| OBS-04 | list_pending muestra todo sin distinción de estado | Alta | 🔲 Pendiente |
| OBS-05 | Consumo excesivo de tokens en preguntas frecuentes | Media | 🔲 Pendiente |

---

## Decisiones Clave

| Decisión | Razón |
|----------|-------|
| StructuredTool con Pydantic | Evita parsing JSON manual; OpenAI function calling llena cada campo |
| MemorySaver (LangGraph) | Reemplaza ConversationBufferMemory por contacto; usa thread_id |
| contact_id directo en CLI | Bypass de phone lookup para testing sin WhatsApp |
| recursion_limit: 25 | Previene loops infinitos de tool calls |
| Retry con backoff para 429 | Org con 200K TPM compartidos |
