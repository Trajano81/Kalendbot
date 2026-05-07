---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: ['NV_Mexico_2026_Analisis_Calendario.md', 'langchain_course_v1/app_conversacional.py']
session_topic: 'KalendBot - Bot inteligente para gestión de calendario de eventos de la Cámara de Comercio Holandesa en México'
session_goals: 'Bot de comunicación con proveedores, gestión inteligente de fechas sin conflictos, awareness de festividades, configurabilidad de restricciones, datos estructurados, integración con Eventbrite'
selected_approach: 'hybrid: ai-recommended + random + progressive'
techniques_used: ['What If Scenarios', 'Alien Anthropologist', 'Morphological Analysis', 'SCAMPER', 'Chaos Engineering', 'Decision Tree Mapping']
ideas_generated: 58
session_active: false
workflow_completed: true
---

# KalendBot — Brainstorming Session Results

**Facilitador:** Kmiloaparicio
**Fecha:** 2026-03-16 al 2026-03-18
**Duración:** 3 días de sesión iterativa

---

## Session Overview

**Tema:** KalendBot — Bot inteligente para gestión de calendario de eventos de la Cámara de Comercio Holandesa en México (NV Mexico). Planificación del calendario 2027 basado en el calendario 2026.

**Contexto del negocio:**
- 31 eventos anuales distribuidos a lo largo del año
- 9 contactos/proveedores gestionan todos los eventos
- 5 venues principales (Holland Wafels alberga el 45% de la actividad)
- 4 tiers de promoción (Grande/Mediano/Regular/Delegado)
- 5 eventos con Eventbrite (pagados), 26 gratuitos
- WhatsApp y RRSS como canales universales de difusión

**Objetivos de la sesión:**
1. Bot que se comunique con proveedores (WhatsApp, Telegram)
2. Ratificación de fechas/horarios/flyers/precios sin conflictos, con alertas de feriados
3. Awareness de festividades y eventos especiales por año
4. Configurabilidad de restricciones (horarios, días, proveedores)
5. Datos estructurados/serializados para consulta del agente
6. API de integración con Eventbrite y otras plataformas

**Enfoque:** Híbrido (IA-recomendado + selección aleatoria + flujo progresivo)

---

## Technique Selection

**Técnicas utilizadas (6):**

| Fase | Técnica | Categoría | Propósito |
|------|---------|-----------|-----------|
| 1 | What If Scenarios | Creative (IA-recomendada) | Explorar posibilidades radicales sin restricciones |
| 1b | Alien Anthropologist | Theatrical (aleatoria) | Revelar supuestos ocultos con ojos ajenos |
| 2 | Morphological Analysis | Deep (IA-recomendada) | Mapear todas las variables y combinaciones posibles |
| 3a | SCAMPER Method | Structured (IA-recomendada) | Refinar ideas con 7 lentes sistemáticos |
| 3b | Chaos Engineering | Wild (aleatoria) | Stress-testear ideas contra escenarios de fallo |
| 4 | Decision Tree Mapping | Structured (IA-recomendada) | Mapear flujos de decisión completos del bot |

---

## Inventario Completo de Ideas

### Tema 1: Arquitectura y Datos

_Cómo se estructura el sistema y dónde vive la información_

**[Bot-Comms #9]: Calendario como "Contrato Vivo" (JSON/YAML)**
_Concepto:_ El calendario no es un Excel estático sino un JSON estructurado donde cada evento tiene: fecha, estado (tentativo/confirmado/bloqueado), proveedor, tier de promoción, restricciones, y un hash de última modificación. El agente consulta este "contrato vivo" para todas sus decisiones.
_Novedad:_ Fuente única de verdad que evoluciona con cada interacción del bot.

**[Morph #26]: Arquitectura "JSON-first, DB-ready"**
_Concepto:_ Empezar con JSON + Git como fuente de verdad, pero estructurar los datos como si fueran tablas relacionales. Si la escala lo requiere, migrar a PostgreSQL es un script de importación, no una reescritura.
_Novedad:_ Lo mejor de ambos mundos — simplicidad hoy, camino de crecimiento mañana.

**[Morph #21]: El MVP Pragmático**
_Concepto:_ WhatsApp + YAML/JSON como fuente de datos + fecha heredada de 2026 con ajuste automático por feriados + solo Eventbrite + LangChain como orquestador. Lo mínimo para funcionar con el menor esfuerzo de desarrollo.
_Novedad:_ Prioriza velocidad de implementación sobre sofisticación.

**[Morph #23]: El Híbrido Evolutivo**
_Concepto:_ Empezar con JSON + LangChain + WhatsApp (MVP), pero diseñar la estructura de datos para migrar a PostgreSQL + agente más sofisticado después. La arquitectura crece con la necesidad.
_Novedad:_ No es "MVP vs completo" — es un camino de evolución planificado desde el día 1.

**[SCAMPER #36]: Eliminar el Excel como fuente de verdad**
_Concepto:_ El Excel actual (NV_2026_Jaarkalender) tiene columnas crípticas (K, N, O), fórmulas ocultas y lógica no documentada. Al migrar a JSON estructurado, el Excel desaparece completamente. El bot ES la interfaz del calendario.
_Novedad:_ No "automatizar el Excel" — reemplazarlo.

**[SCAMPER #30b]: Motor de Eventos Externos Parametrizable**
_Concepto:_ Archivo de configuración por año (`eventos-externos-2027.json`) con eventos relevantes (F1, Champions, etc.) y ciclos deportivos (Mundial cada 4 años, Copa América cada 4, etc.). Actualizable mid-year cuando surgen eventos emergentes.
_Novedad:_ El bot es auto-consciente del ciclo deportivo/cultural global y sabe que en 2027 NO hay Mundial.

**[SCAMPER #30c]: Fuente de eventos externos actualizable**
_Concepto:_ El coordinador puede agregar eventos emergentes mid-year. El archivo se actualiza y el bot recalcula conflictos automáticamente.
_Novedad:_ Eventos externos no son estáticos al inicio del año — evolucionan.

**[Arch #58]: Stack tecnológico final**
_Concepto:_ KalendBot = LangChain (agente REACT conversacional basado en app_conversacional.py) + 7 tools de calendario + FileChatMessageHistory (memoria persistente por proveedor en JSON) + cron job diario.
_Novedad:_ Evolución directa del script existente del equipo, no tecnología nueva desde cero.

**Decisión de almacenamiento:**
- **JSON + Git** como fuente de verdad (31 eventos y 9 contactos no justifican PostgreSQL)
- Git provee versionamiento, rollback y audit trail gratis
- Estructura diseñada para migración futura a DB si la escala crece

---

### Tema 2: Lógica de Negociación y Priorización

_Cómo el bot decide a quién contactar, cuándo y cómo_

**[Bot-Comms #2]: Sistema de Prioridad por Dependencia Crítica**
_Concepto:_ El bot contacta primero a Holland Wafels (14 eventos, 45% del calendario) y bloquea sus fechas antes de contactar a cualquier otro proveedor. Se establece el "esqueleto" del calendario y los demás se acomodan alrededor.
_Novedad:_ Orden estratégico basado en la concentración de dependencia.

**[Flow #49]: Motor de priorización por 4 factores**
_Concepto:_ Cada proveedor recibe un score basado en: (1) Urgencia — deadline de confirmación calculado hacia atrás desde la fecha del evento, (2) Impacto — número de eventos del proveedor, (3) Tipo de negociación — fija/recurrente/heredada/abierta/condicional, (4) Estado actual del evento.
_Fórmula:_ `SCORE = urgencia × 3 + impacto × 2 + tipo × 1`

**[Flow #50]: Algoritmo completo de secuenciamiento**
_Concepto:_ Cola de contacto ordenada por score descendente. Holland Wafels (14 eventos) → Koen Houwen (10 eventos) → Rocco van Velzen → Mirjam van Vliet → Paul vd Voort → Proveedores unitarios.

**[Flow #52]: Negociación VIP Holland Wafels**
_Concepto:_ En vez de negociar evento por evento (14 conversaciones), el bot propone una sesión de planificación anual con las 14 fechas propuestas en un solo documento. Se cierra en 1-2 interacciones en vez de 14.

**[SCAMPER #31]: Pub Quiz 100% automático**
_Concepto:_ Pub Quiz es predecible: primer jueves del mes, mismo venue, mismo precio, mismo contacto. Confirmar regla anual una vez, generar todas las fechas, solo alertar si hay conflicto con feriado.
_Novedad:_ Los eventos recurrentes con patrón fijo no necesitan confirmación mensual.

**[SCAMPER #35]: Simplificar proveedores unitarios**
_Concepto:_ Proveedores de 1 evento (Naranja Tours, Rene Wieben, Vicky Rodríguez) reciben un solo mensaje: "¿Mismo plan que 2026? Sí/No". Nivel de interacción proporcional a la complejidad.

**[SCAMPER #35b]: Anticipación de riesgos para proveedores de baja frecuencia**
_Concepto:_ Antes de confirmar, el bot analiza riesgos por proveedor: climático (tours de montaña en temporada de lluvias), capacidad humana (único operador sin backup), acceso (venue puede cerrar), temporal (cercanía a puentes/feriados). Riesgos configurables por proveedor en JSON.

**[Flow #57]: Flujo Maestro en dos fases**
_Concepto:_ FASE A: Cerrar pendientes del calendario 2026 primero. FASE B: Una vez cerrado 2026, socializar el borrador completo de 2027 en el chat grupal, esperar feedback del grupo (7 días), y luego iniciar negociaciones individuales. Los proveedores ya vieron el contexto antes de negociar.

---

### Tema 3: Comunicación y Canales

_Cómo el bot se comunica con proveedores y el grupo_

**[Flow #48]: Arquitectura de chat dual — Grupo + Privado**
_Concepto:_ Capa 1 — Chat grupal (solo lectura informativa): el bot publica updates de estado. Nadie negocia aquí. Capa 2 — Chat privado (negociación individual): el bot contacta a cada proveedor por privado. Cuando se cierra un acuerdo, se publica en el grupo.

**[Bot-Comms #7]: Multi-Canal Inteligente por Tipo de Proveedor**
_Concepto:_ WhatsApp para proveedores de alta frecuencia (Holland Wafels, Koen). Email formal para la Embajada NL. Canal preferido para guías independientes. El canal se adapta a la relación y formalidad.

**[Alien-Comms #15]: Perfiles de comunicación**
_Concepto:_ El bot adapta su tono según el proveedor: formal/institucional (Embajada), casual/comunitario (bares, guías), comercial/transaccional (Naranja Tours).

**[SCAMPER #27]: WhatsApp Web Automation en vez de Business API**
_Concepto:_ Para 9 contactos y ~50 mensajes al año, no se necesita la API enterprise de Meta. Una librería de automatización (Baileys/whatsapp-web.js) usando una sesión de WhatsApp Web existente reduce costo y burocracia a cero.

**[SCAMPER #37]: Flujo invertido — proveedor inicia la conversación**
_Concepto:_ Dar al proveedor un link/número donde él mismo inicia la confirmación. Los proveedores de alta frecuencia probablemente prefieren hacerlo a su ritmo.

**[Chaos #43]: Fallback de canales**
_Concepto:_ Si WhatsApp bloquea el número o falla la entrega, el bot escala automáticamente: WhatsApp → Telegram → Email. La operación no se detiene.

---

### Tema 4: Gestión de Conflictos y Disputas

_Cómo el bot maneja fechas ocupadas y disputas_

**[Bot-Comms #1]: Auto-Negociador de Fechas**
_Concepto:_ Al contactar a cada proveedor, el bot propone la fecha equivalente de 2026 trasladada a 2027, con análisis automático de conflictos con feriados mexicanos. No solo pregunta — llega con propuesta inteligente.

**[Chaos #39]: Race condition — dos confirman simultáneamente**
_Concepto:_ Lock optimista: el primero en confirmar bloquea la fecha, el segundo recibe "esa fecha ya está tomada" con alternativas inmediatas.

**[Flow #51]: Manejo de conflicto en negociación**
_Concepto:_ Fecha libre → confirmar. Fecha ocupada → proponer alternativas cercanas. Fecha con riesgo de feriado → informar y dejar que el proveedor decida.

**[Flow #53]: Protocolo de Disputa de Fechas (4 niveles)**
_Concepto:_
- Nivel 1: Negociación asistida — bot propone alternativas al solicitante
- Nivel 2: Compatibilidad por horario y venue — dos eventos el mismo día pueden coexistir si diferente venue/horario/audiencia
- Nivel 3: Escalamiento humano con contexto — bot presenta caso completo al director sin tomar partido
- Nivel 4: Reglas de precedencia configurables — tradición > deportivo, pagado > gratis, proveedor crítico > unitario

**[Flow #54]: Reglas de precedencia configurables**
_Concepto:_ Archivo `precedencia.json` con reglas que el bot aplica automáticamente. Última instancia siempre es el director del proyecto.

**Reglas de compatibilidad de fechas:**
- Mismo venue + mismo horario → CONFLICTO REAL (bloqueado)
- Mismo venue + diferente horario → Permitido si buffer de 3+ horas, requiere confirmación del venue
- Diferente venue + misma audiencia → Advertencia de canibalización de asistencia
- Diferente venue + diferente audiencia → Sin conflicto real

---

### Tema 5: Monitoreo y Automatización Continua

_Cómo el bot vigila y actúa día a día_

**[Flow #55]: Job Diario "El Vigilante"**
_Concepto:_ Cron job que ejecuta cada día a las 8am y escanea 5 dimensiones:
1. Urgencias — eventos con deadline atrasado o próximo (🔴 atrasado, 🟠 <7 días, 🟡 <14 días, 🔵 <30 días)
2. Dependencias — verifica si proveedores críticos han confirmado para desbloquear la cola
3. Timeouts activos — proveedores que no han respondido (3/7/14/21 días)
4. Oleadas de promoción — flyers pendientes de aprobar o publicar
5. Reporte al grupo — solo si hay novedades vs ayer (no spamear)

**[Chaos #40]: Protocolo de timeout (escalamiento progresivo)**
_Concepto:_ Día 3 → recordatorio amigable. Día 7 → segundo recordatorio con urgencia suave. Día 14 → escalar a coordinador. Día 21 → marcar evento "en_riesgo" + publicar en grupo. Día 30 → decisión final del director.

**[Bot-Comms #3]: Modo Condicional para Eventos Deportivos**
_Concepto:_ Eventos como el Mundial (solo en años que aplica) se manejan como reservas tentativas que se activan/desactivan según eventos externos. El bot es consciente de los ciclos (Mundial cada 4 años, próximo 2030).

**[Bot-Comms #4]: Motor de Reglas Implícitas**
_Concepto:_ Las 7 reglas no-escritas del calendario codificadas como restricciones configurables: no eventos en Semana Santa, no eventos en Navidad, julio-agosto ligeros, septiembre-octubre transición, Pub Quiz solo primer semestre (negociable), eventos deportivos condicionales, delegados sin gestión NV.

**[Bot-Comms #10]: Detector de Oportunidades**
_Concepto:_ El bot detecta meses vacíos y propone: "Julio quedó libre. ¿Activamos Pub Quiz de verano?" Convierte contingencias en oportunidades.

**[SCAMPER #32]: "Delegado" → "Semi-supervisado"**
_Concepto:_ Eventos "contact post zelf" reciben check-in pasivo 30 días antes. Si no hay respuesta en 7 días, escala al coordinador. Oversight sin micromanagement.

---

### Tema 6: Gestión de Flyers y Promoción

_Cómo se gestiona la cadena de promoción post-confirmación_

**[SCAMPER #29]: Confirmación dispara cadena completa**
_Concepto:_ Cuando el proveedor confirma la fecha, el bot en un solo flujo: (1) bloquea la fecha, (2) solicita/genera flyer, (3) crea evento en Eventbrite si aplica, (4) programa oleadas de promoción según tier.

**[SCAMPER #28]: Templates auto-generados de flyer**
_Concepto:_ El bot genera un draft del flyer con datos del evento. El humano solo revisa y aprueba.

**[SCAMPER #28b]: Ciclo de rechazo de flyer**
_Concepto:_ Si el humano rechaza el draft, loop de revisión con máximo 3 iteraciones antes de escalar a diseño manual. Si no responde, mismo protocolo de timeout.

**[SCAMPER #28c]: Versionamiento de flyers por oleada**
_Concepto:_ Para eventos tier Grande: v1 "save the date" (-60 días), v2 "detalles + precios" (-30 días), v3 "últimos lugares" (-7 días). Contenido evolutivo, no repetitivo.

**[SCAMPER #34]: Tier calculado, no asignado**
_Concepto:_ El bot calcula el tier basándose en reglas: ¿tiene Eventbrite? ¿Precio > $100? ¿Evento único anual? Las características determinan el tier automáticamente.

**[Flow #56]: Flujo de Flyers — NV vs Proveedor**
_Concepto:_ Dos flujos según columna N del calendario:
- N = número (1 o 3): Flyer responsabilidad del **Content Manager de NV** (nombre: Hanna van Rijsse, teléfono: +528120264857). El content manager centraliza todos los flyers de NV.
- N = "Flyer/[nombre]": El proveedor produce su propio flyer, pero NV (content manager) valida antes de publicar.
- N = "x": Sin flyer.

**Cadena por tier:**
- GRANDE: Flyer v1 (-90d) → Oleada 1 (-60d) → Eventbrite (-60d) → Oleada 2 (-30d) → Oleada 3 (-7d) → Evento → Reel (+3d)
- MEDIANO: Flyer (-45d) → Eventbrite si aplica (-30d) → Oleada única (-17d) → Recordatorio (-7d)
- REGULAR: Flyer + WhatsApp + RRSS (-7d) → Recordatorio (-1d)
- DELEGADO: Sin acción de promoción

---

### Tema 7: Análisis Morfológico — Combinaciones Evaluadas

| # | Nombre | Combinación | Veredicto |
|---|--------|-------------|-----------|
| #21 | MVP Pragmático | WhatsApp + JSON + LangChain | **Recomendado como punto de partida** |
| #22 | Agente Inteligente | WhatsApp + PostgreSQL + IA completa | Aspiracional — fase 2 |
| #23 | Híbrido Evolutivo | MVP → crece con necesidad | **Estrategia de evolución** |
| #24 | Delegador Inteligente | Google Sheets como backend | Descartado — no escala |
| #25 | Multi-Canal Adaptativo | WhatsApp + Telegram + Email | Deseable — fase 2 |

---

### Tema 8: Preguntas Abiertas (pendientes de decisión del director)

| # | Pregunta | Impacto |
|---|----------|---------|
| #11 | ¿Plan B si Koen Houwen (10 eventos) no está disponible? | Riesgo de concentración humana |
| #12 | ¿Alternativas si Holland Wafels no puede en 2027? | 45% del calendario depende de 1 venue |
| #13 | ¿Julio-agosto vacíos es decisión estratégica o inercia? | Oportunidad o pausa intencional |
| #14 | ¿Quién absorbe el costo de los 26 eventos gratuitos? | Modelo financiero no visible |
| #19 | ¿Eventos fusión cultural (Día de Muertos holandés)? | Feriados como oportunidad, no restricción |
| #20 | ¿KalendBot como "décimo miembro" del equipo? | Alcance de la automatización |

---

## Árboles de Decisión

### Árbol 1: Flujo Maestro — Ciclo de vida del calendario

```
INICIO DE KALENDBOT
│
╔══════════════════════════════════════════════╗
║  FASE A: CERRAR CALENDARIO 2026 PENDIENTE   ║
╚══════════════════════════════════════════════╝
│
├─ 1. Cargar calendario-2026.json
│   ├─ Identificar eventos con estado ≠ "confirmado"
│   ├─ Filtrar solo eventos FUTUROS (fecha > hoy)
│   └─ Generar lista de PENDIENTES 2026
│
├─ 2. Para cada pendiente 2026:
│   ├─ Ejecutar flujo de negociación (Árbol 2)
│   ├─ Priorizar por urgencia (el más próximo primero)
│   └─ Confirmar fecha → actualizar calendario
│
├─ 3. ¿Todos los eventos 2026 confirmados o resueltos?
│   ├─ NO → Seguir trabajando pendientes (job diario monitorea)
│   └─ SÍ → Publicar en grupo:
│       "✅ Calendario 2026 cerrado. Próximo paso: planificar 2027."
│
╔══════════════════════════════════════════════╗
║  FASE B: SOCIALIZAR Y NEGOCIAR 2027         ║
╚══════════════════════════════════════════════╝
│
├─ 4. Generar borrador calendario 2027
│   ├─ Trasladar fechas confirmadas de 2026
│   ├─ Ajustar por feriados 2027
│   ├─ Detectar conflictos y oportunidades
│   └─ Excluir eventos que no aplican (ej: Mundial)
│
├─ 5. Socialización en grupo
│   ├─ Bot publica borrador completo en grupo
│   ├─ Ventana de feedback grupal (7 días)
│   └─ Director aprueba borrador general
│
├─ 6. Negociación individual 2027
│   ├─ Ejecutar cola de contacto por score (Árbol 2)
│   └─ Cada confirmación actualiza calendario + grupo
│
└─ 7. Monitoreo continuo (Job diario — Árbol 7)
```

### Árbol 2: Flujo de negociación por tipo de proveedor

```
CONTACTAR PROVEEDOR
│
├─ CRÍTICO (Holland Wafels / Koen) → FLUJO VIP
│   ├─ Enviar propuesta completa del año
│   ├─ "Todo bien" → Bloquear todas las fechas de golpe
│   ├─ "Cambiar X fechas" → Verificar disponibilidad → ajustar
│   └─ No responde → Timeout (Árbol 3)
│
├─ PATRÓN RECURRENTE (Pub Quiz, Vrijmibo) → FLUJO REGLA ANUAL
│   ├─ "¿Seguimos con primer jueves del mes?"
│   ├─ Sí → Generar 12 fechas automático, verificar cada una
│   └─ Cambio de regla → Regenerar fechas
│
├─ FECHA FIJA EXTERNA (F1) → CONFIRMACIÓN SIMPLE
│   ├─ "F1 se estima para [fecha]. ¿Organizamos viewing?"
│   └─ Sí → Bloquear como tentativo hasta fecha oficial
│
├─ UNITARIO (Naranja Tours, Rene, Vicky) → SIMPLIFICADO + RIESGOS
│   ├─ "¿Mismo plan que 2026?"
│   ├─ Agregar alertas de riesgo (climático, disponibilidad, acceso)
│   └─ Sí → Bloquear | Cambiar → Verificar | No → Cancelar
│
└─ DELEGADO (contact post zelf) → CHECK-IN PASIVO
    ├─ "¿[Evento] sigue en pie para 2027?"
    └─ No responde 7 días → Escalar a coordinador
```

### Árbol 3: Protocolo de timeout y escalamiento

```
MENSAJE ENVIADO → SIN RESPUESTA
│
├─ Día 3 → Recordatorio amigable
├─ Día 7 → Segundo recordatorio con urgencia suave
├─ Día 14 → Escalar a coordinador
├─ Día 21 → Marcar evento "en_riesgo" + publicar en grupo
└─ Día 30 → Director decide: cancelar / buscar alternativa / esperar
```

### Árbol 4: Flujo de disputa de fechas

```
FECHA SOLICITADA YA OCUPADA
│
├─ ¿Es conflicto real? (misma audiencia/venue/horario)
│   ├─ NO → Permitir ambos + advertencia informativa
│   └─ SÍ ↓
│
├─ ¿El solicitante acepta alternativa del bot?
│   ├─ SÍ → Resuelto automáticamente
│   └─ NO ↓
│
├─ ¿Hay regla de precedencia configurada?
│   ├─ SÍ → Aplicar regla + notificar al afectado con alternativas
│   └─ NO ↓
│
└─ Escalar al director con análisis completo de ambas partes
```

### Árbol 5: Post-confirmación — cadena automática

```
FECHA CONFIRMADA ✅
│
├─ Actualizar calendario JSON + publicar en grupo
├─ Determinar tier de promoción (calculado por reglas)
├─ Determinar responsable de flyer (NV o proveedor)
├─ Ejecutar cadena según tier (Árbol 6)
├─ Crear evento Eventbrite (si aplica)
└─ Programar oleadas de promoción
```

### Árbol 6: Flujo de flyers

```
EVENTO NECESITA FLYER
│
├─ Columna N = número (1 o 3) → CONTENT MANAGER DE NV
│   ├─ Bot notifica al content manager (Hanna van Rijsse, +528120264857)
│   ├─ Content manager produce draft
│   ├─ Coordinador del evento aprueba (máx 3 iteraciones)
│   └─ Timeout si no entrega a tiempo → escalar
│
├─ Columna N = "Flyer/[nombre]" → PROVEEDOR
│   ├─ Bot solicita flyer al proveedor
│   ├─ Content manager de NV valida
│   └─ Timeout si no envía → escalar
│
└─ Columna N = "x" → SIN FLYER
```

### Árbol 7: Job diario "El Vigilante"

```
EJECUTA CADA DÍA A LAS 8AM
│
├─ 1. Escanear urgencias (deadlines atrasados o próximos)
├─ 2. Verificar dependencias (¿proveedor crítico confirmó?)
├─ 3. Verificar timeouts activos (proveedores sin responder)
├─ 4. Verificar oleadas de promoción (flyers pendientes)
└─ 5. Reporte al grupo (solo si hay novedades)
```

---

## Decisiones Arquitectónicas

### Stack Tecnológico

| Componente | Decisión | Razón |
|------------|----------|-------|
| **Orquestador** | LangChain (agente REACT conversacional) | Evolución directa de app_conversacional.py existente |
| **LLM** | GPT-4o-mini (temperature 0.1) | Bajo costo, suficiente para negociación de fechas |
| **Almacenamiento** | JSON + Git | 31 eventos no justifican PostgreSQL. Git da versionamiento gratis |
| **Memoria** | FileChatMessageHistory (1 JSON por proveedor) | Persiste automáticamente, sin código custom |
| **Canal primario** | WhatsApp (Web automation) | 21/31 eventos ya usan WhatsApp |
| **Cron jobs** | schedule / APScheduler | Job diario "El Vigilante" |

### Estructura de datos

```
kalendbot-data/
├── memories/
│   ├── holland-wafels.json       ← FileChatMessageHistory auto-generado
│   ├── koen-houwen.json
│   ├── christiaan-kemper.json
│   ├── rocco-van-velzen.json
│   ├── mirjam-van-vliet.json
│   ├── paul-vd-voort.json
│   ├── naranja-tours.json
│   ├── rene-wieben.json
│   └── vicky-rodriguez.json
├── config/
│   ├── restricciones.json        ← Feriados MX + reglas implícitas
│   ├── tiers-promocion.json      ← Grande/Mediano/Regular/Delegado
│   ├── eventos-externos-2027.json ← F1, Champions + ciclos deportivos
│   └── precedencia.json          ← Reglas de disputa de fechas
├── proveedores/
│   ├── holland-wafels.json       ← Datos + contacto + venue + riesgos
│   ├── de-sprinkhaan.json
│   ├── embajada-nl.json
│   └── ...
├── calendario-2026.json
└── calendario-2027.json
```

### Modelo de evento (JSON)

```json
{
  "id": "koningsdag-2027",
  "nombre": "Koningsdag",
  "fecha_propuesta": "2027-04-25",
  "fecha_confirmada": null,
  "estado": "tentativo",
  "proveedor_id": "holland-wafels",
  "contacto_id": "rocco-van-velzen",
  "venue_id": "holland-wafels",
  "tier_promocion": "grande",
  "precio": { "adulto": 200, "nino": 100 },
  "eventbrite": true,
  "canales": ["flyer", "reel", "eventbrite", "whatsapp", "rrss", "email"],
  "flyer_responsable": "nv",
  "restricciones_detectadas": ["Semana Santa 2027: verificar proximidad"],
  "condicional": false,
  "delegado": false
}
```

### Los 7 Tools de LangChain

| Tool | Nombre | Función |
|------|--------|---------|
| 1 | CalendarManager | Leer/actualizar calendario, verificar conflictos, bloquear fechas |
| 2 | ProviderManager | Leer info de proveedores, eventos asignados, riesgos |
| 3 | DateLocker | Bloquear fecha con lock optimista |
| 4 | ConflictDetector | Analizar fecha vs feriados, eventos confirmados, reglas |
| 5 | GroupNotifier | Publicar updates en chat grupal |
| 6 | FlyerManager | Solicitar/rastrear flyers, ciclo de aprobación |
| 7 | RulesEngine | Consultar tiers, precedencia, restricciones |

### Componente de memoria

```python
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain.memory import ConversationBufferMemory

class ProviderMemoryManager:
    def __init__(self, memory_dir="data/memories"):
        self.memory_dir = memory_dir
        os.makedirs(memory_dir, exist_ok=True)
        self.memories = {}

    def get_memory(self, provider_id: str) -> ConversationBufferMemory:
        if provider_id not in self.memories:
            history = FileChatMessageHistory(
                file_path=f"{self.memory_dir}/{provider_id}.json"
            )
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                chat_memory=history
            )
            self.memories[provider_id] = memory
        return self.memories[provider_id]
```

---

## Resumen de la Sesión

**Logros creativos:**
- 58 ideas generadas en 6 técnicas distintas
- 7 árboles de decisión que mapean todo el ciclo de vida del bot
- Stack tecnológico definido (LangChain + JSON + WhatsApp + Git)
- Estructura de datos completa con modelo de evento
- Flujo maestro en 2 fases: cerrar 2026 → socializar y negociar 2027
- Protocolo completo de disputas, timeouts y escalamiento
- Gestión de flyers separada (Content Manager NV vs proveedores)
- Job diario de monitoreo continuo

**Narrativa de la sesión:**
La sesión comenzó explorando posibilidades radicales con "What If Scenarios" y rápidamente se ancló en datos reales del calendario 2026 (31 eventos, 9 contactos, 5 venues). El "Alien Anthropologist" reveló preguntas incómodas que quedaron como decisiones pendientes del director. El análisis morfológico descartó PostgreSQL a favor de JSON+Git. SCAMPER refinó los flujos de flyers, negociación y eventos externos. Chaos Engineering stress-testeó los escenarios de fallo (timeouts, disputas, race conditions). Decision Tree Mapping consolidó todo en 7 árboles ejecutables. Finalmente, la decisión de usar LangChain sobre n8n se tomó por la naturaleza conversacional del bot y la existencia de un script base funcional.

**Próximos pasos:**
1. Crear la estructura de carpetas `kalendbot-data/` con los JSON iniciales
2. Migrar datos del Excel 2026 al formato JSON definido
3. Implementar los 7 Tools de LangChain basándose en app_conversacional.py
4. Integrar WhatsApp (Web automation) como canal de entrada
5. Implementar el cron job diario "El Vigilante"
6. Probar con Holland Wafels como primer proveedor (mayor impacto)
7. Resolver las preguntas abiertas con el director del proyecto

---

*Sesión de brainstorming facilitada con técnicas: What If Scenarios, Alien Anthropologist, Morphological Analysis, SCAMPER, Chaos Engineering, Decision Tree Mapping — Marzo 2026*
