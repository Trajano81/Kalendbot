---
epicId: EPIC-CAL-EXPORT
epicTitle: "Exportar Calendario JSON a Excel"
status: ready
priority: high
createdDate: 2026-03-24
author: Kmiloaparicio
stepsCompleted: ['requirements-extracted', 'stories-defined']
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '.claude/plans/mossy-meandering-micali.md'
relatedFiles:
  - 'src/tools/calendar_exporter.py (NUEVO)'
  - 'src/gateways/telegram_bot.py'
  - 'src/tools/__init__.py'
  - 'src/agent.py'
  - 'kalendbot-data/NV_2026_Jaarkalender V2.0.xlsx (template)'
---

# Epic: Exportar Calendario JSON a Excel

## Objetivo

Permitir la exportacion del calendario JSON (`calendario-{year}.json`) a formato Excel (.xlsx) manteniendo el formato original del archivo `NV_2026_Jaarkalender V2.0.xlsx`. Approach hibrido: script independiente (sin consumo de tokens) + LangChain tool opcional (para filtros inteligentes via chat).

## Justificacion

El calendario se mantiene en JSON como fuente de verdad, pero el equipo de NV Mexico necesita un Excel actualizado con el formato original para revision, impresion y distribucion. Actualmente no existe forma automatizada de generar este output.

## Requisitos Funcionales

- FR1: Exportar todos los eventos del calendario JSON a filas Excel con mapping de 20 columnas (A-T)
- FR2: Resolver nombres de proveedores (partner_id -> nombre) y contactos (contacto_ids -> nombre + telefono)
- FR3: Colorear filas por estado: confirmado=verde, pendiente=amarillo, cancelado=rojo
- FR4: Formatear fechas en holandes ("22 Januari", "15 Maart")
- FR5: Preservar estilos, anchos de columna y formato del Excel original como template
- FR6: Comando `/exportar` en Telegram que genera y envia el XLSX sin consumir tokens
- FR7: CLI entry point `python -m src.tools.calendar_exporter` para exportacion directa
- FR8: LangChain tool con filtros opcionales (year, status, contacto) para uso via chat
- FR9: Mapear canales de promocion a columnas booleanas ("x"): whatsapp, rrss, email, eventbrite, reel

## Requisitos No Funcionales

- NFR1: El comando `/exportar` y CLI NO deben consumir tokens del agente
- NFR2: Solo el uso via chat (LangChain tool con filtros) consume tokens
- NFR3: El archivo generado debe ser compatible con Excel y Google Sheets

## Mapping de Columnas (A-T)

| Col | Header | JSON field |
|-----|--------|------------|
| A | Estado | estado |
| B | Datum | fecha -> texto NL ("22 Januari") |
| C | Activiteit | nombre |
| D | Partner | partner_id -> nombre del proveedor |
| E | Locatie | venue_nombre |
| F | 1 omschrijving | descripcion |
| G | 2 Tijdstip | hora |
| H | 3 Entree | precio |
| I | 4 Adres | venue_direccion |
| J | 5 Info post/FLYER | detalle |
| K | 6 flyer moment | flyer_moment |
| L | 7 contact persoon | contacto_ids -> nombre |
| M | 8 Celular | telefono del contacto |
| N | Flyer voor event | flyer_oleadas o "x" |
| O | reel na event | reel_post -> "x" |
| P | eventbrite | eventbrite -> "x" |
| Q | whats | "whatsapp" in canales -> "x" |
| R | inst FB TT | "rrss" in canales -> "x" |
| S | email | "email" in canales -> "x" |
| T | Texto Socials | texto_social |

---

## Epic List

- Story 1.1: Funcion principal de exportacion JSON -> Excel
- Story 1.2: Comando /exportar en Telegram Bot
- Story 1.3: LangChain tool wrapper con filtros
- Story 1.4: Registro del tool en agent y __init__

---

## Story 1.1: Funcion principal de exportacion JSON -> Excel

As a **administrador de NV Mexico**,
I want **exportar el calendario JSON a un archivo Excel con el formato original**,
So that **el equipo pueda revisar, imprimir y distribuir el calendario actualizado**.

**Archivo:** `src/tools/calendar_exporter.py` (NUEVO)

**Acceptance Criteria:**

**Given** el archivo `calendario-2026.json` existe con eventos
**When** se ejecuta `export_calendar(year=2026)`
**Then** se genera `kalendbot-data/NV_2026_Jaarkalender_UPDATED.xlsx`
**And** cada evento ocupa una fila con las 20 columnas (A-T) mapeadas correctamente

**Given** un evento con `partner_id: "holanda-tours"`
**When** se exporta a Excel
**Then** la columna D muestra el nombre del proveedor resuelto desde `proveedores/{partner_id}.json`

**Given** un evento con `estado: "confirmado"`
**When** se exporta a Excel
**Then** la fila tiene fondo verde

**Given** un evento con `estado: "pendiente"`
**When** se exporta a Excel
**Then** la fila tiene fondo amarillo

**Given** un evento con `estado: "cancelado"`
**When** se exporta a Excel
**Then** la fila tiene fondo rojo

**Given** un evento con `fecha: "2026-01-22"`
**When** se exporta a Excel
**Then** la columna B muestra "22 Januari" (formato holandes)

**Given** un evento con `canales: ["whatsapp", "rrss", "email"]`
**When** se exporta a Excel
**Then** las columnas Q, R, S muestran "x" y las demas quedan vacias

**Given** se ejecuta `python -m src.tools.calendar_exporter` desde CLI
**When** el script termina
**Then** genera el XLSX y retorna el path del archivo sin consumir tokens

---

## Story 1.2: Comando /exportar en Telegram Bot

As a **usuario de Telegram (admin/tester)**,
I want **ejecutar `/exportar` en el chat con el bot**,
So that **reciba el archivo Excel actualizado directamente en Telegram sin costo de tokens**.

**Archivo:** `src/gateways/telegram_bot.py`

**Acceptance Criteria:**

**Given** un usuario con rol admin o tester en Telegram
**When** envia el comando `/exportar`
**Then** el bot genera el XLSX llamando a `export_calendar()` directamente (sin LLM)
**And** envia el archivo como documento adjunto en el chat

**Given** un usuario con rol readonly en Telegram
**When** envia el comando `/exportar`
**Then** el bot responde con mensaje de permisos insuficientes

**Given** la generacion del XLSX falla
**When** ocurre un error
**Then** el bot responde con mensaje de error descriptivo

---

## Story 1.3: LangChain tool wrapper con filtros

As a **usuario del chat con el agente**,
I want **pedir exportaciones filtradas como "exporta solo los pendientes de mayo"**,
So that **obtenga archivos Excel personalizados segun mis necesidades**.

**Archivo:** `src/tools/calendar_exporter.py`

**Acceptance Criteria:**

**Given** un usuario pide "exporta el calendario" via chat
**When** el agente invoca CalendarExporter sin filtros
**Then** se genera el XLSX completo y se retorna el path

**Given** un usuario pide "exporta solo los eventos pendientes"
**When** el agente invoca CalendarExporter con `filter_status="pendiente"`
**Then** el XLSX solo contiene eventos con estado pendiente

**Given** el tool se usa via LangChain
**When** se ejecuta
**Then** consume tokens del agente (comportamiento esperado para filtros inteligentes)

---

## Story 1.4: Registro del tool en agent y __init__

As a **desarrollador**,
I want **que CalendarExporter este registrado en el sistema de tools**,
So that **el agente pueda usarlo cuando el usuario lo solicite via chat**.

**Archivos:** `src/tools/__init__.py`, `src/agent.py`

**Acceptance Criteria:**

**Given** el tool `calendar_exporter_tool` esta definido
**When** se importa en `__init__.py`
**Then** aparece en `WRITE_TOOLS` y `ALL_TOOLS`

**Given** el system prompt del agente
**When** se revisa la lista de herramientas
**Then** CalendarExporter esta listado con su descripcion

---

## Modos de Uso

| Modo | Consume tokens | Como |
|------|---------------|------|
| Comando `/exportar` en Telegram | NO | Handler directo |
| CLI `python -m src.tools.calendar_exporter` | NO | Script directo |
| "exporta solo los pendientes de mayo" via chat | SI | LangChain tool con filtros |

## Verificacion

1. `python -m src.tools.calendar_exporter` -> genera XLSX
2. `/exportar` en Telegram -> recibe archivo
3. "exporta el calendario" via chat -> usa LangChain tool
4. Abrir XLSX y comparar con formato original
