# Issues Report: CLI Testing Session #002

**Fecha:** 2026-03-20
**Tester:** Kmilo Aparicio
**Escenario:** CLI → contacto "hanna-van-rijsse" → múltiples queries
**Resultado:** 5 observaciones, 4 mejoras requeridas

---

## Observaciones

### OBS-01: Agente no encuentra "Koen" por nombre parcial
- **Severidad:** Alta (funcionalidad core)
- **Síntoma:** Al preguntar "cuantos eventos tiene Koen", el agente buscó en ProviderManager en vez de ContactManager, y no encontró match parcial.
- **Causa raíz:** ContactManager no tiene búsqueda por nombre parcial (fuzzy matching). El agente no sabe que debe buscar en contactos primero.
- **Fix propuesto:** Agregar acción `search_by_name` en ContactManager que haga match parcial (case-insensitive, substring). Ajustar system prompt para priorizar ContactManager sobre ProviderManager para búsquedas de personas.

### OBS-02: Discrepancia en conteo de eventos de Koen (10 vs 9)
- **Severidad:** Media (posible error en datos)
- **Síntoma:** El agente reporta 10 eventos para koen-houwen, pero el usuario cuenta 9 en el Excel.
- **Causa raíz:** Nations League (`nations-league-2026`) puede estar incorrectamente asignado a koen-houwen en el JSON. Requiere verificación contra el Excel fuente.
- **Fix propuesto:** Verificar asignación de Nations League en Excel. Si no es de Koen, corregir `contacto_ids` en calendario-2026.json.

### OBS-03: Verificación de conflictos funciona correctamente
- **Severidad:** N/A (positivo)
- **Síntoma:** Al preguntar "hay conflictos el 5 de mayo?", el agente respondió correctamente que no hay conflictos y que el 5 de mayo no es feriado oficial.
- **Nota:** El 5 de mayo no es feriado oficial en México (correcto). Considerar agregarlo como "fecha notable cultural" si el usuario lo requiere.

### OBS-04: list_pending muestra fechas pasadas sin distinción de estado
- **Severidad:** Alta (UX y lógica de negocio)
- **Síntoma:** `list_pending` muestra todos los 31 eventos como "pendientes", incluyendo eventos con fechas ya pasadas. No distingue entre "pendiente de confirmar" y "confirmado por ocurrir".
- **Causa raíz:** Todos los eventos tienen `estado: "pendiente"` sin distinción. No hay lógica para filtrar por fecha actual ni para separar estados de confirmación.
- **Fix propuesto:**
  1. Definir estados: `pendiente` (fecha no confirmada), `confirmado` (fecha bloqueada), `cancelado`
  2. En `list_pending`, filtrar solo eventos futuros O separar en secciones
  3. Agregar campo `fecha_confirmada` vs `fecha` (propuesta vs confirmada)

### OBS-05: Consumo excesivo de tokens en preguntas frecuentes
- **Severidad:** Media (costo operativo)
- **Síntoma:** Preguntas comunes como "cuántos eventos hay" o "quién es el content manager" generan llamadas al LLM que podrían responderse localmente.
- **Fix propuesto:** Crear `kalendbot-data/config/faq.json` con respuestas predefinidas para preguntas frecuentes. Implementar FAQ lookup antes de invocar al agente.

---

## Relación entre Observaciones

```
OBS-01 (fuzzy matching) ──► mejora ContactManager
OBS-02 (conteo Koen)    ──► verificación datos
OBS-04 (estados evento) ──► mejora CalendarManager + datos
OBS-05 (FAQ tokens)     ──► nueva funcionalidad
OBS-03 (conflictos OK)  ──► sin acción
```

---

## Prioridad de Implementación

1. **OBS-01** — Fuzzy matching en ContactManager (desbloquea búsquedas por nombre)
2. **OBS-04** — Sistema de estados de eventos (mejora UX y lógica)
3. **OBS-05** — FAQ document (ahorro de tokens)
4. **OBS-02** — Verificar Nations League (requiere Excel del usuario)

---

## Entidad: Contactos vs Proveedores

Clarificación del usuario sobre la estructura de datos:

- **Proveedores** (`proveedores/`): Organizaciones/empresas (columna "Mapa de partners" del Excel)
- **Contactos** (`contactos/`): Personas físicas (columna L = nombre, columna M = teléfono)
- **Responsable de flyer** (columna N): Si aparece un nombre → esa persona. Si no → Hanna van Rijsse (Content Manager de NV)
- Un proveedor puede tener múltiples contactos; un contacto pertenece a un proveedor
