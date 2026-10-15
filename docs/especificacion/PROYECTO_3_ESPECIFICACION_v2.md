# Proyecto 3 · Apoyo Inteligente para Familias
## Especificación completa para el agente del IDE

> Hackatón de IA Generativa **AWS Breaking Barriers Chile 2026** · 14–16 de octubre de 2026 · Universidad de Chile (Beauchef 851).
> Desafío 3 de **Fundación Integra**: *"Conectando a familias con beneficios clave"*.
> Referente: Lissette Saavedra (Dirección Ejecutiva, Integra).
>
> Este documento es la fuente de verdad del proyecto. Léelo completo antes de escribir código. Los datos vienen en `participantes_e3.zip` (descomprimir en `data/`).

> **Versión 2 · reorganizada por roles (14-10-2026).** Cambios respecto de la v1:
> 1. Nueva **idea final del equipo** (§2.6): base de datos con el zip → cruce con beneficios → **ficha de matrícula de Integra como ventana de contexto** → la tía ve los beneficios ordenados por **prioridad, urgencia y beneficio para la familia**.
> 2. Nueva sección **§2.7 Ficha de matrícula como ventana de contexto** (mapeo campo por campo y qué puede ver la IA).
> 3. **§8 Priorización reescrita** con tres ejes visibles para la tía: Urgencia · Beneficio para la familia · Vulnerabilidad del hogar.
> 4. Nueva sección **§18 Roles del equipo** (4 integrantes, uno sin código), con contratos entre roles para trabajar en paralelo.
> 5. **§15 Plan de trabajo** y **§17 Definición de terminado** ahora tienen dueño por tarea.
>
> **Convención de rutas:** todas las rutas de este documento se interpretan desde la raíz del repositorio, aunque este archivo viva en `docs/especificacion/`.
>
> Navegación: [roles y responsabilidades](../equipo/ROLES_Y_RESPONSABILIDADES.md) · [estructura del repositorio](../arquitectura/ESTRUCTURA_REPOSITORIO.md) · [flujo de la ficha](../producto/FLUJO_DE_FICHA.md)

---

## 0. Resumen en una frase

Una herramienta **para la educadora / directora del jardín ("la tía")** que, a partir de los datos de cada familia, le dice **qué beneficios del Estado (y de organizaciones locales) podría obtener esa familia, por qué, qué le falta y dónde ir**, y le entrega un **guion simple para contárselo cara a cara** (boca a boca), más un mensaje que la familia se puede llevar. La tía registra que conversó con la familia y eso alimenta el KPI: **100 % de las familias informadas**.

**En concreto (v2):** cargamos el dataset E-3 en una base de datos, lo **cruzamos con el catálogo de beneficios** mediante un motor de reglas, y sumamos la **ficha de inscripción y matrícula de Integra** como ventana de contexto de cada familia. Con eso, la tía ve para cada familia los beneficios ordenados por **prioridad**, con tres señales simples: **qué tan urgente es**, **cuánto le ayudaría a la familia** y **qué tan vulnerable es el hogar**.

La IA no reemplaza a la tía: la convierte en una "orientadora experta" en 2 minutos, que es exactamente lo que hizo la tía Ana con Don Julio.

---

## 1. Contexto del desafío (lo que dice Integra)

### 1.1 La historia
Don Julio llega al jardín Agualuna de Dalcahue sin conocer los beneficios del Estado. La tía Ana, directora, lo orienta con información que ella misma recolectó en el CESFAM. Gracias a eso Don Julio accede al programa "Más Adulto Mayor Autovalente" y se mantiene activo para jugar con su nieto Benjamín y apoyarlo en su desarrollo.

### 1.2 Datos duros
1. **El boca a boca es la forma más común** en que las familias se enteran de beneficios del Estado a nivel local.
2. **Hay una brecha** en la entrega de beneficios a las familias que más lo necesitan.
3. Integra puede llegar a **85.000 familias** a través de sus **1.200 jardines y salas cuna**.

### 1.3 Problema de fondo
Asimetría de información: las familias no conocen los beneficios a los que podrían acceder, y tienen **altos costos de transacción** para informarse institución por institución.

### 1.4 Desafío textual
> Crear una herramienta tecnológica que esté constantemente **mapeando y clasificando los beneficios del Estado en cada territorio**. Una **puerta de entrada única, amigable y cercana**, que ayude a navegar un sistema complejo.

### 1.5 Impacto y escalabilidad (para el pitch)
- **Ahora:** rompe la asimetría de información; las familias acceden a más apoyos; los niños y niñas reciben mejor apoyo de sus familias fuera del jardín.
- **Replicable:** en cualquier institución que sea puerta de entrada a información (ChileAtiende, CESFAM, municipalidades).
- **Escalable:** a cualquier organización con oficinas de atención ciudadana.
- **Efecto multiplicador:** mejor calidad de vida de quienes acceden a más beneficios.

### 1.6 KPIs que hay que mover
| KPI | Línea base | Meta |
|---|---|---|
| ⭐ Familias informadas del set de beneficios del Estado | 0 % | 100 % (85 mil familias) |
| Familias **nuevas** que ingresan cada año informadas | 0 % | 100 % |

**La herramienta debe medir estos dos KPIs por sí misma** (registro de conversaciones + panel).

### 1.7 Integra en números (para el pitch)
+27.500 trabajadoras (98 % mujeres) · +1.200 jardines y salas cuna · 60 % de la población más vulnerable · 36 años · 320 comunas (95 %) · 25 % de la matrícula pública de educación parvularia · +85.000 niños/as y familias al año. Integra ya tiene una app ("IntegrApp") → canal futuro natural.

---

## 2. Visión de producto (decisión del equipo)

### 2.1 Usuario principal: la tía (educadora / directora del jardín)
- Usa celular o tablet, muchas veces con mala conexión y poco tiempo.
- No es experta en beneficios sociales, pero **es la persona de confianza** de la familia.
- Necesita: saber de qué hablarle a cada familia, con palabras simples, sin equivocarse ni prometer cosas que no puede asegurar.

### 2.2 Usuario secundario: la familia
- **No usa la herramienta directamente en el MVP.** Recibe la información de la tía, en persona, y se lleva una tarjeta impresa o un mensaje de WhatsApp.

### 2.3 Usuario terciario: Integra (dirección regional / nacional)
- Ve el avance del KPI por jardín, comuna y región, y las brechas más frecuentes (beneficios a los que muchas familias califican pero no acceden).

### 2.4 Principios no negociables
1. **La elegibilidad la decide un motor de reglas determinista y trazable. El LLM nunca decide si una familia califica**; solo explica, redacta y conversa a partir del resultado del motor.
2. **Nunca prometer.** Siempre "podría calificar", "vale la pena consultar". Todo resultado lleva el aviso: *"Orientación referencial; no determina derechos. Confirmar en la institución."*
3. **Lenguaje simple** (nivel lectura básica, sin siglas sin explicar, frases cortas, tono cercano chileno, trato de usted).
4. **Lo que no se sabe se convierte en pregunta.** Si falta un dato (p. ej. si hay alguien embarazada), la herramienta no dice "no califica": le sugiere a la tía una pregunta para hacer en la conversación.
5. **Privacidad:** datos mínimos, nada sensible a terceros, nada de datos personales en los prompts más allá de lo imprescindible (usar IDs y atributos, no nombres ni RUT).
6. **Mobile-first y funciona con poca conexión** (PWA; la ficha de una familia debe poder verse ya cargada).

### 2.5 Flujo principal (el "momento boca a boca")
```
Tía abre la app → ve su jardín → lista de familias ordenada por prioridad
   → toca una familia → ve "3 cosas para conversar con esta familia"
       (beneficio + por qué + qué tiene que hacer + dónde ir + qué preguntar)
   → conversa en la puerta / reunión de apoderados
   → marca "Conversado" (+ qué beneficios mencionó + siguiente paso acordado)
   → opcional: imprime tarjeta / envía WhatsApp a la familia
   → KPI sube
```

### 2.6 Idea final del equipo: el flujo de datos de punta a punta
```
participantes_e3.zip ──► [1] Base de datos (DuckDB)
                              │  tablas normalizadas + vistas
                              ▼
catálogo 20 beneficios ──► [2] Cruce familia × beneficio (motor de reglas, §6)
                              │  10.000 evaluaciones con traza
                              ▼
gestiones/pagos ─────────► [3] Estado de acceso (§7): ¿ya lo tiene, en trámite, brecha?
                              │
ficha de matrícula ──────► [4] Ventana de contexto de la familia (§2.7)
                              │  completa datos faltantes y da contexto humano
                              ▼
                          [5] Priorización (§8): Urgencia · Beneficio · Vulnerabilidad
                              │
                              ▼
                          [6] Vista de la tía: "3 cosas para conversar" + guion IA
                              │
                              ▼
                          [7] Registro de conversación → KPIs (§11)
```
Las capas 1–3 y 5 son **deterministas** (SQL + Python). La IA (capa 6) solo redacta a partir de lo que entregan las capas anteriores. La ficha (capa 4) entra al motor solo como hechos `DECLARADO` y al LLM solo en su versión filtrada (§2.7.3).

### 2.7 La ficha de matrícula como ventana de contexto

La **Ficha de Inscripción y Matrícula** de Integra (formato 2019, `Ficha_Inscripcionmatricula_2019_V_B_.pdf`) es lo que el jardín **ya sabe** de cada familia al matricular. La usamos de tres formas:

1. **Fuente de hechos** para el motor: campos que corresponden a un `campo_dato` de las reglas entran como hechos `estado_dato=DECLARADO, acreditada=false` (dan resultados `PRELIMINAR`).
2. **Contexto para la tía y para la IA:** ayuda a decidir el tono, el formato del mensaje y la urgencia, sin decidir elegibilidad.
3. **Plantilla del cuestionario de familia nueva** (S2): en vez de inventar preguntas, digitalizamos los campos útiles de la ficha (§10).

> La ficha es un **formato vacío**: el dataset E-3 no trae fichas llenas. Para la demo se genera una **ficha sintética por familia** derivada del dataset (`backend/app/context/ficha_sintetica.py`); los campos que no se pueden derivar quedan como `NO_INFORMADO` y nunca se inventan.

#### 2.7.1 Mapeo ficha → datos → beneficios
| Campo de la ficha | Dato / `campo_dato` en E-3 | Beneficios que toca | Uso |
|---|---|---|---|
| Edad del niño/a al 31 de marzo | `integrantes.fecha_nacimiento_sintetica` → `edad`, `edad_meses` | BEN-007, 009, 012, 015 | Motor |
| N.º de hermanos < 6, 6–14, 15–18 | conteo de `integrantes` HIJO_HIJA por edad | BEN-001, 002, 007, 013, 014, 015 | Motor (candidatos) + control de consistencia: si la ficha y el dataset no coinciden → pregunta |
| Hermanos con discapacidad · NEE (tipo, permanente/transitoria, certificado médico) | `DISCAPACIDAD.SEVERIDAD` (la ficha **no** trae severidad) | BEN-006, BEN-019 | Pregunta: "¿Tiene credencial de discapacidad?" · **diagnóstico nunca va al LLM** |
| ¿Tiene Registro Social de Hogares? | `familias.estado_rsh_corte` | BEN-001, 002, 003, 006 | Motor; si "no" → acción concreta: actualizar RSH |
| Ingreso per cápita (tabla del manual) | `INGRESO_HOGAR.MONTO / numero_integrantes_corte` | BEN-005, 011, 019 | Motor (DECLARADO) |
| Beneficiario Subsistema Seguridades y Oportunidades / Chile Solidario | `SUBSISTEMA_SSYO.PARTICIPACION` | BEN-004, 010, 011, 012, 013 | Motor (DECLARADO) |
| Beneficiario Chile Crece Contigo | `ACCESO` (programa ChCC) | BEN-008, BEN-009 | Estado de acceso ("ya lo tiene") |
| Última evaluación del cuaderno de salud | `CONTROL_SALUD.INFANTIL_RED_PUBLICA` + **fecha** | BEN-009, BEN-012 | Motor: **resuelve `dias_desde_control`**, que en E-3 solo existe como proxy (§6.5) |
| Previsión de salud del niño/a (sin previsión, FONASA A/B/C/D, ISAPRE…) | no existe en E-3 | — | Eje Vulnerabilidad (§8); no decide elegibilidad |
| Puntaje final ficha / CSE (0–34) | no existe en E-3 | — | Eje Vulnerabilidad (§8), si el jardín lo tiene |
| Vivienda (campamento o toma, pieza en otra casa) | no existe en E-3 | BEN-020 (contexto) | Eje Urgencia (§8) |
| Madre en programa SernamEG Jefas de Hogar | no existe en E-3 | — | Eje Vulnerabilidad |
| Escolaridad del apoderado (incluye "no sabe leer ni escribir") | no existe en E-3 | — | **Formato del mensaje**: se traduce a `formato_preferido = VISUAL/AUDIO` (tarjeta con íconos, la tía lo lee en voz alta). La etiqueta original no se guarda en el contexto de IA |
| Nacionalidad | no existe en E-3 | — | Solo la tía elige idioma del mensaje (p. ej. creole). **No va al motor ni al LLM.** No se confunde con años de residencia (BEN-017 sigue como pregunta) |
| ¿Tiene una persona que lo cuide durante el día? | no existe en E-3 | — | Contexto para la tía |
| Correo, teléfono, quién retira, nombres, RUT | — | — | **Nunca** al LLM; contacto solo en el dispositivo de la tía para enviar WhatsApp |
| Enfermedades crónicas, alergias, NAE, lactancia, vacunas, esfínter | — | — | **Excluido.** No hay beneficio en el catálogo; datos de salud no salen del jardín |
| Derivación por Tribunal de Familia / Sename | — | — | **Excluido** totalmente de la herramienta |
| Jornada, extensión horaria, alimentación | — | — | Fuera de alcance |

#### 2.7.2 Objeto `contexto_familia` (lo que produce la capa 4)
```json
{
  "id_familia": "FAM-SIM-E3-00123",
  "fuente": "FICHA_SINTETICA | FICHA_DIGITAL",
  "composicion": [{"rol": "ADULTA_REFERENCIA", "edad": 31}, {"rol": "NINA_JARDIN", "edad": 4}, {"rol": "ABUELA", "edad": 72}],
  "rsh": {"tiene": true, "tramo": 40},
  "ingreso_per_capita_rango": "MENOS_110K",
  "senales_vulnerabilidad": {"fonasa_tramo": "A", "puntaje_cse": 22, "jefa_hogar_sernameg": true},
  "senales_urgencia": {"vivienda_precaria": false},
  "posible_discapacidad_nino": false,
  "formato_preferido": "TEXTO | VISUAL | AUDIO",
  "idioma_mensaje": "es",
  "inconsistencias": ["hermanos_6_14: ficha=2, dataset=1"],
  "no_informado": ["previsión", "embarazo"]
}
```

#### 2.7.3 Qué recibe el LLM
Solo: `composicion` (roles y edades), `rsh.tramo`, `ingreso_per_capita_rango`, `formato_preferido`, `idioma_mensaje` y la salida del motor. **Nunca**: nombres, RUT, folio RSH, teléfono, nacionalidad, diagnósticos, salud, derivaciones judiciales. El único filtro previo al envío al modelo vive en `ia/context_filter.py`, con un test que falla si aparece un campo prohibido.

> **Consentimiento:** la autorización de la ficha (Ley N.º 19.628) cubre estudios y transferencia a organismos públicos. Para el piloto real habría que agregar un consentimiento explícito para este uso; en la demo se muestra un aviso.

---

## 3. Alcance del MVP (3 días)

### MUST (sin esto no hay demo)
- **M1. Base de datos:** carga del dataset E-3 a DuckDB con vistas de cruce (`v_familia_beneficio`, `v_oportunidades`, `v_brechas`). *(Mecánica)*
- **M2. Motor de elegibilidad** que evalúe las 20 prestaciones para las 500 familias en la fecha de corte, con resultado `SI | NO | INDETERMINADO`, nivel `CONFIRMADO | PRELIMINAR` y traza por regla. *(Computación)*
- **M3. Estado de acceso** combinando elegibilidad + gestiones existentes (¿ya lo recibe?, ¿está postulando?, ¿le rechazaron?, ¿califica pero nunca lo pidió? ← la brecha). *(Mecánica, integrado por Computación)*
- **M3b. Ventana de contexto:** ficha sintética por familia + objeto `contexto_familia` + filtro hacia el LLM (§2.7). *(Mecánica calcula · Recursos Naturales define el mapeo · Computación implementa el filtro)*
- **M3c. Priorización de tres ejes** (Urgencia · Beneficio · Vulnerabilidad), con el "por qué está primero" visible (§8). *(Mecánica · pesos definidos por Recursos Naturales)*
- **M4. Panel del jardín:** lista de familias con semáforo y prioridad, % de familias informadas. *(Eléctrica)*
- **M5. Ficha de familia:** beneficios priorizados, explicación simple generada por IA, "qué falta" y "dónde ir", **guion de conversación** para la tía. *(Eléctrica implementa la vista · Computación integra Bedrock · Recursos Naturales revisa el lenguaje)*
- **M6. Registro de conversación** ("Conversado" + beneficios mencionados + siguiente paso + fecha) → alimenta KPI. *(Computación API · Eléctrica vista)*
- **M7. Panel KPI** (jardín / comuna / región): % informadas, % nuevas informadas, top brechas. *(Eléctrica, con API de Computación)*

### SHOULD
- **S1. Mensaje para la familia:** tarjeta imprimible (PDF/HTML) y texto para WhatsApp, generado por IA, en lenguaje simple.
- **S2. Familia nueva = ficha digital:** la tía llena en la matrícula los campos útiles de la ficha de Integra (§10) → pre-evaluación `PRELIMINAR` inmediata. Cubre el KPI #2.
- **S3. Asistente conversacional para la tía** ("¿Qué hay para una abuela de 70 años que vive con la familia?"), anclado al catálogo (RAG sobre catálogo + fuentes oficiales), que nunca inventa beneficios.
- **S4. Preguntas sugeridas** para resolver los `INDETERMINADO` (ver §2.4 punto 4).

### COULD (si sobra tiempo, suma mucho en el pitch)
- **C1. Mapeo territorial colaborativo:** la tía sube una **foto de un afiche** del CESFAM/municipalidad → la IA (multimodal) extrae un borrador de beneficio local (nombre, institución, requisitos, comuna, fechas, contacto) → queda "pendiente de revisión" → al aprobarse entra al catálogo de esa comuna. Esto responde literal a "estar constantemente mapeando beneficios en cada territorio" y replica lo que hizo la tía Ana.
- **C2. Alertas de ventana:** beneficios con ventana de postulación por cerrar o versión que cambia (p. ej. monto nuevo).
- **C3. Modo reunión de apoderados:** un beneficio explicado para todo el curso.
- **C4. Exportar** reporte del jardín.

### Fuera de alcance
Postular en nombre de la familia, integrarse con sistemas reales del Estado (RSH, IPS), datos reales de personas.

---

## 4. Arquitectura propuesta

Hackatón de AWS → usar **Amazon Bedrock (Claude)** para la capa generativa. Mantener una abstracción `LLMProvider` para poder correr local con otra API si Bedrock falla.

```
┌──────────────────────── Frontend (PWA, mobile-first) ────────────────────────┐
│ React + Vite + TypeScript + Tailwind                                         │
│ Vistas: Jardín · Familia · Conversación · Familia nueva · KPIs · Asistente    │
└───────────────────────────────▲──────────────────────────────────────────────┘
                                │ REST/JSON
┌───────────────────────────────┴──────────────────────────────────────────────┐
│ Backend Python 3.11 · FastAPI                                                │
│  ├─ loader/        carga CSV/JSON → DuckDB (o SQLite)                        │
│  ├─ engine/        motor de reglas determinista (sin LLM)                    │
│  ├─ access/        estado de acceso (elegibilidad + gestiones)               │
│  ├─ priority/      ranking de qué conversar con cada familia                 │
│  ├─ tracking/      registro de conversaciones (KPI)                          │
│  └─ api/           endpoints; entrega contexto mínimo a ia/                  │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ contrato interno
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ IA generativa (`ia/`) · única integración Bedrock                           │
│ filtro de contexto → prompts técnicos → explicaciones, guion y mensajes      │
└──────────────────────────────────────────────────────────────────────────────┘
Despliegue sugerido: backend en AWS App Runner o Lambda (Mangum); front en Amplify/S3+CloudFront;
persistencia de conversaciones en DynamoDB (o SQLite local para la demo).
```

### 4.1 Estructura de repo sugerida
```
/data/participantes_e3/            # zip descomprimido (no versionar si es pesado) · Mecánica
/backend                          # Computación lidera integración técnica
  /app
    main.py
    config.py                      # FECHA_EVALUACION y rutas
    /loader      load.py                                       # Mecánica
    /db          schema.sql  views.sql                         # Mecánica
    /engine      model.py  facts.py  operators.py  evaluator.py  roles.py   # Computación
    /access      access_state.py                               # Mecánica
    /context     ficha_sintetica.py  contexto_familia.py       # Mecánica
    /priority    ranking.py                                    # Mecánica
    /tracking    conversations.py                              # Computación
    /api         routes_jardin.py routes_familia.py routes_kpi.py routes_genai.py   # Computación
  /tests         test_operators.py test_evaluator.py test_access.py test_fixtures.py   # QA Mecánica; motor Computación
/ia                               # Computación · única integración Bedrock
  provider.py  context_filter.py  prompts.py  explain.py  script.py  message.py  assistant.py  ingest_flyer.py
/frontend                          # Eléctrica
  /src  pages/ components/ api/ mocks/ i18n/es.ts
/content                           # Recursos Naturales (artefactos futuros de producto, sin código)
  mapeo_ficha.csv                  # lo consumen Mecánica y Computación
  pesos_priorizacion.yaml          # lo consume priority/ranking.py
  preguntas.yaml                   # dato_faltante → pregunta humana
  beneficios_simple.yaml           # nombre simple, dónde ir, qué llevar, URL oficial
  prompts/*.md                     # Recursos Naturales redacta; Computación conecta
  demo/familias_demo.md  pitch.md
README.md
```

### 4.2 Endpoints mínimos
| Método | Ruta | Devuelve |
|---|---|---|
| GET | `/jardines` | lista de jardines (id, comuna, zona) |
| GET | `/jardines/{id}/familias` | familias del jardín con: prioridad, nº de oportunidades, estado "conversado", semáforo |
| GET | `/familias/{id}` | ficha: integrantes (sin RUT), RSH, resultados por beneficio, estado de acceso, traza |
| GET | `/familias/{id}/contexto` | `contexto_familia` (§2.7.2), sin campos prohibidos |
| GET | `/familias/{id}/oportunidades?orden=prioridad|urgencia|beneficio` | beneficios priorizados con los 3 ejes y el "por qué está primero" + qué falta + dónde ir + preguntas sugeridas |
| POST | `/familias/{id}/guion` | guion de conversación generado (IA) para la tía |
| POST | `/familias/{id}/mensaje` | texto WhatsApp + HTML imprimible para la familia (IA) |
| POST | `/familias/{id}/conversaciones` | registra conversación (beneficios mencionados, siguiente paso, fecha) |
| POST | `/familias/nueva/preevaluacion` | recibe cuestionario → evaluación PRELIMINAR |
| GET | `/kpi?nivel=jardin|comuna|region&id=...` | % informadas, % nuevas informadas, top brechas |
| POST | `/asistente` | respuesta anclada al catálogo (IA + RAG) |
| POST | `/catalogo/ingesta-afiche` | (COULD) imagen → borrador de beneficio |

---

## 5. El dataset E-3 (todo es sintético)

### 5.1 Qué trae
- **500 hogares**, **1.700 integrantes**, **50 jardines** sintéticos en **20 comunas** y **5 regiones** simuladas (10 jardines rurales, 40 urbanos).
- **20 prestaciones** (17 estatales simplificadas + 3 privadas sintéticas), **41 versiones** en el tiempo, **151 reglas** atómicas, **158 parámetros**.
- **2.383 gestiones** (postulaciones/asignaciones/derivaciones) con su historia de estados, y **2.343 pagos/entregas**.
- Fuentes oficiales de contexto (VUS, ChileAtiende, JUNAEB, Chile Crece Contigo, IPS) con URL → usarlas como "Más información" en la UI.

### 5.2 Convenciones
- CSV UTF-8, coma, con encabezado. Fechas ISO-8601, timestamps RFC 3339 (con offset -03/-04).
- Booleanos `true/false`. Vacío = nulo.
- **Intervalos semiabiertos `[desde, hasta)`**: vigente si `desde <= fecha < hasta`; `hasta` vacío = abierto.
- **Fecha de evaluación (snapshot):** `2026-10-13T23:59:59-03:00`. **Corte exclusivo:** `2026-10-14T00:00:00-03:00`. Todas las versiones actuales terminan en `2026-10-14`, por lo que se evalúa al **13-10-2026**. Dejar `FECHA_EVALUACION` configurable.
- `id_version_concesion` (en postulaciones) es la versión que gobierna la decisión, el término y los pagos de una gestión.

### 5.3 Tablas (carpeta `publico/`)
| Archivo | PK | Contenido / uso |
|---|---|---|
| `comunas.csv` | id_comuna | COM-001…020, región REG-SIM-01…05 |
| `jardines.csv` | id_jardin | 50 jardines, comuna, URBANA/RURAL |
| `familias.csv` | id_familia | folio RSH, `estado_rsh_corte` (VIGENTE 475 · SIN_REGISTRO 15 · REGISTRO_ANTECEDENTE_PENDIENTE 10), `tramo_rsh_corte` (40/50/60/70/80/90/100 o vacío), nº integrantes, comuna, **id_jardin** |
| `integrantes.csv` | id_integrante | parentesco (PERSONA_REFERENCIA, PAREJA, HIJO_HIJA, OTRO_PARIENTE), fecha nacimiento, sexo registral, `es_nino_jardin` |
| `rsh_historial.csv` | id_registro_rsh | estado, tramo, `subtramo_sintetico` (solo tramo 40), vigencia |
| `antecedentes_familia.csv` | id_antecedente | **hechos EAV del hogar** (ver 5.4) |
| `condiciones_integrante.csv` | id_condicion | **hechos EAV por persona** (ver 5.4) |
| `relaciones_integrantes.csv` | id_relacion | CARGA_DE (hijo→adulto), PROGENITOR_DE (adulto→hijo), acreditada, vigencia |
| `accesos_previos_hogar.csv` / `_causantes.csv` | id_acceso_previo | accesos históricos habilitantes (p. ej. SUF vigente en 2024) |
| `beneficios.csv` | id_beneficio | catálogo: nombre, institución, tipo de prestación, canal |
| `beneficios_versiones.csv` | id_version | vigencia, monto referencial, periodicidad, **modalidad_acceso** (POSTULACION / ASIGNACION_AUTOMATICA / DERIVACION), ventana, **requiere_accion_familia**, política de pérdida, cupo |
| `parametros_version.csv` | id_parametro | umbrales por versión (INT, DECIMAL, DATE, ENUM_LIST, RANGE_LIST, MAP, FORMULA, STRING) |
| `reglas_elegibilidad.csv` | (id_regla, id_version) | reglas atómicas (ver §6) |
| `fuentes.csv` + `*_fuentes.csv` | — | trazabilidad a fuente oficial (F001–F021) o supuesto sintético (F900) |
| `postulaciones.csv` | id_postulacion | gestiones reales (si no hay fila, no hubo gestión) |
| `postulaciones_estados.csv` | id_evento_estado | historia: POSTULADA, DERIVADA, EN_REVISION, APROBADA, VIGENTE, RECHAZADA (y FINALIZADA/DESISTIDA posibles) |
| `postulaciones_causantes.csv` | — | qué integrante es causante de cada gestión |
| `pagos_beneficios.csv` | id_pago | pagos/entregas por gestión |
| `dataset_e3.json` | — | lo mismo consolidado por familia (útil para el front o para depurar) |

### 5.4 Hechos EAV disponibles
Una fila = un hecho. El valor va en una sola de `valor_booleano | valor_numero | valor_texto | valor_fecha | valor_json`. Además: `estado_dato` (OBSERVADO; podría venir DECLARADO/DESCONOCIDO/NO_APLICA), `acreditada` (true/false), `vigencia_desde/hasta`, `id_contexto` (agrupa hechos de una misma matrícula, terapia, boleta, etc.).

**Hogar (`antecedentes_familia`):** INGRESO_HOGAR.MONTO · RESIDENCIA.COMUNA · INSEGURIDAD_ALIMENTARIA.INDICE · SUBSISTEMA_SSYO.PARTICIPACION · ACOMPANAMIENTO.ACEPTADO · COBERTURA_INCOMPATIBLE.ESTADO · BOLETA_AGUA.{MONTO, MORA_DIAS, COMUNA_CUENTA} · EVENTO_EMERGENCIA.TIPO · INFORME_DERIVACION.VIGENTE

**Persona (`condiciones_integrante`):** MATRICULA.{ESTADO, NIVEL, TIPO_ESTABLECIMIENTO, ADSCRITO_PAE} · CONTROL_SALUD.INFANTIL_RED_PUBLICA · ASISTENCIA.PORCENTAJE · DESEMPENO.PERCENTIL · PREVISION.{CATEGORIA, INGRESO_BRUTO} · DISCAPACIDAD.SEVERIDAD (50 casos) · TERAPIA.{ESTADO, DISTANCIA_KM, FECHA_DOCUMENTO} (50 casos)

### 5.5 Catálogo de las 20 prestaciones
| ID | Nombre | Modalidad | ¿Familia debe actuar? | Idea de requisitos (versión vigente) |
|---|---|---|---|---|
| BEN-001 | Subsidio Familiar (SUF) | POSTULACION | Sí | Tramo RSH ≤ 60; causante < 18 con antecedente por edad vigente |
| BEN-002 | SUF Automático | ASIGNACION_AUTOMATICA | No | Tramo ≤ 40; causante < 18 |
| BEN-003 | Subsidio Maternal | POSTULACION | Sí | Gestante ≥ semana 20; tramo ≤ 60; sin cobertura incompatible |
| BEN-004 | Aporte Familiar Permanente | ASIGNACION_AUTOMATICA | No | Tener SUF, Asignación Familiar o Subsistema SSyO activo al 31-12-2025 (OR de 3 grupos) |
| BEN-005 | Subsidio agua potable | POSTULACION | Sí | Gasto agua ≥ 5 % del ingreso; mora 0 días; cuenta en la comuna de residencia |
| BEN-006 | Subsidio discapacidad < 18 | POSTULACION | Sí | Mismo causante < 18 con discapacidad SEVERA vigente; tramo ≤ 60 |
| BEN-007 | Alimentación Escolar (PAE) | AUTOMATICA | No | Mismo estudiante 4–18 años, matrícula vigente, establecimiento adscrito |
| BEN-008 | Apoyo al Recién Nacido | DERIVACION | No | Recién nacido ≤ 90 días, parto en red pública |
| BEN-009 | Apoyo Desarrollo Biopsicosocial | DERIVACION | No | Gestante con control prenatal público **o** niño ≤ 60 meses con control infantil público |
| BEN-010 | Bono de Protección | AUTOMATICA | No | Subsistema SSyO vigente + acompañamiento aceptado |
| BEN-011 | Bono Base Familiar | AUTOMATICA | No | SSyO vigente + ingreso per cápita < $110.000 |
| BEN-012 | Bono Control Niño Sano | AUTOMATICA | No | SSyO vigente + niño < 6 con control ≤ 180 días |
| BEN-013 | Bono Asistencia Escolar | AUTOMATICA | No | SSyO + estudiante 6–18, matrícula, asistencia ≥ 85 % |
| BEN-014 | Bono Logro Escolar | AUTOMATICA | No | Estudiante < 24 en 5°B–4°M, subtramo ≤ 30, percentil ≤ 30 |
| BEN-015 | Útiles Escolares | AUTOMATICA | No | Matrícula vigente NT1–4°M en MUNICIPAL o SUBVENCIONADO_ADSCRITO |
| BEN-016 | Asignación Familiar | POSTULACION | Sí | Beneficiario con previsión compatible e ingreso bruto en tramo; causante acreditado como su carga |
| BEN-017 | Bono por Hijo | POSTULACION | Sí | Mujer ≥ 65, residencia ≥ 20 años (4 de los últimos 20), previsión compatible, ≥ 1 hijo/a |
| BEN-018 | Canasta Familiar (privado sint.) | DERIVACION | Sí | Inseguridad alimentaria ≥ 2, comuna cubierta, **cupo 75** con prioridad |
| BEN-019 | Traslado a Terapias (privado sint.) | POSTULACION | Sí | Mismo niño < 18 en terapia vigente, distancia ≥ 8 km, ingreso pc < $250.000, documento ≤ 90 días |
| BEN-020 | Emergencia Familiar (privado sint.) | DERIVACION | Sí | Evento crítico ≤ 60 días, comuna cubierta, informe vigente, sin pago previo en 180 días |

> Los valores exactos están en `parametros_version.csv`; **nunca hardcodear umbrales**: el motor debe leerlos por versión (BEN-016 tiene 3 versiones, el resto 2).

---

## 6. Motor de elegibilidad (especificación)

### 6.1 Selección de versión
Para cada `(familia, beneficio, fecha)`: usar la versión con `vigencia_desde <= fecha < vigencia_hasta`. Si no hay versión vigente → `NO_APLICA` (fuera de vigencia).

### 6.2 Estructura de una regla (`reglas_elegibilidad.csv`)
| Columna | Significado |
|---|---|
| `grupo_or` | Grupos alternativos. **Entre grupos: OR. Dentro de un grupo: AND.** |
| `orden` | orden de evaluación dentro del grupo (para la traza) |
| `cuantificador` | `HOUSEHOLD` (dato del hogar) · `EXISTS` (existe una entidad que cumpla) · `COUNT` (conteo de relaciones) |
| `binding_grupo` | Identificador de la entidad ligada (`HOGAR`, `CAUSANTE_1`, `ESTUDIANTE_1`, `GESTANTE_1`, `BENEFICIARIO_1`, `RECIEN_NACIDO_1`, `ACCESO_n`). **Todas las reglas con el mismo binding deben cumplirse por la MISMA entidad** (el "mismo niño o niña"). |
| `binding_padre` | binding del que depende (p. ej. CAUSANTE_1 depende de BENEFICIARIO_1 en Asignación Familiar) |
| `rol_causante` | NINGUNO, CAUSANTE, ESTUDIANTE, GESTANTE, RECIEN_NACIDO, BENEFICIARIO, ACCESO |
| `entidad_objetivo` | FAMILIA, INTEGRANTE, RELACION, ACCESO |
| `campo_dato` | campo lógico a resolver (ver 6.5) |
| `operador` | ver 6.3 |
| `valor_literal_tipo` + `valor_literal` | comparación contra literal (BOOLEAN, INT, STRING; listas como JSON) |
| `id_parametro_version` | comparación contra parámetro de la versión |
| `valor_binding_ref` | para `REF_EQ`: debe apuntar a la entidad de ese binding |
| `id_parametro_fecha_contexto` | para `ACTIVE_ON_DATE`: fecha a usar en vez de la fecha de evaluación (p. ej. corte 2025-12-31 del Aporte Familiar Permanente) |

### 6.3 Operadores
| Operador | Semántica |
|---|---|
| `EQ`, `LT`, `LTE`, `GT`, `GTE` | comparación escalar |
| `IN` | valor ∈ lista (ENUM_LIST del parámetro o literal JSON) |
| `BETWEEN` | valor dentro de RANGE_LIST, p. ej. `[4,19)` (respetar corchetes abiertos/cerrados) |
| `ACTIVE_ON_DATE` | existe un hecho de ese tipo con vigencia que cubre la fecha (de evaluación o la del parámetro de contexto) y con estado "activo" (MATRICULA=ACTIVA, SSYO=ACTIVA, TERAPIA=EN_CURSO, CONTROL=true, etc.) |
| `RANGE_LOOKUP` | el valor cae en algún tramo de `tramos_ingreso_monto` (`(0,360000]:26000;…`); cumple si cae en un tramo (y devuelve el monto del tramo para la estimación) |
| `REF_EQ` | existe relación `carga_acreditada_de` (CARGA_DE acreditada y vigente) desde la entidad del binding hacia la entidad de `valor_binding_ref` |
| `COUNT_REL_GTE` | nº de relaciones PROGENITOR_DE vigentes desde la entidad ≥ literal |
| `NOT_EXISTS_WITHIN` | no existe pago de BEN-020 en los últimos N días (N = parámetro `recurrencia_min_dias`) |

### 6.4 Lógica de tres valores y nivel de confianza
Cada regla atómica da `CUMPLE | NO_CUMPLE | INDETERMINADO`.
- **INDETERMINADO** cuando el dato no existe, es nulo o `estado_dato = DESCONOCIDO`.
- **AND (dentro de un grupo / binding):** algún NO → NO; si no, algún IND → IND; si no → SI.
- **EXISTS sobre candidatos:** algún candidato SI → SI; si no, algún IND → IND; si no → NO. Guardar **el candidato ganador** (id_integrante o id_acceso) para la explicación.
- **OR entre grupos:** algún SI → SI; si no, algún IND → IND; si no → NO.
- **Nivel** (solo cuando el resultado es SI): `CONFIRMADO` si todos los hechos que sustentan el SI tienen `acreditada=true` y `estado_dato=OBSERVADO`; si alguno es declarado / no acreditado → `PRELIMINAR`. `NO` e `INDETERMINADO` no llevan nivel.
- **Códigos de motivo** sugeridos: `CRITERIOS_CUMPLEN`, `CRITERIO_NO_CUMPLE`, `DATO_FALTANTE:<campo>`, `DATO_RSH_FALTANTE`, `EVIDENCIA_DECLARADA`.
- Un rechazo de una gestión **no cambia** el resultado de criterios (son cosas distintas: ver §7).

### 6.5 Resolución de `campo_dato` → datos
| campo_dato | Fuente / cálculo | Nota |
|---|---|---|
| `tramo_rsh` | `familias.tramo_rsh_corte` (o `rsh_historial` vigente) | vacío (25 familias sin RSH vigente) → IND → pregunta "¿tiene Registro Social de Hogares al día?" |
| `subtramo_sintetico` | `rsh_historial.subtramo_sintetico` | solo existe en tramo 40 |
| `edad`, `edad_meses`, `dias_desde_nacimiento` | `integrantes.fecha_nacimiento_sintetica` a la fecha de evaluación | años/meses cumplidos |
| `sexo_registral` | `integrantes.sexo_registral_sintetico` | |
| `antecedente_edad_vigente` | **no hay hecho en el dataset** | IND (o supuesto configurable `true` si hay matrícula/control vigente; documentar si se usa) |
| `semanas_gestacion`, `control_prenatal_red_publica`, `parto_red_publica` | **no hay datos de gestación ni parto** | sin candidatos → IND → pregunta "¿hay alguien embarazada / un bebé de menos de 3 meses?" |
| `cobertura_incompatible` | `antecedentes.COBERTURA_INCOMPATIBLE.ESTADO` (hogar) | aplicar a la gestante |
| `gasto_agua_pct_ingreso` | `BOLETA_AGUA.MONTO / INGRESO_HOGAR.MONTO × 100` | |
| `mora_dias` | `BOLETA_AGUA.MORA_DIAS` | |
| `comuna_cuenta_coincide_residencia` | `BOLETA_AGUA.COMUNA_CUENTA == RESIDENCIA.COMUNA` | |
| `ingreso_per_capita` | `INGRESO_HOGAR.MONTO / familias.numero_integrantes_corte` | |
| `indice_inseguridad` | `INSEGURIDAD_ALIMENTARIA.INDICE` | |
| `comuna_residencia` | `RESIDENCIA.COMUNA` vigente | |
| `subsistema_ssyo_vigencia` | `SUBSISTEMA_SSYO.PARTICIPACION = ACTIVA` vigente | |
| `acompanamiento_aceptado` | `ACOMPANAMIENTO.ACEPTADO` | |
| `tipo_evento` | `EVENTO_EMERGENCIA.TIPO` | |
| `dias_desde_evento` | **no hay fecha de evento explícita** | proxy: `vigencia_desde` o `fecha_observacion` del hecho; documentar supuesto |
| `informe_derivacion_vigente` | `INFORME_DERIVACION.VIGENTE` con vigencia | |
| `pago_previo_ben020` | `pagos_beneficios` ⨝ `postulaciones` (BEN-020) | ventana de N días |
| `matricula_vigencia`, `nivel`, `tipo_establecimiento`, `establecimiento_adscrito_pae` | `MATRICULA.*` (mismo `id_contexto`) | |
| `asistencia_pct` | `ASISTENCIA.PORCENTAJE` | |
| `percentil_desempeno` | `DESEMPENO.PERCENTIL` | |
| `control_infantil_red_publica` | `CONTROL_SALUD.INFANTIL_RED_PUBLICA` vigente | |
| `dias_desde_control` | **no hay fecha del control** | proxy: `fecha_observacion` del hecho; documentar |
| `discapacidad_severidad`, `discapacidad_vigencia` | `DISCAPACIDAD.SEVERIDAD` + vigencia | |
| `terapia_vigencia`, `distancia_terapia_km`, `documento_terapia_dias` | `TERAPIA.{ESTADO, DISTANCIA_KM, FECHA_DOCUMENTO}` (mismo contexto) | |
| `situacion_previsional`, `ingreso_bruto` | `PREVISION.{CATEGORIA, INGRESO_BRUTO}` | |
| `carga_acreditada_de` | `relaciones_integrantes` CARGA_DE acreditada vigente | |
| `hijos_activos` | `relaciones_integrantes` PROGENITOR_DE vigentes | |
| `residencia_total_anios`, `residencia_ultimos20_anios` | **no hay datos** | IND → pregunta "¿cuántos años lleva viviendo en Chile?" |
| ACCESO: `id_beneficio_o_programa`, `estado_acceso`, `vigencia` | `accesos_previos_hogar` ∪ gestiones (`postulaciones` + último estado + vigencia) | `SUBSISTEMA_SSYO` también puede salir del antecedente SSYO |

**Candidatos por rol** (configurable en `roles.py`):
- `CAUSANTE`: integrantes < 18 (o con relación CARGA_DE).
- `ESTUDIANTE`: integrantes con MATRICULA.
- `GESTANTE`: integrantes con hechos de gestación (hoy ninguno → IND con pregunta).
- `RECIEN_NACIDO`: integrantes con ≤ 90 días.
- `BENEFICIARIO`: adultos del hogar.

### 6.6 Salida del motor (por familia × beneficio)
```json
{
  "id_familia": "FAM-SIM-E3-00001",
  "id_beneficio": "BEN-001",
  "id_version": "V002",
  "fecha_evaluacion": "2026-10-13T23:59:59-03:00",
  "resultado": "SI | NO | INDETERMINADO",
  "nivel": "CONFIRMADO | PRELIMINAR | null",
  "motivos": ["CRITERIOS_CUMPLEN"],
  "datos_faltantes": ["tramo_rsh"],
  "entidad_ganadora": {"CAUSANTE_1": "PER-SIM-E3-000002"},
  "traza": [
    {"id_regla": "R00101", "campo": "tramo_rsh", "operador": "LTE",
     "esperado": 60, "observado": 50, "resultado": "CUMPLE", "id_hecho": "RSH-SIM-E3-000001"}
  ],
  "monto_estimado": 22000,
  "fuentes": ["F004", "F900"]
}
```
Precalcular las 10.000 evaluaciones (500 × 20) al arrancar: es rápido y simplifica el front.

### 6.7 Tests obligatorios
- Unitarios por operador (incluye intervalos abiertos/cerrados y nulos).
- Binding: una familia donde la condición A la cumple un niño y la B otro niño **no** debe dar SI.
- OR de BEN-004 (SUF **o** Asignación Familiar **o** SSyO).
- Cambio de versión: misma familia evaluada en 2025-06 y 2026-10 usa parámetros distintos.
- Familia sin RSH → `INDETERMINADO` (no `NO`) en BEN-001/002/003/006.
- Arquetipos de prueba (los ejemplos oficiales): familia "brecha" que califica a BEN-001 y no tiene gestión; familia "discapacidad" con el mismo niño en BEN-006 y BEN-019; familia de tramo alto → NO.

---

## 7. Estado de acceso (lo que la tía realmente necesita saber)

Combina el resultado del motor con las gestiones (`postulaciones` + último estado a la fecha):

| Estado de acceso | Regla | Qué significa para la conversación |
|---|---|---|
| `ASIGNADO` | SI + gestión con estado VIGENTE (o FINALIZADA tras VIGENTE) | "Ya lo recibe" → confirmar que lo está cobrando / usando |
| `GESTION_EN_CURSO` | SI + último estado POSTULADA / DERIVADA / EN_REVISION / APROBADA | "Está en trámite" → acompañar |
| `GESTION_RECHAZADA` | SI + último estado RECHAZADA / DESISTIDA | "Le dijeron que no, pero los requisitos parecen cumplirse" → orientar a reconsiderar / volver a consultar |
| `ELEGIBLE_SIN_ASIGNACION` ⭐ | SI CONFIRMADO + sin gestión | **LA BRECHA.** Prioridad máxima si `requiere_accion_familia = true` |
| `SIN_CUPO` | BEN-018 SI pero posición > cupo (75) | Informar que existe y que hay lista |
| `PENDIENTE_ANTECEDENTES` | SI PRELIMINAR | "Podría calificar si acredita X" |
| `INDETERMINADO` | IND | Convertir en pregunta para la tía |
| `NO_APLICA` | NO | No mencionar (o mencionar solo si la familia pregunta) |

**Prioridad BEN-018 (cupo 75):** ordenar elegibles por `indice_inseguridad` descendente, luego `ingreso_per_capita` ascendente, luego id.

---

## 8. Priorización: "3 cosas para conversar con esta familia"

La tía tiene que ver **por qué** un beneficio aparece primero. Por eso el puntaje se arma con tres ejes que también se muestran en pantalla como chips simples.

### 8.1 Los tres ejes (cada uno de 0 a 1)

**⏰ Urgencia (U)**: ¿se pierde algo si no se conversa esta semana? Se toma el **máximo** de estas señales:
| Señal | Valor |
|---|---|
| Emergencia familiar reciente (BEN-020, evento ≤ 60 días) | 1.0 |
| Recién nacido: quedan pocos días de los 90 de BEN-008 | 1 − días_restantes/90 |
| Documento de terapia por vencer (BEN-019, ≤ 90 días) | 1 − días_restantes/90 |
| Cupo limitado (BEN-018, cupo 75) y la familia está dentro del cupo | 0.8 |
| Inseguridad alimentaria ≥ 3 | 0.8 |
| Vivienda precaria según la ficha (campamento o toma) | 0.7 |
| Ventana de postulación cierra en ≤ 7 días / ≤ 30 días | 1.0 / 0.6 |
| Nada de lo anterior | 0.2 |

> ⚠️ **Ojo con el dataset:** casi todas las versiones vigentes tienen `ventana_acceso_hasta = 2026-10-14`, o sea, a la fecha de evaluación **todas** cerrarían mañana. Si la urgencia dependiera solo de la ventana, todo saldría "urgente" y el eje no serviría. Por eso la señal de ventana es configurable (`usar_ventana: false` por defecto en la demo) y la urgencia se basa sobre todo en la situación de la familia. Documentarlo en el README.

**💰 Beneficio para la familia (B)**: ¿cuánto le cambia la vida?
```
monto_anual = monto_referencial × periodicidad (MENSUAL ×12, ANUAL ×1, UNICA ×1)
             (o el monto del tramo devuelto por RANGE_LOOKUP en BEN-016)
B = min(1, (monto_anual / ingreso_anual_hogar) / 0.20)     # 20 % del ingreso = máximo
```
Beneficios en especie o servicio (PAE, Apoyo Biopsicosocial, Útiles, Recién Nacido) usan un **valor equivalente** de `content/pesos_priorizacion.yaml`. Si falta el ingreso, se usa la mediana del jardín y se marca `B_estimado=true`. En pantalla se muestra en pesos y en proporción: *"≈ $264.000 al año (casi 2 meses de su ingreso)"*.

**🏠 Vulnerabilidad del hogar (V)**: igual para todos los beneficios de una familia; sirve para ordenar la lista del jardín.
```
V = promedio ponderado de:
  tramo RSH (40 → 1.0, 50 → 0.85, 60 → 0.7, 70 → 0.4, 80 → 0.2, 90–100 → 0; sin RSH → 0.8)
  ingreso per cápita (< 110.000 → 1.0 … > 400.000 → 0)
  señales de la ficha: FONASA A o sin previsión, puntaje CSE alto, jefa de hogar SernamEG, niño/a con posible discapacidad
```
Las señales que no se conocen no suman ni restan (no se castiga a quien tiene menos datos).

### 8.2 Puntaje por (familia, beneficio)
```
puntaje = peso_estado × (1 + bonus_accion) × (w_U·U + w_B·B + w_V·V)
peso_estado: ELEGIBLE_SIN_ASIGNACION 10 · GESTION_RECHAZADA 7 · PENDIENTE_ANTECEDENTES 6
             · INDETERMINADO (resoluble con 1 pregunta) 5 · GESTION_EN_CURSO 2 · SIN_CUPO 1 · ASIGNADO 0
bonus_accion: +1 si requiere_accion_familia = true (si es automático, la familia no tiene que hacer nada)
pesos por defecto: w_U = 0.4 · w_B = 0.4 · w_V = 0.2
```
Todos los números viven en `content/pesos_priorizacion.yaml` (dueño funcional: Ingeniería en Recursos Naturales; implementación: Ingeniería Mecánica). `ranking.py` no tiene ningún número escrito a mano.

### 8.3 Prioridad de la familia en la lista del jardín
```
prioridad_familia = suma de los 3 mejores puntajes
                  + 3 × V
                  + bonus si NO ha sido conversada
                  + bonus si es familia nueva (≤ 30 días)
```

### 8.4 Cómo lo ve la tía
Cada tarjeta de beneficio muestra:
- Título simple + grupo de color:
  - 🟢 **"Puede pedirlo ya"** (ELEGIBLE_SIN_ASIGNACION con acción)
  - 🟡 **"Preguntar primero"** (INDETERMINADO / PENDIENTE)
  - 🔵 **"Ya lo tiene / está en trámite"**
- Chips: `⏰ Urgente` / `⏰ Esta semana` / (nada) · `💰 ≈ $264.000 al año` · `✋ Tiene que ir a pedirlo` o `📬 Le llega solo`.
- Una línea **"¿Por qué está primero?"** generada por plantilla (no por IA), p. ej. *"Califica, nunca lo ha pedido y equivale a casi 2 meses de ingreso."*
- Selector de orden: **Prioridad** (por defecto) · **Lo más urgente** · **Lo que más ayuda**.

En el detalle técnico se muestran U, B, V, peso_estado y el puntaje final, para que cualquiera pueda auditar el orden.

---

## 9. Capa de IA generativa (Bedrock · Claude)

### 9.1 Reglas para todos los prompts
- Entrada = **solo** el JSON de salida del motor + puntajes de §8 + `contexto_familia` filtrado (§2.7.3) + catálogo + fuentes. Nada de RUT ni nombres.
- Si `formato_preferido = VISUAL/AUDIO`, el mensaje usa frases aún más cortas, íconos y una versión para que la tía lo lea en voz alta.
- Ingeniería en Recursos Naturales define y revisa el contenido en `docs/producto/`; las plantillas técnicas viven en `ia/`, donde Ingeniería en Computación las conecta e inyecta los datos filtrados.
- Prohibido inventar beneficios, montos, requisitos o lugares que no estén en la entrada.
- Prohibido afirmar que la familia "tiene derecho" o "recibirá". Usar "podría", "vale la pena consultar".
- Español de Chile, trato de usted, frases ≤ 20 palabras, sin siglas sin explicar (RSH → "Registro Social de Hogares").
- Siempre cerrar con el aviso de orientación referencial.
- Temperatura baja (0.2–0.4). Salidas estructuradas en JSON cuando el front las consume.
- Cachear por (familia, beneficio, versión) para no regenerar.

### 9.2 Prompts a implementar
1. **Explicación simple por beneficio** → `{titulo_simple, por_que_podria_calificar, que_tiene_que_hacer, donde_ir, que_llevar, mas_info_url}`.
2. **Guion de conversación para la tía** (≤ 120 palabras): saludo cercano → 1 a 3 beneficios en orden de prioridad → preguntas para resolver INDETERMINADOS → siguiente paso concreto → aviso. Pensado para decirse en la puerta del jardín en 2 minutos.
3. **Mensaje para la familia**: versión WhatsApp (≤ 600 caracteres, con emojis moderados) y versión tarjeta imprimible (HTML simple, letra grande, iconos).
4. **Asistente de la tía** (RAG sobre `beneficios.csv` + versiones + parámetros + fuentes): responde preguntas abiertas; si la pregunta no está cubierta por el catálogo, lo dice y sugiere la fuente oficial (VUS / ChileAtiende).
5. **(COULD) Ingesta de afiche**: imagen → JSON `{nombre, institucion, requisitos_texto, comuna, fechas, contacto, tipo_prestacion}` con `confianza` por campo → queda en estado `PENDIENTE_REVISION`; no entra al motor hasta que alguien lo aprueba (y entonces se formaliza como reglas simples o queda como "beneficio informativo" sin evaluación automática).

### 9.3 Preguntas sugeridas (S4)
Mapear cada `datos_faltantes` a una pregunta humana. Ejemplos:
- `tramo_rsh` → "¿Tiene el Registro Social de Hogares al día?"
- `semanas_gestacion` → "¿Hay alguien embarazada en la familia?"
- `residencia_*` → "¿Cuántos años lleva viviendo en Chile?"
- `parto_red_publica` → "¿Hay un bebé de menos de 3 meses? ¿Nació en un hospital público?"
Cuando la tía responde, se guarda como hecho `estado_dato=DECLARADO, acreditada=false` y se reevalúa (→ `PRELIMINAR`).

---

## 10. Familia nueva (KPI #2): ficha digital

En vez de un cuestionario inventado, la tía llena una **versión digital y corta de la ficha de matrícula de Integra** (los mismos campos que ya conoce, §2.7.1). Todas las preguntas son opcionales y tienen "No sé".

Campos de la ficha que se piden: comuna · edad del niño/a · hermanos por tramo de edad (< 6, 6–14, 15–18) · ¿tiene Registro Social de Hogares? / tramo si lo sabe · ingreso aproximado del hogar (rangos) · ¿Subsistema Seguridades y Oportunidades? · ¿Chile Crece Contigo? · fecha del último control del cuaderno de salud · ¿algún niño/a con discapacidad o en terapia? · tipo de vivienda.

Preguntas que **no están en la ficha** pero el motor necesita (se agregan al final): ¿alguien embarazada? · ¿alguien mayor de 65? · ¿trabaja con contrato / tiene previsión? · ¿dificultad para pagar el agua o comprar alimentos?

→ crea familia con hechos `DECLARADO` → motor → resultados `PRELIMINAR` → priorización → guion inmediato. Marcar `es_nueva=true` y fecha de ingreso para el KPI.

---

## 11. Registro de conversaciones y KPIs

### 11.1 Modelo
```
conversacion {
  id, id_familia, id_jardin, fecha_hora,
  beneficios_mencionados: [id_beneficio],
  siguiente_paso: "IR_A_MUNICIPALIDAD" | "ACTUALIZAR_RSH" | "LLEVAR_DOCUMENTOS" | "NINGUNO" | texto,
  canal: "PRESENCIAL" | "REUNION_APODERADOS" | "WHATSAPP" | "IMPRESO",
  notas_breves (sin datos sensibles)
}
```

### 11.2 Indicadores
- **% familias informadas** = familias con ≥ 1 conversación / total de familias (por jardín, comuna, región, nacional).
- **% familias nuevas informadas** = nuevas con conversación ≤ 30 días desde el ingreso / nuevas.
- **Cobertura del set:** % de las oportunidades 🟢 que fueron mencionadas.
- **Brecha detectada:** nº de pares (familia, beneficio) en ELEGIBLE_SIN_ASIGNACION; top 5 beneficios con más brecha por comuna (esto le sirve a Integra para coordinar con municipios).
- **Monto potencial no cobrado** (estimado) por jardín → número potente para el pitch.
- (Futuro) conversión: brechas que pasan a gestión / asignado.

Para la demo: sembrar conversaciones simuladas en algunos jardines para que el panel tenga vida (y decirlo explícitamente en la demo).

---

## 12. Advertencias importantes sobre el dataset (leer antes de validar)

1. **Todo es sintético** y simplificado. Montos y requisitos no son los reales. Mostrar siempre el aviso.
2. **Hay campos que las reglas piden y que no existen en los datos públicos** (gestación, parto, antecedente por edad, años de residencia, fecha del control, fecha del evento). Tratarlos como `INDETERMINADO` + pregunta, o con supuestos explícitos y configurables. **Documentar cada supuesto** en `README.md`.
3. Los organizadores tienen un paquete interno con "respuestas esperadas" (`elegibilidad_esperada`, `asignacion_esperada`, `brechas_acceso`) que **no** se entrega. Revisando `generador.py`, esas respuestas se construyen por **arquetipo de familia y una regla sintética**, no siempre derivable de los hechos públicos (ej.: todas las familias tienen Subsistema SSyO activo y acompañamiento aceptado en los datos, pero las respuestas esperadas de Bono de Protección no son SI para todas). **No sobreajustar** para adivinar el arquetipo: el valor está en un motor transparente, trazable y explicable, y en el producto para la tía. Si los organizadores evalúan contra ese paquete, explicar las discrepancias con la traza.
4. Los arquetipos que el generador usa (útiles para elegir casos de demo): acceso completo (90), brecha (140), RSH faltante (50), no elegible (80), discapacidad (50), rechazo (40), cambio temporal (50). Las familias 91–230 son "brecha" (califican a SUF sin haberlo pedido) → **casos ideales para la demo**.
5. `generador.py` y `validador.py` solo regeneran/validan el dataset; no evalúan soluciones.

---

## 13. Privacidad, ética y seguridad
- Datos de niños/as y familias vulnerables: principio de mínimo dato, roles (tía ve solo su jardín; región ve agregados).
- No enviar identificadores (`identificador_mod11_simulado`, folio RSH) al LLM.
- Logs sin datos personales. Conversaciones: notas breves, sin diagnósticos ni datos de salud en texto libre (avisar en la UI).
- La herramienta orienta; la decisión es de la institución que otorga el beneficio.
- Accesibilidad: contraste alto, letra grande, botones grandes, funciona en celulares de gama baja.

---

## 14. UX / pantallas

1. **Inicio (Mi jardín):** barra de progreso "32 de 48 familias conversadas (67 %)", botón "Siguiente familia para conversar", lista con semáforo y chips (🟢 2 · 🟡 1).
2. **Ficha familia:** encabezado con composición del hogar en iconos (👩 adulta · 👧 niña 4 años · 👵 abuela 72), tramo RSH. Tres tarjetas "Para conversar hoy" (beneficio en lenguaje simple, chips ⏰ urgencia · 💰 beneficio · ✋/📬 acción, línea "¿Por qué está primero?", qué hacer, dónde, botón "Ver detalle técnico" que muestra la traza y los puntajes U/B/V). Selector de orden: Prioridad · Lo más urgente · Lo que más ayuda. Sección "Preguntar a la familia". Sección "Ya lo tiene / en trámite". Botones: **Ver guion** · **Enviar WhatsApp** · **Imprimir tarjeta** · **Marcar conversado**.
3. **Marcar conversado:** checklist de beneficios mencionados + siguiente paso + canal (3 toques).
4. **Familia nueva:** cuestionario paso a paso con "No sé".
5. **KPIs:** mapa o tabla por comuna, barras por jardín, top brechas, monto potencial.
6. **Asistente:** chat simple con respuestas citando la fuente.

Copy siempre en español simple. Nada de jerga técnica en la vista principal (los códigos `ELEGIBLE_SIN_ASIGNACION` etc. solo en el detalle técnico).

---

## 15. Plan de trabajo por rol (14 → 16 de octubre)

Roles detallados en §18. Hay **tres puntos de integración diarios**: 🔗 10:00 (acuerdos del día) · 🔗 14:00 (integrar lo que hay) · 🔗 19:00 (demo interna de 5 minutos, aunque sea fea).

| | **Computación · liderazgo, motor, API y Bedrock** | **Mecánica · datos, acceso, prioridad y QA** | **Eléctrica · PWA, integración y AWS** | **Recursos Naturales · producto y pitch (sin código)** |
|---|---|---|---|---|
| **Día 1 mañana** | Acordar arquitectura; FastAPI con endpoints mock y `/docs` | Loader DuckDB, `schema.sql`, vistas y perfil de calidad | Esqueleto PWA, rutas y consumo de mocks | Mapeo de ficha y primera propuesta de pesos de prioridad |
| **Día 1 tarde** | Operadores + evaluador; publicar stub de 5 familias; probar Bedrock | Características calculadas, casos QA y ranking U/B/V parametrizado | Lista del jardín con semáforo y barra de avance | Banco de preguntas y contenido simple de beneficios |
| **Día 1 noche** | Motor y API de oportunidades integrados | Carga de 10.000 pares, estado de acceso y pruebas de datos | Ficha familiar con tarjetas y chips U/B/V | Elegir 3 familias demo revisando la salida |
| **Día 2 mañana** | Filtro de contexto + test; explicación y guion con caché | Cupo BEN-018, ficha sintética, `contexto_familia` y ranking final | “Marcar conversado” en 3 toques + guion | Revisar 10 salidas reales, privacidad y lenguaje |
| **Día 2 tarde** | Mensaje, conversaciones, KPI y API real | Ficha digital → hechos DECLARADO → reevaluación; QA extremo a extremo | Panel KPI, ficha nueva y primer despliegue AWS | Prueba de usabilidad como “tía” en un celular real |
| **Día 2 noche** | Asistente RAG (S3) y plan B sin Bedrock | Sembrar conversaciones simuladas y documentar supuestos | Pulido móvil 360 px y modo poca conexión | Primer borrador de slides y guion de pitch |
| **Día 3** | Soporte de integración; congelar motor/API a las 12:00 | Pruebas finales y congelar datos a las 12:00 | Pulido y despliegue final; respaldo local | **Ensayo del pitch ×3**, video de respaldo y respuestas al jurado |

**Regla de oro:** nadie espera a nadie. Eléctrica trabaja contra mocks hasta que Computación publica el API real; Computación trabaja contra el contrato pequeño hasta que Mecánica entrega la carga completa. Recursos Naturales prueba cada integración visible.

---

## 16. Guion de demo (3–4 minutos)

1. **Problema** (30 s): Don Julio y la tía Ana; el boca a boca funciona, pero depende de que la tía sepa. Asimetría de información y costos de transacción.
2. **La tía abre la app** en el celular → su jardín → "Siguiente familia para conversar" (una familia del arquetipo brecha).
3. **Ficha:** "Puede pedirlo ya: Subsidio Familiar, ~$22.000 al mes por su hija" + por qué + dónde ir + chips "💰 casi 2 meses de ingreso al año" y "¿Por qué está primero?". "Preguntar: ¿alguien embarazada?". Mencionar que la herramienta usa la **ficha de matrícula que Integra ya tiene**: no le pide nada nuevo a la tía. Mostrar "Ver detalle técnico" (traza regla por regla) → confianza y transparencia.
4. **Guion en 2 minutos** generado por IA → la tía lo lee y conversa.
5. **Enviar WhatsApp / tarjeta** a la familia.
6. **Marcar conversado** → la barra del jardín sube → **panel nacional**: % informadas, brechas por comuna, monto potencial no cobrado.
7. **(Si está) foto de afiche del CESFAM** → nuevo beneficio local en el catálogo de la comuna: "así se mapea el territorio, con las mismas tías".
8. **Cierre:** KPI 100 % de familias informadas; replicable en CESFAM, municipios, ChileAtiende; escalable a 85 mil familias desde 1.200 jardines.

---

## 17. Definición de terminado (checklist con dueño)
- [ ] `make setup && make run` (o equivalente) levanta backend + front con los datos cargados. *(Computación + Eléctrica)*
- [ ] Base DuckDB con vistas de cruce; 10.000 evaluaciones precalculadas en < 30 s, con traza por regla. *(Mecánica carga · Computación motor)*
- [ ] Tests de operadores, bindings, OR, versiones, nulos e INDETERMINADO pasando. *(Computación; QA Mecánica)*
- [ ] `contexto_familia` generado para las 500 familias; test del filtro de campos prohibidos pasando. *(Mecánica genera · Computación filtra)*
- [ ] Priorización con U/B/V leyendo `pesos_priorizacion.yaml`, sin números en el código. *(Mecánica; Recursos Naturales valida pesos)*
- [ ] Ninguna decisión de elegibilidad pasa por el LLM. *(Computación)*
- [ ] Ficha de familia con top 3 + chips U/B/V + "¿por qué está primero?" + preguntas + guion + mensaje + marcar conversado. *(Eléctrica)*
- [ ] Panel KPI con % informadas y % nuevas informadas. *(Eléctrica + API de Computación)*
- [ ] Aviso "orientación referencial; no determina derechos" visible en ficha, guion y mensaje. *(Eléctrica; Recursos Naturales revisa)*
- [ ] Todos los textos visibles revisados en lenguaje simple. *(Recursos Naturales)*
- [ ] README con arquitectura, supuestos sobre datos faltantes (incluida la ventana de acceso, §8.1) y cómo correr. *(Computación + Mecánica; Recursos Naturales revisa que se entienda)*
- [ ] Funciona bien en un celular (viewport 360 px). *(Eléctrica; Recursos Naturales lo prueba)*
- [ ] Pitch ensayado en ≤ 4 minutos + video de respaldo. *(Recursos Naturales)*

---

## 18. Roles del equipo (4 integrantes)

El repositorio se organiza por componentes, no por carpetas personales. Ser dueño significa decidir y responder por un entregable; cualquier integrante puede ayudar, pero el dueño aprueba los cambios y coordina sus contratos.

### 💻 Ingeniería en Computación · liderazgo técnico, motor, backend/API y Bedrock

**Perfil:** integrante con mayor experiencia en programación, arquitectura y servicios.

**Dueño de:** liderazgo técnico y `backend/` —en especial futuras áreas `engine` y `api`—; también de `ia/`, ubicación única de la integración Bedrock y del filtro de contexto previo al envío.

**Responsable de:**
- Acordar arquitectura y contratos, integrar los componentes y destrabar decisiones técnicas.
- Implementar el motor de reglas (§6): versiones, operadores, bindings, OR/AND, tres valores, CONFIRMADO/PRELIMINAR y traza.
- Publicar endpoints mock desde la primera hora y luego el API real de §4.2.
- Integrar Bedrock para explicación, guion y mensaje, con filtro de contexto (§2.7.3), caché y temperatura baja.
- Garantizar que Bedrock nunca decida elegibilidad, acceso o prioridad y mantener un plan B por plantillas.
- Implementar registro de conversaciones y endpoints de KPI (§11).

**Entrega a otros:** contrato de evaluación determinista y API documentada, primero con un stub pequeño y luego con la carga completa.

### ⚙️ Ingeniería Mecánica · datos, características, acceso, prioridad y QA

**Perfil:** programación básica; trabajo guiado por contratos, SQL/Python acotado y pruebas reproducibles.

**Dueño de:** `data/`, `database/` y futuras áreas `loader`, `features`, `access`, `priority` y QA, aunque esas carpetas todavía no se creen.

**Responsable de:**
- Cargar los 23 CSV canónicos y crear el esquema y las vistas de cruce (`v_familia_beneficio`, `v_oportunidades`, `v_brechas`).
- Construir características calculadas sin confundir dato ausente, `false` y cero.
- Combinar la evaluación con gestiones para producir estado de acceso (§7), incluido el cupo de BEN-018.
- Generar ficha sintética y `contexto_familia` (§2.7) según el mapeo validado por Recursos Naturales.
- Implementar la priorización U/B/V (§8) a partir de parámetros revisados por Recursos Naturales.
- Preparar casos QA, verificar bindings, nulos, cambios de versión y consistencia extremo a extremo.

**Entrega a otros:** base tipada, características, estado de acceso, prioridad con explicación y evidencia de QA.

### 📱 Ingeniería Eléctrica · PWA, integración y despliegue AWS

**Perfil:** programación básica; trabajo apoyado en componentes visuales, mocks y contratos de API.

**Dueño de:** `frontend/`, integración visible y despliegue AWS.

**Responsable de:**
- Implementar las seis pantallas de §14 para celular de gama baja y poca conexión.
- Mostrar tarjetas con U/B/V, orden, “¿por qué está primero?”, preguntas y separación de beneficios personalizados y generales.
- Implementar “Marcar conversado” en tres toques, ficha de familia nueva y panel KPI.
- Consumir primero mocks y luego el API real sin duplicar reglas de elegibilidad o prioridad en el navegador.
- Mostrar el aviso referencial donde corresponda y mantener secretos fuera del frontend.
- Desplegar la PWA y servicios acordados en AWS, con respaldo local para la demo.

**Entrega a otros:** PWA integrada, URL o ejecución local reproducible y recorrido de demo.

### 🌿 Ingeniería en Recursos Naturales · producto, dominio y pitch (**sin programar**)

**Perfil:** conocimiento de contexto, comunicación y criterio. Trabaja en documentos, planillas y pruebas en celular; no necesita programar.

**Dueño de:** `docs/producto/`, lenguaje, privacidad, pruebas manuales, demo y pitch.

**Responsable de:**
- Revisar campo por campo la ficha de Integra y decidir qué entra al motor, qué es contexto y qué se excluye (§2.7.1).
- Definir y justificar señales y pesos de prioridad junto con Mecánica.
- Validar nombre simple, dónde consultar, qué llevar y fuente oficial de los 20 beneficios.
- Convertir cada dato faltante en una pregunta amable que la educadora pueda hacer.
- Escribir y revisar el contenido de prompts y salidas: sin promesas, trato de usted, frases cortas y sin siglas.
- Probar el flujo como “tía” en un celular, cronometrarlo y entregar hallazgos priorizados a Eléctrica.
- Revisar que ningún dato prohibido aparezca en pantallas, mensajes o prompts (§13 y §2.7.3).
- Elegir familias de demo, escribir el guion (§16), preparar slides, grabar respaldo y liderar ensayos.

**Entrega a otros:** criterios verificables de producto, textos aprobados, checklist de privacidad, resultados de pruebas manuales y pitch.

### Contratos entre roles (para trabajar en paralelo)

| Contrato | De → Para | Qué es | Plazo |
|---|---|---|---|
| C0 · Mapeo de ficha | Recursos Naturales → Mecánica y Computación | Campos de motor, contexto y exclusión | Día 1, 14:00 |
| C1 · Datos tipados | Mecánica → Computación | Base, características y significado de nulos | stub Día 1, 14:00 · completo Día 1 noche |
| C2 · Salida del motor | Computación → Mecánica y Eléctrica | JSON de §6.6, con traza y datos faltantes | stub de 5 familias primero |
| C3 · Acceso y prioridad | Mecánica → Computación y Eléctrica | Estado, U/B/V, puntaje y razón del orden | Día 2, 12:00 |
| C4 · API | Computación → Eléctrica | Endpoints de §4.2, primero con mocks | mocks Día 1, 11:00 |
| C5 · Producto y lenguaje | Recursos Naturales → Computación y Eléctrica | Preguntas, textos, privacidad y hallazgos | v1 Día 1 noche · final Día 2, 18:00 |
| C6 · PWA y despliegue | Eléctrica → equipo | Flujo integrado y plan de respaldo | Día 2, 18:00 |

### Forma de trabajo

- Una rama por tarea y componente, no por persona (por ejemplo, `datos/loader`, `backend/motor`, `front/ficha`, `docs/privacidad`). Se integra en cada punto diario acordado.
- Si algo bloquea a otra persona por más de 30 minutos, se avisa en el chat y se acuerda un mock que preserve el contrato.
- Computación y Mecánica hacen revisión cruzada de motor/datos; Eléctrica y Recursos Naturales revisan juntas la experiencia visible.
- Recursos Naturales conduce la demo interna de las 19:00: si el flujo no se puede mostrar, aún no está terminado.
- El detalle operativo y ownership por componente está en [Roles y responsabilidades](../equipo/ROLES_Y_RESPONSABILIDADES.md).
