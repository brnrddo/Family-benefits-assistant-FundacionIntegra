# Proyecto 3 · Apoyo Inteligente para Familias
## Especificación completa para el agente del IDE

> Hackatón de IA Generativa **AWS Breaking Barriers Chile 2026** · 14–16 de octubre de 2026 · Universidad de Chile (Beauchef 851).
> Desafío 3 de **Fundación Integra**: *"Conectando a familias con beneficios clave"*.
> Referente: Lissette Saavedra (Dirección Ejecutiva, Integra).
>
> Este documento es la fuente de verdad del proyecto. Léelo completo antes de escribir código. Los datos vienen en `participantes_e3.zip` (descomprimir en `data/`).

---

## 0. Resumen en una frase

Una herramienta **para la educadora / directora del jardín ("la tía")** que, a partir de los datos de cada familia, le dice **qué beneficios del Estado (y de organizaciones locales) podría obtener esa familia, por qué, qué le falta y dónde ir**, y le entrega un **guion simple para contárselo cara a cara** (boca a boca), más un mensaje que la familia se puede llevar. La tía registra que conversó con la familia y eso alimenta el KPI: **100 % de las familias informadas**.

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

---

## 3. Alcance del MVP (3 días)

### MUST (sin esto no hay demo)
- **M1. Carga de datos** del dataset E-3 a una base local (DuckDB o SQLite).
- **M2. Motor de elegibilidad** que evalúe las 20 prestaciones para las 500 familias en la fecha de corte, con resultado `SI | NO | INDETERMINADO`, nivel `CONFIRMADO | PRELIMINAR` y traza por regla.
- **M3. Estado de acceso** combinando elegibilidad + gestiones existentes (¿ya lo recibe?, ¿está postulando?, ¿le rechazaron?, ¿califica pero nunca lo pidió? ← la brecha).
- **M4. Panel del jardín:** lista de familias con semáforo y prioridad, % de familias informadas.
- **M5. Ficha de familia:** beneficios priorizados, explicación simple generada por IA, "qué falta" y "dónde ir", **guion de conversación** para la tía.
- **M6. Registro de conversación** ("Conversado" + beneficios mencionados + siguiente paso + fecha) → alimenta KPI.
- **M7. Panel KPI** (jardín / comuna / región): % informadas, % nuevas informadas, top brechas.

### SHOULD
- **S1. Mensaje para la familia:** tarjeta imprimible (PDF/HTML) y texto para WhatsApp, generado por IA, en lenguaje simple.
- **S2. Familia nueva (ingreso):** cuestionario corto (≤10 preguntas) que la tía llena con la familia en la matrícula → pre-evaluación `PRELIMINAR` inmediata. Cubre el KPI #2.
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
│  ├─ genai/         Bedrock: explicaciones, guion, mensaje, asistente, OCR    │
│  ├─ tracking/      registro de conversaciones (KPI)                          │
│  └─ api/           endpoints                                                 │
└──────────────────────────────────────────────────────────────────────────────┘
Despliegue sugerido: backend en AWS App Runner o Lambda (Mangum); front en Amplify/S3+CloudFront;
persistencia de conversaciones en DynamoDB (o SQLite local para la demo).
```

### 4.1 Estructura de repo sugerida
```
/data/participantes_e3/            # zip descomprimido (no versionar si es pesado)
/backend
  /app
    main.py
    config.py                      # FECHA_EVALUACION, rutas, proveedor LLM
    /loader      load.py
    /engine      model.py  facts.py  operators.py  evaluator.py  roles.py
    /access      access_state.py
    /priority    ranking.py
    /genai       provider.py  prompts.py  explain.py  script.py  message.py  assistant.py  ingest_flyer.py
    /tracking    conversations.py
    /api         routes_jardin.py routes_familia.py routes_kpi.py routes_genai.py
  /tests         test_operators.py test_evaluator.py test_access.py test_fixtures.py
/frontend
  /src  pages/ components/ api/ i18n/es.ts
README.md
```

### 4.2 Endpoints mínimos
| Método | Ruta | Devuelve |
|---|---|---|
| GET | `/jardines` | lista de jardines (id, comuna, zona) |
| GET | `/jardines/{id}/familias` | familias del jardín con: prioridad, nº de oportunidades, estado "conversado", semáforo |
| GET | `/familias/{id}` | ficha: integrantes (sin RUT), RSH, resultados por beneficio, estado de acceso, traza |
| GET | `/familias/{id}/oportunidades` | top N beneficios priorizados + qué falta + dónde ir + preguntas sugeridas |
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

Puntaje sugerido por (familia, beneficio), configurable:
```
puntaje = peso_estado × (1 + bonus_accion) × factor_monto × factor_urgencia
peso_estado: ELEGIBLE_SIN_ASIGNACION 10 · GESTION_RECHAZADA 7 · PENDIENTE_ANTECEDENTES 6
             · INDETERMINADO (resoluble con 1 pregunta) 5 · GESTION_EN_CURSO 2 · SIN_CUPO 1 · ASIGNADO 0
bonus_accion: +1 si requiere_accion_familia = true (si es automático, la familia no tiene que hacer nada)
factor_monto: log del monto anual estimado (o 1.0 para especie/servicio)
factor_urgencia: +50 % si la ventana de acceso cierra en < 30 días
```
**Prioridad de la familia en la lista del jardín:** suma de los 3 mejores puntajes + bonus si **no ha sido conversada** + bonus si es **familia nueva**.

Agrupar en lenguaje de la tía:
- 🟢 **"Puede pedirlo ya"** (ELEGIBLE_SIN_ASIGNACION con acción)
- 🟡 **"Preguntar primero"** (INDETERMINADO / PENDIENTE)
- 🔵 **"Ya lo tiene / está en trámite"**

---

## 9. Capa de IA generativa (Bedrock · Claude)

### 9.1 Reglas para todos los prompts
- Entrada = **solo** el JSON de salida del motor + catálogo + fuentes. Nada de RUT ni nombres.
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

## 10. Familia nueva (KPI #2)

Cuestionario de ingreso (≤ 10 preguntas, todas opcionales, con "no sé"):
comuna · nº de personas en el hogar · ¿tiene RSH? / tramo si lo sabe · edades de integrantes · ¿alguien embarazada? · ¿algún niño/a con discapacidad o en terapia? · ¿alguien mayor de 65? · ¿trabaja con contrato / tiene previsión? · ingreso aproximado del hogar (rangos) · ¿dificultad para comprar alimentos o pagar el agua?

→ crea familia con hechos `DECLARADO` → motor → resultados `PRELIMINAR` → guion inmediato. Marcar `es_nueva=true` y fecha de ingreso para el KPI.

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
2. **Ficha familia:** encabezado con composición del hogar en iconos (👩 adulta · 👧 niña 4 años · 👵 abuela 72), tramo RSH. Tres tarjetas "Para conversar hoy" (beneficio en lenguaje simple, por qué, qué hacer, dónde, botón "Ver detalle técnico" que muestra la traza). Sección "Preguntar a la familia". Sección "Ya lo tiene / en trámite". Botones: **Ver guion** · **Enviar WhatsApp** · **Imprimir tarjeta** · **Marcar conversado**.
3. **Marcar conversado:** checklist de beneficios mencionados + siguiente paso + canal (3 toques).
4. **Familia nueva:** cuestionario paso a paso con "No sé".
5. **KPIs:** mapa o tabla por comuna, barras por jardín, top brechas, monto potencial.
6. **Asistente:** chat simple con respuestas citando la fuente.

Copy siempre en español simple. Nada de jerga técnica en la vista principal (los códigos `ELEGIBLE_SIN_ASIGNACION` etc. solo en el detalle técnico).

---

## 15. Plan de trabajo (14 → 16 de octubre)

**Día 1 (hoy)**
- Repo + loader a DuckDB + modelos.
- Motor: operadores, bindings, OR/AND, tres valores, versiones. Tests con arquetipos.
- Estado de acceso + priorización. Endpoint `/familias/{id}/oportunidades`.
- Front: esqueleto PWA + lista del jardín.

**Día 2**
- Bedrock: explicación, guion, mensaje (con caché). Preguntas sugeridas.
- Ficha de familia completa + marcar conversado + KPIs.
- Familia nueva (cuestionario → PRELIMINAR).
- Deploy en AWS.

**Día 3 (mañana) → demo**
- Asistente RAG (y si alcanza, ingesta de afiche).
- Pulido UX móvil, datos sembrados para el panel, README con supuestos.
- Ensayo del pitch.

---

## 16. Guion de demo (3–4 minutos)

1. **Problema** (30 s): Don Julio y la tía Ana; el boca a boca funciona, pero depende de que la tía sepa. Asimetría de información y costos de transacción.
2. **La tía abre la app** en el celular → su jardín → "Siguiente familia para conversar" (una familia del arquetipo brecha).
3. **Ficha:** "Puede pedirlo ya: Subsidio Familiar, ~$22.000 al mes por su hija" + por qué + dónde ir. "Preguntar: ¿alguien embarazada?". Mostrar "Ver detalle técnico" (traza regla por regla) → confianza y transparencia.
4. **Guion en 2 minutos** generado por IA → la tía lo lee y conversa.
5. **Enviar WhatsApp / tarjeta** a la familia.
6. **Marcar conversado** → la barra del jardín sube → **panel nacional**: % informadas, brechas por comuna, monto potencial no cobrado.
7. **(Si está) foto de afiche del CESFAM** → nuevo beneficio local en el catálogo de la comuna: "así se mapea el territorio, con las mismas tías".
8. **Cierre:** KPI 100 % de familias informadas; replicable en CESFAM, municipios, ChileAtiende; escalable a 85 mil familias desde 1.200 jardines.

---

## 17. Definición de terminado (checklist para el agente)
- [ ] `make setup && make run` (o equivalente) levanta backend + front con los datos cargados.
- [ ] 10.000 evaluaciones precalculadas en < 30 s, con traza por regla.
- [ ] Tests de operadores, bindings, OR, versiones, nulos e INDETERMINADO pasando.
- [ ] Ninguna decisión de elegibilidad pasa por el LLM.
- [ ] Ficha de familia con top 3 + preguntas + guion + mensaje + marcar conversado.
- [ ] Panel KPI con % informadas y % nuevas informadas.
- [ ] Aviso "orientación referencial; no determina derechos" visible en ficha, guion y mensaje.
- [ ] README con arquitectura, supuestos sobre datos faltantes, y cómo correr.
- [ ] Funciona bien en un celular (viewport 360 px).
