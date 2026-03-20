# Análisis del Calendario Anual NV Mexico 2026

## Resumen ejecutivo

El archivo **NV_2026_Jaarkalender_V2_0.xlsx** contiene la planificación anual preliminar de la asociación neerlandesa en México (NV Mexico) para 2026. Incluye 31 eventos distribuidos a lo largo del año, con 2 eventos recurrentes mensuales, 9 organizadores/contactos y 5 venues principales. El calendario abarca dos hojas: una principal con el detalle completo de cada evento y una hoja simplificada ("Hoja1") con un resumen reducido.

---

## 1. Tipología y lógica de eventos

### Eventos recurrentes (fijos mensuales)

| Evento | Regla de fecha | Hora | Entrada | Responsable |
|--------|---------------|------|---------|-------------|
| Pub Quiz | 1er jueves del mes | 7 pm | $75 MXN | Christiaan Kemper |
| Vrijmibo (after-work) | Último viernes del mes | 4 pm | Gratis | Andre Major |

El Pub Quiz tiene instancias fijas listadas individualmente: 5 Feb, 5 Mar, 5 Abr, 7 May y 4 Jun. No se listan instancias de julio a diciembre, lo que sugiere una pausa en el segundo semestre. El Vrijmibo no tiene fechas individuales listadas.

### Categorías de eventos únicos

| Categoría | Cantidad | Ejemplos |
|-----------|----------|----------|
| Deportivo / fútbol | 7 | Mundial (fase de grupos + eliminatorias), Champions League, Nations League |
| Cultural / tradición | 5 | Koningsdag, Sinterklaas, Gran Dictado Neerlandés, Elfstedentocht |
| Social / comunidad | 4 | Recepción de Año Nuevo (incl. Asamblea), Convivencia voluntarios, Día al aire libre |
| Publicación | 3 | Revista POPO — ediciones de abril, septiembre y diciembre |
| Outdoor / tour | 3 | Escalada Pico de Águila (Ajusco), Tour Iztaccíhuatl, Visita guiada Chapultepec |
| Automovilismo | 1 | F1 GP México |

### Eventos condicionales

Los partidos del Mundial de fútbol en rondas eliminatorias (32avos, 16avos, 8vos en junio-julio) son **condicionales**: solo se activan si la selección de Holanda avanza en el torneo. Esto implica que el calendario de julio puede quedar vacío si Holanda no clasifica.

---

## 2. Restricciones identificadas

### 2.1 Restricciones de promoción (columna "flyer moment")

Existe un sistema escalonado de anticipación para la difusión de cada evento, codificado en la columna K:

| Nivel | Anticipación requerida | Canales de difusión | Eventos que aplican |
|-------|----------------------|---------------------|---------------------|
| **Grande** | -60, -30 y -7 días (3 oleadas) | Flyer + Reel + Eventbrite + WhatsApp + RRSS + Email | Koningsdag, Sinterklaas |
| **Mediano** | -17 a -30 días | Flyer + Eventbrite + WhatsApp + RRSS + Email | Recepción Año Nuevo, Buitendag, Tour Iztaccíhuatl |
| **Regular** | -4 a -7 días | Flyer + WhatsApp + RRSS | Pub Quiz, partidos de fútbol, Dictado, F1 |
| **Delegado** | Variable (el partner decide) | Marcados como "contact post zelf" | Pub Quiz individual, Elfstedentocht, Taalkamp |
| **Publicación** | 0 días | Solo se anuncia el día de publicación | Revista POPO (3 ediciones) |

### 2.2 Restricciones de flyers (columna N)

La columna N indica la responsabilidad y volumen de flyers:

- **N = 1**: NV produce 1 flyer para el evento (14 eventos)
- **N = 3**: NV produce 3 oleadas de flyers — solo para los eventos grandes (Koningsdag, Sinterklaas, Vrijmibo)
- **N = "Flyer/ [nombre]"**: El partner produce su propio flyer (~10 eventos)
- **N = "x"**: No se produce flyer (Convivencia voluntarios)

### 2.3 Reels post-evento (columna O)

Solo 6 eventos tienen reel programado después del evento (marcados como "reel aft/desp"): Recepción Año Nuevo, Koningsdag, partidos del Mundial de fase de grupos, Sinterklaas y Recepción 2027. Esto corresponde a los eventos de mayor escala.

### 2.4 Restricciones de venta de boletos

Solo 5 eventos utilizan Eventbrite para venta de boletos (cupo limitado):

| Evento | Precio entrada |
|--------|---------------|
| Recepción de Año Nuevo | $200 MXN |
| Koningsdag | $100 niños / $200 adultos |
| Día al aire libre (Cuernavaca) | $200 MXN |
| Sinterklaas | $100 niños / $200 adultos |
| Recepción Año Nuevo 2027 | $200 MXN |

---

## 3. Cruces con feriados mexicanos

### Conflictos detectados

| Evento NV | Fecha | Feriado MX cercano | Nivel de impacto | Notas |
|-----------|-------|--------------------|--------------------|-------|
| Koningsdag | 25 Abr → **movido al 3 May** | 1 May (Día del Trabajo) + Semana Santa | **Alto** | Ya resuelto: el texto del evento confirma que se movió explícitamente por Semana Santa |
| Taalkamp niños | 30 Abr – 3 May | 1 May + puente | **Medio** | Aprovecha vacaciones escolares — probablemente intencional |
| Escalada Ajusco | 14 Mar | 16 Mar (Benito Juárez, lunes) | **Bajo** | El evento es sábado, el feriado lunes; podrían beneficiarse del fin de semana largo |
| F1 México | 1 Nov | 1-2 Nov (Día de Muertos) | **Medio** | Competencia directa por atención; muchas familias tienen planes para Día de Muertos |
| Sinterklaas | 5 Dic | Sin feriado oficial MX | **OK** | Cae viernes — potencial puente pero sin conflicto |

### Feriados mexicanos oficiales 2026 (referencia)

- 1 Ene: Año Nuevo
- 2 Feb: Día de la Constitución (se mueve al lunes)
- 16 Mar: Natalicio de Benito Juárez (lunes)
- Semana Santa: variable (abril)
- 1 May: Día del Trabajo
- 16 Sep: Día de la Independencia
- 1-2 Nov: Día de Muertos
- 16 Nov: Revolución Mexicana (se mueve al lunes)
- 25 Dic: Navidad

---

## 4. Coparticipación y dependencias

### Mapa de partners

| Partner | Rol | Eventos involucrados | Dependencia |
|---------|-----|---------------------|-------------|
| **Holland Wafels** | Venue principal + co-organizador | Pub Quiz (6x), fútbol (6x), Dictado, Champions, F1 ≈ **14 eventos** | **Crítica** — alberga ~45% de la actividad anual |
| **De Sprinkhaan** | Organizador programa infantil | Elfstedentocht, Taalkamp, Koningsdag (parte infantil), Sinterklaas | Alta — único proveedor de contenido infantil |
| **Embajada NL** | Anfitrión institucional | Recepción Año Nuevo 2026 y 2027 (incl. Asamblea) | Media — 2 eventos al año pero de alto perfil |
| **Redacción POPO** | Publicación independiente | 3 ediciones anuales (Abr, Sep, Dic) | Baja — operan de forma autónoma |
| **Naranja Tours** | Operador turístico | Tour Iztaccíhuatl (25% descuento para miembros NV) | Baja — 1 evento anual |
| **Rene Wieben** | Guía outdoor personal | Escalada Pico de Águila (Ajusco) | Baja — 1 evento anual |
| **Vicky Rodríguez** | Guía cultural | Visita guiada Castillo de Chapultepec | Baja — 1 evento anual |
| **AtK** | Co-organizador social | Día al aire libre en Cuernavaca | Baja — 1 evento anual |
| **Paul vd Voort / Jasper de Gelder** | Coordinador artístico | Paisaje Intercultural (exposición) | Baja — 1 evento anual |

### Concentración de contactos

Solo 9 personas de contacto gestionan los 31 eventos. Los más activos son:

1. **Koen Houwen** — 10 eventos (todos los deportivos + Dictado + Convivencia voluntarios)
2. **Christian Kemper** — 6 eventos (todos los Pub Quiz)
3. **Rocco van Velzen** — 4 eventos (Recepción Año Nuevo x2, Koningsdag, Convocatoria junta)
4. **Mirjam van Vliet** — 3 eventos (Elfstedentocht, Taalkamp, Sinterklaas)
5. **Paul vd Voort** — 4 eventos (POPO x3, Paisaje Intercultural)

---

## 5. Reglas implícitas (no escritas) identificadas

Del análisis del patrón de distribución de eventos se deducen las siguientes reglas no documentadas:

| Regla implícita | Evidencia |
|-----------------|-----------|
| **No eventos en Semana Santa** | Koningsdag fue movido explícitamente al 3 de mayo citando Semana Santa |
| **No eventos en Navidad / Año Nuevo** | Diciembre solo tiene la publicación de POPO; enero arranca con la Recepción |
| **Julio-agosto son meses ligeros** | Solo Mundial (condicional) y Rondleiding — probable periodo vacacional de la comunidad |
| **Septiembre-octubre son meses de transición** | Solo POPO en septiembre; octubre retoma con F1 |
| **Pub Quiz se pausa en el segundo semestre** | Última instancia listada: 4 de junio. No hay Pub Quiz de julio a diciembre |
| **Eventos de fútbol son condicionales** | Las rondas eliminatorias del Mundial dependen de que Holanda avance |
| **Eventos delegados no requieren gestión de NV** | Los marcados "contact post zelf" tienen todas las columnas de difusión en "x" |

---

## 6. Resumen de canales de difusión

Conteo de eventos por canal (datos de las fórmulas del archivo):

| Canal | Eventos que lo usan |
|-------|-------------------|
| Flyers (pre-evento) | 14 |
| Reels (post-evento) | 7 |
| Eventbrite | 5 |
| WhatsApp | 21 |
| Instagram / Facebook / TikTok | 21 |
| Email | 9 |

WhatsApp y redes sociales son los canales universales. Email se reserva para los eventos de mayor escala. Eventbrite solo para eventos con boleto.

---

*Análisis generado a partir de NV_2026_Jaarkalender_V2_0.xlsx — Marzo 2026*
