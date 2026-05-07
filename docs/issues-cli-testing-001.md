# Issues Report: CLI Testing Session #001

**Fecha:** 2026-03-20
**Tester:** Kmilo Aparicio
**Escenario:** CLI → contacto "hanna van rijsse" → pregunta "cuantos eventos tiene Koen"
**Resultado:** 2 errores, 5 issues identificados

---

## Errores Observados

### Error 1: Contacto no identificado
```
Contacto no identificado para teléfono: simulated-hanna van rijsse
```

### Error 2: Recursion limit
```
Error procesando mensaje de unknown-jsse: Recursion limit of 25 reached without hitting a stop condition.
```

---

## Issues Identificados

### ISSUE-01: CLI phone simulation rota
- **Severidad:** Alta (bloqueante para testing)
- **Archivo:** `src/cli.py:37`
- **Síntoma:** `Contacto no identificado para teléfono: simulated-hanna van rijsse`
- **Causa raíz:** CLI construye `phone = f"simulated-{contact_id}"` pero `_identify_contact_by_phone()` busca números reales en los JSON de contactos. El string "simulated-hanna van rijsse" nunca matchea con "+528120264857".
- **Impacto:** Todo contacto simulado en CLI es tratado como desconocido.
- **Fix:** Pasar contact_id directo al agente con parámetro opcional en `handle_message()`.

### ISSUE-02: Recursion limit por tool call loop
- **Severidad:** Alta (bloqueante para funcionalidad)
- **Archivo:** `src/agent.py:110`
- **Síntoma:** `Recursion limit of 25 reached without hitting a stop condition`
- **Causa raíz:** El LLM necesita llamar `CalendarManager` con `{"action": "list_by_contact", "contact_id": "koen-houwen"}` pero las tools usan `Tool` (string input). El modelo envía strings planos que no parsean correctamente → error → reintento → loop infinito.
- **Impacto:** Cualquier consulta que requiera tools con múltiples parámetros falla.
- **Fix:** Migrar tools a `StructuredTool` con parámetros Pydantic tipados para que OpenAI function calling llene cada campo correctamente.

### ISSUE-03: Memoria asignada a contacto incorrecto
- **Severidad:** Alta (corrupción de datos)
- **Archivo:** `src/cli.py:37` + `src/agent.py:104`
- **Síntoma:** Memoria se guarda bajo `unknown-jsse` en vez de `hanna-van-rijsse`
- **Causa raíz:** Como el teléfono simulado no matchea, el agente crea `contact_id = f"unknown-{phone[-4:]}"`. Los últimos 4 chars de "simulated-hanna van rijsse" son "jsse".
- **Impacto:**
  - La memoria de conversación se pierde entre sesiones
  - El agente no sabe quién es el contacto (pierde contexto de tono, rol)
  - Contactos con mismos últimos 4 chars compartirían memoria
- **Fix:** Mismo que ISSUE-01 — pasar contact_id directo.

### ISSUE-04: Tools con input multi-parámetro son frágiles
- **Severidad:** Alta (causa raíz del ISSUE-02)
- **Archivos:** `src/tools/calendar_manager.py`, `src/tools/date_locker.py`, `src/tools/flyer_manager.py`
- **Síntoma:** Tools devuelven error cuando el LLM envía input no-JSON
- **Causa raíz:** Estas tools usan `Tool` (single string input) y esperan JSON con múltiples campos. El LLM envía:
  - String plano: `"list_by_contact koen-houwen"` → se parsea como `{"action": "list_by_contact koen-houwen"}` → no matchea
  - JSON parcial o mal formado
  - Solo el action sin parámetros requeridos
- **Patrón:** Cualquier tool que necesite >1 parámetro es vulnerable a este problema con `Tool`.
- **Fix:** Migrar a `StructuredTool` con `args_schema` Pydantic. OpenAI function calling genera parámetros separados automáticamente.

### ISSUE-05: RulesEngine recursión interna
- **Severidad:** Media (no bloqueante, pero ineficiente)
- **Archivo:** `src/tools/rules_engine.py:113-118`
- **Síntoma:** Respuesta excesivamente larga cuando se consulta "all"
- **Causa raíz:** El caso `query == "all"` llama `rules_engine(sub_query)` recursivamente. Aunque es recursión Python (no LangGraph), genera output largo que consume tokens.
- **Fix:** Extraer sub-queries a funciones helper y llamarlas directamente.

---

## Lecciones Aprendidas

1. **Tool design para LLMs:** `Tool` (string input) es frágil para acciones con múltiples parámetros. Usar `StructuredTool` con Pydantic schemas desde el inicio.
2. **CLI testing necesita bypass de phone lookup:** En modo testing, el contact_id debe inyectarse directamente, no depender de phone matching.
3. **Recursion limit sin logging es opaco:** El loop de tool calls no loggea qué tool se llama ni qué error recibe. Agregar logging de tool calls ayudaría al debugging.
4. **Los últimos N chars de un string no son un ID único:** Usar `phone[-4:]` como fallback puede causar colisiones.

---

## Relación entre Issues

```
ISSUE-01 (phone simulation) ──┐
                               ├──► ISSUE-03 (memoria incorrecta)
ISSUE-04 (tools frágiles) ────┤
                               └──► ISSUE-02 (recursion loop)

ISSUE-05 (recursión RulesEngine) ──► independiente
```
