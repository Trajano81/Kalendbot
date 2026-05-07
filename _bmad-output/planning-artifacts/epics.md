---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '.claude/plans/mossy-meandering-micali.md'
  - 'src/tools/calendar_exporter.py'
  - 'kalendbot-data/calendario-2026.json'
---

# Kalendbot - Epic Breakdown: QA CalendarExporter V3

## Overview

This document provides the complete epic and story breakdown for QA testing of the CalendarExporter V3 changes, decomposing the implementation plan into testable stories with acceptance criteria following QA best practices.

## Requirements Inventory

### Functional Requirements

FR1: El exporter debe resolver venue_id a nombres legibles desde proveedores JSON (ej: "holland-wafels" → "Holland Wafels", "embajada-nl" → "Residentie Ambassade")
FR2: El exporter debe resolver venue_nombre del proveedor cuando el evento tiene venue_id pero no venue_nombre propio
FR3: Todo contenido exportado en modo Dutch (default) debe estar en holandés — sin texto en español
FR4: Las reglas de eventos recurrentes deben mostrarse en holandés (ej: "1e donderdag vd mnd")
FR5: Los eventos recurrentes con instancias_2026 deben expandirse en filas individuales cronológicamente entre los demás eventos
FR6: Las instancias expandidas heredan todos los datos del evento padre (partner, venue, hora, canales, etc.)
FR7: Rows 4-5 siguen mostrando la definición base de eventos recurrentes (regla, datos generales)
FR8: El export debe soportar 4 idiomas: dut (default), eng, spa, por
FR9: El export Dutch debe ser instantáneo (sin llamadas LLM)
FR10: Los exports no-Dutch traducen headers, meses y valores estáticos mediante diccionario
FR11: Los exports no-Dutch traducen contenido de eventos (nombre, descripcion, detalle, texto_social) mediante LLM
FR12: El archivo de salida incluye sufijo de idioma: NV_{year}_Jaarkalender_UPDATED_{lang}.xlsx
FR13: El template base es V3.0 con columna "Flyer resp." añadida (21 cols B-U)
FR14: La columna N muestra "Flyer oleadas" y columna O muestra "Flyer resp." como columnas separadas
FR15: El parámetro lang es aceptado tanto por el CLI como por el LangChain tool

### NonFunctional Requirements

NFR1: El export Dutch debe completarse en menos de 5 segundos (sin LLM)
NFR2: El export con LLM translation no debe tardar más de 30 segundos
NFR3: Si el LLM falla, el export debe completar con texto original (fallback graceful)
NFR4: El formato Excel preserva estilos, merged cells y formulas del template V3.0
NFR5: Los teléfonos deben mostrarse como números con código de país (ej: 525554317397)
NFR6: Las fechas deben formatearse en el idioma correspondiente (ej: "22 Januari" para dut, "22 January" para eng)
NFR7: El exporter no debe crashear con datos faltantes (venue_id null, precio null, contacto vacío)

### Additional Requirements

- Template V3.0 debe tener merged cells correctos: R1:T1 para "Waar posten", N1/O1 separados
- Row 2 formulas deben referenciar las columnas correctas tras el shift (N2, P2-S2)
- El campo instancias_2026 del JSON debe contener fechas válidas ISO 8601
- Los proveedores JSON deben tener campo venue_nombre cuando el nombre del venue difiere del nombre de la organización

### UX Design Requirements

N/A — Sistema conversacional sin interfaz visual. El output es un archivo Excel.

### FR Coverage Map

| FR | Epic | Description |
|---|---|---|
| FR1 | Epic 1 | Venue ID → readable name resolution |
| FR2 | Epic 1 | Venue name fallback from provider |
| FR3 | Epic 2 | Dutch export = Dutch content only |
| FR4 | Epic 2 | Recurring rules in Dutch |
| FR5 | Epic 3 | Expand recurring instances chronologically |
| FR6 | Epic 3 | Instances inherit parent data |
| FR7 | Epic 3 | Rows 4-5 show base definition |
| FR8 | Epic 4 | 4 language support |
| FR9 | Epic 4 | Dutch export instant (no LLM) |
| FR10 | Epic 4 | Non-Dutch static translation via dict |
| FR11 | Epic 4 | Non-Dutch content translation via LLM |
| FR12 | Epic 4 | Output file lang suffix |
| FR13 | Epic 5 | Template V3.0 with Flyer resp. column |
| FR14 | Epic 5 | Flyer oleadas (N) / Flyer resp. (O) separate |
| FR15 | Epic 4 | Lang param in CLI and LangChain tool |
| NFR1 | Epic 4 | Dutch export < 5 seconds |
| NFR2 | Epic 4 | LLM export < 30 seconds |
| NFR3 | Epic 4 | LLM failure graceful fallback |
| NFR4 | Epic 5 | Preserve styles, merged cells, formulas |
| NFR5 | Epic 1 | Phone numbers with country code |
| NFR6 | Epic 2 | Dates in correct language |
| NFR7 | Epic 1 | No crash on missing data |

## Epic List

### Epic 1: Data Quality & Venue Resolution
QA testers can verify that all venue IDs resolve to human-readable names and that event data (contacts, addresses, prices) renders correctly in the export.
**FRs covered:** FR1, FR2, NFR5, NFR7

### Epic 2: Dutch Content & Localization Correctness
QA testers can verify that the default Dutch export contains zero Spanish text — all recurring rules, descriptions, details, and social text are in Dutch, with dates formatted in Dutch.
**FRs covered:** FR3, FR4, NFR6, NFR9

### Epic 3: Recurring Event Expansion
QA testers can verify that recurring events with instancias_2026 expand into individual chronological rows (Pub Quiz) while events with expandir_en_export: false (Vrijmibo) are excluded, and rows 4-5 retain the base definition.
**FRs covered:** FR5, FR6, FR7

### Epic 4: Multi-Language Export
QA testers can verify that exports in eng/spa/por correctly translate headers, months, static values via dictionary, and event content via LLM, with proper file naming and graceful fallback.
**FRs covered:** FR8, FR9, FR10, FR11, FR12, FR15, NFR1, NFR2, NFR3

### Epic 5: Template V3.0 & Format Integrity
QA testers can verify that the V3.0 template structure is preserved — 21 columns (B-U), merged cells, formulas, image positioning, cell styles — and the 2-column flyer layout (N=oleadas, O=resp.) is correct.
**FRs covered:** FR13, FR14, NFR4, Additional Requirements (merged cells, formulas, template structure)

## Epic 1: Data Quality & Venue Resolution

QA testers can verify that all venue IDs resolve to human-readable names and that event data (contacts, addresses, prices) renders correctly in the export.

### Story 1.1: Venue ID Resolution to Readable Names

As a QA tester,
I want to verify that venue IDs in the export resolve to human-readable names,
So that the Excel shows "Holland Wafels" instead of "holland-wafels".

**Acceptance Criteria:**

**Given** an event with `venue_id: "holland-wafels"` and no `venue_nombre`
**When** the calendar is exported to Excel
**Then** column D (Locatie) shows "Holland Wafels" (from proveedores JSON `nombre`)

**Given** an event with `venue_id: "embajada-nl"` and no `venue_nombre`
**When** the calendar is exported to Excel
**Then** column D shows "Residentie Ambassade" (from proveedores JSON `venue_nombre`)

**Given** an event with both `venue_nombre: "Lucerna 42, Juárez, CDMX"` and no `venue_id`
**When** the calendar is exported to Excel
**Then** column D shows the event's own `venue_nombre` directly

### Story 1.2: Contact & Phone Number Resolution

As a QA tester,
I want to verify that contact names and phone numbers render correctly,
So that the contact column shows names and phones with country codes.

**Acceptance Criteria:**

**Given** an event with `contacto_ids: ["rocco-van-velzen"]`
**When** the calendar is exported
**Then** column K shows the contact's `nombre` from contactos JSON
**And** column L shows the phone number as a number with country code (e.g., 525554317397)

**Given** an event with multiple `contacto_ids`
**When** the calendar is exported
**Then** column K shows comma-separated names

### Story 1.3: Graceful Handling of Missing Data

As a QA tester,
I want to verify the exporter doesn't crash with null/missing fields,
So that exports always complete even with incomplete event data.

**Acceptance Criteria:**

**Given** an event with `venue_id: null` and no `venue_nombre`
**When** the calendar is exported
**Then** column D shows "nvt" and the export completes

**Given** an event with `precio: null`
**When** the calendar is exported
**Then** column G shows 0 and the export completes

**Given** an event with empty `contacto_ids: []`
**When** the calendar is exported
**Then** columns K-L are empty and the export completes without error

## Epic 2: Dutch Content & Localization Correctness

QA testers can verify that the default Dutch export contains zero Spanish text — all recurring rules, descriptions, details, and social text are in Dutch, with dates formatted in Dutch.

### Story 2.1: Zero Spanish Content in Dutch Export

As a QA tester,
I want to scan the entire Dutch export for Spanish text,
So that I can confirm all user-facing content is in Dutch.

**Acceptance Criteria:**

**Given** the calendar is exported with `lang="dut"` (default)
**When** I inspect all cells in columns B-U across all data rows
**Then** no cell contains Spanish text (no "jueves", "viernes", "voluntarios", "convocatoria", "exposición", "edición")
**And** recurring rules show Dutch text: "1e donderdag vd mnd", "Laatste vrijdag vd mnd"

**Given** event descriptions and details in the JSON are in Dutch
**When** the calendar is exported
**Then** descriptions like "Borrel voor vrijwilligers", "Alleen kennisgeving, geen fysiek evenement" appear verbatim

### Story 2.2: Dutch Date Formatting

As a QA tester,
I want to verify all dates use Dutch month names,
So that the export is linguistically consistent.

**Acceptance Criteria:**

**Given** an event with `fecha: "2026-01-22"`
**When** exported with `lang="dut"`
**Then** column B shows "22 Januari"

**Given** an event with `fecha: "2026-06-04"`
**When** exported with `lang="dut"`
**Then** column B shows "4 Juni"

**Given** all 29 events in the export
**When** I check column B
**Then** every date uses Dutch month names from the TRANSLATIONS dict (Januari, Februari, Maart, etc.)

### Story 2.3: Dutch Export Without LLM Calls

As a QA tester,
I want to confirm the Dutch export path makes zero LLM API calls,
So that it executes instantly without external dependencies.

**Acceptance Criteria:**

**Given** `lang="dut"` (default)
**When** the export is executed
**Then** `_translate_content()` returns early without invoking ChatAnthropic
**And** the export completes in under 5 seconds (NFR1)

## Epic 3: Recurring Event Expansion

QA testers can verify that recurring events with instancias_2026 expand into individual chronological rows (Pub Quiz) while events with expandir_en_export: false (Vrijmibo) are excluded, and rows 4-5 retain the base definition.

### Story 3.1: Pub Quiz Instance Expansion

As a QA tester,
I want to verify Pub Quiz instances expand into individual rows sorted chronologically,
So that each monthly quiz appears in its correct calendar position.

**Acceptance Criteria:**

**Given** pub-quiz-recurrente has 5 entries in `instancias_2026` (Feb-Jun 2026)
**When** the calendar is exported
**Then** 5 individual "Maandelijkse Pub Quiz" rows appear in rows 6+
**And** they are interleaved chronologically with regular events (e.g., Feb quiz between Jan and Mar events)

**Given** an expanded Pub Quiz instance with `fecha: "2026-02-05"`
**When** it appears in the export
**Then** column B shows "5 Februari"

### Story 3.2: Expanded Instances Inherit Parent Data

As a QA tester,
I want to verify each expanded instance inherits all parent event data,
So that partner, venue, time, channels, and contact info are complete.

**Acceptance Criteria:**

**Given** an expanded Pub Quiz instance
**When** I check its row in the export
**Then** column C (Partner) shows "Holland Wafels"
**And** column D (Locatie) shows "Holland Wafels" (resolved from venue_id)
**And** column F (Tijdstip) shows "19:00"
**And** column G (Entree) shows 75
**And** column K (Contact) shows "Christian Kemper"

### Story 3.3: Vrijmibo Excluded from Expansion

As a QA tester,
I want to verify Vrijmibo instances are NOT expanded into rows,
So that the export matches the V3 reference with exactly 29 events.

**Acceptance Criteria:**

**Given** vrijmibo-recurrente has `expandir_en_export: false` and 6 entries in `instancias_2026`
**When** the calendar is exported
**Then** zero Vrijmibo instance rows appear in rows 6+
**And** the total event count in rows 6+ is exactly 29

**Given** vrijmibo-recurrente still appears in `eventos_recurrentes`
**When** rows 4-5 are checked
**Then** row 5 shows the Vrijmibo base definition (regla, venue, etc.)

### Story 3.4: Rows 4-5 Base Definitions

As a QA tester,
I want to verify rows 4-5 show the base recurring event definitions,
So that the summary section is preserved above the chronological data.

**Acceptance Criteria:**

**Given** two recurring events (Pub Quiz and Vrijmibo)
**When** the calendar is exported
**Then** row 4 column B shows "1e donderdag vd mnd" (Pub Quiz regla)
**And** row 5 column B shows "Laatste vrijdag vd mnd" (Vrijmibo regla)
**And** both rows show their respective partner, venue, and contact data

## Epic 4: Multi-Language Export

QA testers can verify that exports in eng/spa/por correctly translate headers, months, static values via dictionary, and event content via LLM, with proper file naming and graceful fallback.

### Story 4.1: Language Parameter Acceptance

As a QA tester,
I want to verify the lang parameter works via both CLI and LangChain tool,
So that users can request exports in any supported language.

**Acceptance Criteria:**

**Given** `python -m src.tools.calendar_exporter 2026 eng`
**When** the CLI is executed
**Then** the export completes and outputs a file path ending in `_eng.xlsx`

**Given** the LangChain tool is called with `lang="spa"`
**When** the tool executes
**Then** the export completes with suffix `_spa.xlsx`

**Given** `lang="xyz"` (invalid)
**When** the export is attempted
**Then** an error message is returned listing valid languages: dut, eng, spa, por

### Story 4.2: Static Translation via Dictionary

As a QA tester,
I want to verify headers, months, and static values translate correctly per language,
So that structural content doesn't depend on LLM.

**Acceptance Criteria:**

**Given** `lang="eng"`
**When** the export is generated
**Then** row 3 headers show: "Date", "Activity", "Partner", "Location", etc.
**And** dates use English months: "22 January", "4 June"
**And** missing values show "TBD" instead of "ntbp"

**Given** `lang="spa"`
**When** the export is generated
**Then** row 3 headers show: "Fecha", "Actividad", "Socio", "Ubicación", etc.
**And** dates use Spanish months: "22 Enero", "4 Junio"

**Given** `lang="por"`
**When** the export is generated
**Then** row 3 headers show: "Data", "Atividade", "Parceiro", "Local", etc.

### Story 4.3: LLM Content Translation

As a QA tester,
I want to verify event content (nombre, descripcion, detalle, texto_social) is translated via LLM for non-Dutch exports,
So that the full export reads naturally in the target language.

**Acceptance Criteria:**

**Given** `lang="eng"` and an event with `descripcion: "Social / Pub Quiz"`
**When** the export is generated
**Then** column E shows the LLM-translated English version of the description

**Given** `lang="spa"` and an event with `detalle: "Incl: borrel hap/drankjes. Eventbrite link toevoegen"`
**When** the export is generated
**Then** column I shows the Spanish translation

**Given** proper nouns and emojis in texto_social
**When** translated
**Then** proper nouns (e.g., "Holland Wafels", "Koningsdag") and emojis remain unchanged

### Story 4.4: LLM Failure Graceful Fallback

As a QA tester,
I want to verify that if the LLM translation fails, the export completes with original Dutch text,
So that the system never blocks on translation errors.

**Acceptance Criteria:**

**Given** `lang="eng"` and the LLM API is unreachable or returns an error
**When** the export is generated
**Then** the export completes successfully
**And** event content fields retain their original Dutch text
**And** headers and months are still translated via static dictionary (no LLM needed)

### Story 4.5: Output File Naming Convention

As a QA tester,
I want to verify each language export produces a correctly named file,
So that files are distinguishable by language suffix.

**Acceptance Criteria:**

**Given** `lang="dut"`
**When** exported
**Then** file is named `NV_2026_Jaarkalender_UPDATED_dut.xlsx`

**Given** `lang="eng"`
**When** exported
**Then** file is named `NV_2026_Jaarkalender_UPDATED_eng.xlsx`

**Given** `lang="spa"` and `lang="por"`
**When** exported
**Then** files are named with `_spa.xlsx` and `_por.xlsx` respectively

### Story 4.6: Performance — Dutch vs LLM Exports

As a QA tester,
I want to measure export times to verify performance requirements,
So that Dutch exports are instant and LLM exports stay within bounds.

**Acceptance Criteria:**

**Given** `lang="dut"`
**When** the export is timed
**Then** it completes in under 5 seconds (NFR1)

**Given** `lang="eng"` (requires LLM)
**When** the export is timed
**Then** it completes in under 30 seconds (NFR2)

## Epic 5: Template V3.0 & Format Integrity

QA testers can verify that the V3.0 template structure is preserved — 21 columns (B-U), merged cells, formulas, image positioning, cell styles — and the 2-column flyer layout (N=oleadas, O=resp.) is correct.

### Story 5.1: Column Layout & Flyer Split

As a QA tester,
I want to verify the export has 21 columns (B-U) with Flyer oleadas and Flyer resp. as separate columns,
So that the V3.0 structure matches the reference spreadsheet.

**Acceptance Criteria:**

**Given** the exported Excel file
**When** I check row 3 (headers)
**Then** column N shows "Flyer oleadas"
**And** column O shows "Flyer resp."
**And** columns B through U total 20 header cells (21 columns including row labels)

**Given** an event with `flyer_oleadas: 3` and `flyer_responsable: "nv"`
**When** exported
**Then** column N shows 3
**And** column O shows the content manager's name (resolved from CONTENT_MANAGER)

### Story 5.2: Merged Cells & Row 1-2 Structure

As a QA tester,
I want to verify merged cells and formulas in rows 1-2 are preserved,
So that the template header structure matches V3.0.

**Acceptance Criteria:**

**Given** the exported Excel
**When** I check row 1
**Then** R1:T1 is merged with text "Waar posten"
**And** N1 and O1 are separate (not merged)

**Given** row 2
**When** I check formulas
**Then** N2 contains a SUMIF formula referencing column N
**And** P2-S2 contain COUNTIF formulas referencing their respective columns

### Story 5.3: Image Positioning Below Data

As a QA tester,
I want to verify footer logos appear below the last data row,
So that images don't overlap with event data.

**Acceptance Criteria:**

**Given** 29 events in the export (rows 6-34)
**When** I check the footer images
**Then** all images are positioned at row 36 or later (last_data_row + 2)
**And** no image overlaps with any data row

**Given** a different event count (e.g., filtered export with fewer events)
**When** exported
**Then** images dynamically reposition below the last data row

### Story 5.4: Cell Styles for Extended Rows

As a QA tester,
I want to verify that rows beyond the template's original extent have proper formatting,
So that all data rows look consistent regardless of count.

**Acceptance Criteria:**

**Given** the template originally has formatting up to row 38
**When** data extends to rows 39+
**Then** those rows have the same font, fill, border, alignment, and number format as row 6
**And** there are no unformatted rows in the data range
