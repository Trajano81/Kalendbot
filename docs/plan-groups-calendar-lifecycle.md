# Feature Plan: Groups + Calendar Lifecycle

## Summary

Add support for **groups** that own **multiple calendars** with defined time spans,
and a **guided replication flow** to create new calendars from existing ones.

---

## Phase 1: Data Migration (Foundation)

### 1.1 Rename `instancias_2026` -> `instancias`

**Why**: The year-specific key doesn't scale. All code references need to become generic.

**Files to update (code)**:
- `src/tools/calendar_manager.py` (6 occurrences, lines 132, 300, 328, 366, 414, 632)
- `src/tools/calendar_exporter.py` (2 occurrences, line 368, 370)

**Data files to update**:
- `kalendbot-data/calendario-2026.json` (2 occurrences: pub-quiz, vrijmibo)
- `tests/fixtures/calendario-2026.json`

**Migration**: Simple find-replace. Write a one-time script or do it manually.

### 1.2 Add span metadata to calendar root

Current:
```json
{
  "ano": 2026,
  "version": "1.0",
  ...
}
```

New:
```json
{
  "id": "nv-mexico-2026",
  "group_id": "nv-mexico",
  "span": {
    "type": "year",
    "year": 2026,
    "start": "2026-01-01",
    "end": "2026-12-31"
  },
  "ano": 2026,
  "version": "1.0",
  ...
}
```

- `start`/`end` are always present regardless of `type` (computed from year if type=year)
- Keeps backward compat: `ano` stays

### 1.3 Move calendar file to new directory structure

```
kalendbot-data/
  calendars/
    nv-mexico-2026.json      (moved from calendario-2026.json)
  groups/
    nv-mexico.json            (new)
  contactos/                  (unchanged)
  proveedores/                (unchanged)
  config/                     (unchanged)
```

### 1.4 Centralize calendar loading

Create `src/services/calendar_loader.py`:

```python
def resolve_calendar(group_id: str, slug: str = None, date: str = None) -> str:
    """Returns the calendar file path based on slug (##2027) or date auto-detection."""
    ...

def load_calendar(calendar_id: str) -> dict:
    """Load a calendar by its ID."""
    ...

def save_calendar(data: dict, calendar_id: str):
    """Save a calendar by its ID."""
    ...

def get_active_calendar(group_id: str) -> dict:
    """Get the currently active calendar for a group."""
    ...
```

All 8 files that currently do `os.path.join(DATA_DIR, f"calendario-{year}.json")` will
call `load_calendar()` instead:
- `src/tools/calendar_manager.py`
- `src/tools/calendar_exporter.py`
- `src/tools/conflict_detector.py`
- `src/tools/date_locker.py`
- `src/tools/flyer_manager.py`
- `src/gateways/telegram_bot.py`
- `src/gateways/whatsapp_bot.py`
- `tests/conftest.py`

---

## Phase 2: Group Definition

### 2.1 Group JSON schema

File: `kalendbot-data/groups/nv-mexico.json`

```json
{
  "id": "nv-mexico",
  "nombre": "NV Mexico",
  "descripcion": "Asociacion Neerlandesa en Mexico",
  "channels": {
    "telegram_group_id": "-100xxx",
    "whatsapp_group_id": "xxx@g.us"
  },
  "calendars": [
    {
      "id": "nv-mexico-2026",
      "slug": "2026",
      "file": "nv-mexico-2026.json",
      "span": { "type": "year", "year": 2026 },
      "active": true
    }
  ],
  "contacto_ids": ["kmilo-aparicio", "hanna-van-rijsse"],
  "admin_ids": ["kmilo-aparicio"]
}
```

Contacts stay global (shared across groups), identified by telegram_id or phone.

### 2.2 Group Manager tool

New file: `src/tools/group_manager.py`

Actions:
- `list_groups` - list all groups
- `get_group` - get group details
- `list_calendars` - list calendars for a group
- `set_active_calendar` - activate a calendar by slug
- `get_active_calendar` - get current active calendar

---

## Phase 3: Calendar Selection (## Syntax)

### 3.1 Parsing `##` tokens

In the message preprocessing pipeline (agent.py), extract `##` tokens:

```
Input:  "/change #1 nombre actividad ##2027"
Parsed: calendar_override="2027", rest="/change #1 nombre actividad"

Input:  "/change #1 fecha 01/02/2027"
Parsed: auto_detect calendar with span containing 2027-02-01

Input:  "/change #1 nombre actividad"
Parsed: use active calendar (default)
```

Resolution priority:
1. Explicit `##slug` (highest)
2. Auto-detect from dates in the message
3. Active calendar for the group (fallback)

### 3.2 Slug resolution

| User types | Resolves to |
|---|---|
| `##2026` | Calendar with `span.year == 2026` or `slug == "2026"` |
| `##2027` | Calendar with `span.year == 2027` or `slug == "2027"` |
| `##summer_events` | Calendar with `slug == "summer_events"` |

### 3.3 Auto-detect by date

When user mentions a date (e.g., `01/02/2027`), check all calendars in the group:
- If exactly one calendar's span contains the date -> use it
- If multiple calendars match -> use the active one, add a note:
  "This date also falls in ##summer_events"
- If no calendar matches -> warn the user

---

## Phase 4: Replication Flow

### 4.1 New command: `/replicar`

Guided conversational flow (not a single-action tool):

```
Step 1: User triggers
  User: /replicar ##2026

Step 2: Bot presents options
  Bot: Replicar calendario "NV Mexico 2026" (ene 2026 - dic 2026)
       Nuevo periodo: ##2027 (ene 2027 - dic 2027)

       How do you want to create the new calendar?
       1. Auto-fill: copy events + recurring, dates adjusted to 2027, status "pendiente"
       2. Empty: just the structure, no events

Step 3: User chooses
  User: 1

Step 4: Bot creates and asks about activation
  Bot: Calendar ##2027 created with:
       - 2 recurring events (instances generated for 2027)
       - 29 unique events (dates shifted, status: pendiente)

       Do you want to activate it now?
       Yes - ##2027 becomes the active calendar
       No  - ##2026 stays active

Step 5: User decides
  User: yes

Step 6: Confirmation
  Bot: ##2027 is now the active calendar.
       ##2026 remains available (switch with /calendario ##2026).
```

### 4.2 Auto-fill logic (clone mode)

| Event type | What happens |
|---|---|
| Recurring (has `regla`) | Keep same rule, auto-generate `instancias` for new span |
| Fixed date (`fecha`) | Shift to same month/day in new year. Flag Feb 29 for review |
| Date range (`fecha_inicio`/`fecha_fin`) | Shift both by same offset |
| Approximate (`fecha_exacta: false`) | Shift year, keep `fecha_exacta: false` |
| Conditional (`condicional: true`) | Copy with shifted date, keep condition text |

**Fields reset on clone**:
| Field | Cloned value |
|---|---|
| `estado` | -> `pendiente` |
| `show_in_export` | -> `true` |
| `ultima_actualizacion` | -> cleared |
| `_undo_snapshot` | -> cleared |
| `fecha_original` | -> cleared |
| `nombre`, `hora`, `venue_*`, `precio` | -> copied as-is |
| `contacto_ids`, `partner_id` | -> copied as-is |
| `flyer_*`, `tier_promocion` | -> copied as-is |
| `texto_social` | -> copied (user can edit later) |

**Recurring instance generation**:
Rules like "1e donderdag vd mnd" (first Thursday of the month) should be computed
for the new year. Implementation approach:
- Parse the Dutch rule patterns already used in the data
- Generate dates for each month in the target span
- Store in `instancias` array with `estado: "pendiente"`
- If a rule can't be parsed, copy the raw rule and leave `instancias` empty with a
  warning to the user

### 4.3 Overwrite protection

If the target calendar already exists:
```
Bot: Calendar ##2027 already exists with 15 events.
     What do you want to do?
     1. Overwrite - replace ##2027 completely
     2. Cancel
```

No merge option. Overwrite or cancel only.

### 4.4 Non-year replication (named calendars)

```
User: /replicar ##summer_events
Bot:  Replicar "Eventos de Verano" (jun 2026 - ago 2026)
      Target period?
      Example: jun 2027 - ago 2027, or specific dates (YYYY-MM-DD)

User: jun 2027 - ago 2027
Bot:  (continues same flow: auto-fill/empty -> activate?)
```

---

## Phase 5: New Commands

### 5.1 Calendar management commands

| Command | Description |
|---|---|
| `/calendarios` | List all calendars for the current group |
| `/calendario ##slug` | Switch active calendar |
| `/calendario info` | Show active calendar details + span |
| `/replicar ##slug` | Start replication flow |

### 5.2 Inline ## usage in existing commands

All existing commands that target events support `##`:
```
/change #1 nombre "Fiesta" ##2027     -> edit event #1 in 2027 calendar
/ocultar #5 ##2027                    -> hide event #5 in 2027 calendar
/mostrar #5 ##2027                    -> show event #5 in 2027 calendar
```

Without `##`, uses the active calendar. With a date in the future year,
auto-detects.

---

## Implementation Order

1. **Phase 1.1-1.2**: Rename `instancias_2026` -> `instancias`, add span metadata
   (small, safe, backward-compatible with `ano` field kept)

2. **Phase 1.3-1.4**: Move files to `calendars/` dir, centralize loader
   (all tools updated to use new loader)

3. **Phase 2**: Group definition + GroupManager tool
   (new files, no breaking changes)

4. **Phase 3**: ## parsing + calendar resolution
   (agent.py preprocessing update)

5. **Phase 4**: /replicar command with guided flow
   (new tool + conversation state)

6. **Phase 5**: Wire up new commands to Telegram/WhatsApp bots

Each phase is independently deployable. Phase 1 is the critical foundation.

---

## Open Items

- [ ] Dutch rule parser for recurring instance generation (Phase 4.2)
      Current rules: "1e donderdag vd mnd", "Laatste vrijdag vd mnd"
      Need: a function that takes a rule + year -> list of dates
- [ ] Decide if groups are auto-created for existing setup or manually created
- [ ] Test strategy: unit tests for calendar_loader, replication logic,
      ## parsing; integration tests for the full flow
