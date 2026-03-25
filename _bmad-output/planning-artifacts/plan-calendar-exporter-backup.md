# Plan: Exportar calendario JSON a Excel — Hibrido (script + LangChain tool)

> Backup del plan original creado el 2026-03-24. Fuente: `.claude/plans/mossy-meandering-micali.md`

## Context
El calendario se mantiene en JSON pero el equipo necesita Excel actualizado con formato original. Approach hibrido: script independiente (sin tokens) + LangChain tool opcional (para filtros inteligentes).

## Archivos a crear/modificar

### 1. `src/tools/calendar_exporter.py` (NUEVO, ~120 lineas)

**Funcion principal `export_calendar(year, filter_status=None)` — NO consume tokens:**
- Copia el Excel original como template (preserva merged cells, estilos, anchos)
- Carga `calendario-{year}.json`
- Mapea cada evento JSON -> fila Excel
- Resuelve nombres: partner_id -> proveedores, contacto_ids -> contactos
- Color de fila por estado: confirmado=verde, pendiente=amarillo, cancelado=rojo
- Guarda como `kalendbot-data/NV_{year}_Jaarkalender_UPDATED.xlsx`
- Retorna path del archivo generado

**LangChain tool wrapper (consume tokens solo si se usa via chat):**
- StructuredTool que llama a `export_calendar()`
- Permite filtros: ano, status, contacto

**CLI entry point `if __name__ == "__main__"`:**
- `python -m src.tools.calendar_exporter` -> exporta directo

**Mapping columnas (A-T):**
| Col | Header | JSON field |
|-----|--------|------------|
| A | Estado | estado (NUEVO — no estaba en original) |
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

### 2. `src/gateways/telegram_bot.py` — comando `/exportar`
- Agregar handler para comando `/exportar`
- Ejecuta `export_calendar()` directo (sin LLM)
- Envia el archivo XLSX como documento por Telegram
- Sin costo de tokens

### 3. `src/tools/__init__.py`
- Agregar `calendar_exporter_tool` a `WRITE_TOOLS` y `ALL_TOOLS`

### 4. `src/agent.py` — system prompt
- Agregar CalendarExporter a herramientas disponibles

## Modos de uso
| Modo | Consume tokens | Como |
|------|---------------|------|
| Comando `/exportar` en Telegram | NO | Handler directo |
| CLI `python -m src.tools.calendar_exporter` | NO | Script directo |
| "exporta solo los pendientes de mayo" via chat | SI | LangChain tool con filtros |

## Verificacion
1. `python -m src.tools.calendar_exporter` -> genera XLSX
2. `/exportar` en Telegram -> recibe archivo
3. "exporta el calendario" via chat -> usa LangChain tool
4. Abrir XLSX y comparar con original
