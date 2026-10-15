# Backend — Apoyo Inteligente para Familias (Desafío 3 Integra)

API y lógica del servidor. Aquí vive el motor de elegibilidad, el estado de
acceso, la capa de IA generativa y las pantallas HTML servidas por FastAPI.

Stack: **Python 3.11+** · **FastAPI** · **SQLite** (biblioteca estándar para el loader).
Frontend: **HTML + CSS + JavaScript** servidos por FastAPI (sin framework ni bundler).

---

## M1 — Loader del dataset E-3 a SQLite

El loader carga los **23 CSV públicos** de `../data/publico/` en una base SQLite
(`backend/e3.db`), una tabla por archivo (nombre de tabla = nombre de archivo sin `.csv`).

### Enfoque "SQL directo"
- Todas las columnas se cargan como **TEXT**. Las fechas ISO (`2026-10-13`) se
  comparan correctamente como texto, lo que evita problemas de parsing. Donde una
  consulta necesite un número se usa `CAST` puntual.
- Los valores vacíos del CSV se cargan como **NULL** (no como cadena vacía).
- Lectura explícita en **UTF-8** (en Windows el default puede no serlo), de modo
  que los acentos (p. ej. "Automático") quedan correctos.
- El consolidado `dataset_e3.json` **no** se carga a una tabla; queda como archivo
  para el frontend si se necesita.

### Base de datos efímera
`backend/e3.db` **no se versiona** (está en `.gitignore` como `*.db`). Se regenera
desde los CSV cuando haga falta. Nunca la subas a git.

### Fecha de evaluación
Configurable en `app/config.py` (`FECHA_EVALUACION`, default `2026-10-13`; corte
exclusivo `2026-10-14`). Se puede sobrescribir con la variable de entorno
`E3_FECHA_EVALUACION`. También `E3_DB_PATH` para cambiar la ruta de la DB.

---

## Cómo generar la DB

Desde la carpeta `backend/`:

```bash
# (opcional) crear entorno virtual
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/mac: source .venv/bin/activate

# El loader M1 solo usa la stdlib; no requiere instalar nada.
python -m app.loader.load          # crea e3.db si no existe
python -m app.loader.load --force  # reconstruye desde cero
```

Imprime un resumen con los conteos por tabla. Conteos esperados: 500 familias,
1700 integrantes, 20 beneficios, 41 versiones, 151 reglas, etc.

## Cómo correr los tests

```bash
pip install -r requirements-dev.txt   # instala pytest
pytest                                # desde backend/
```

Los tests construyen una DB de prueba en un directorio temporal (no tocan
`e3.db`) y verifican: creación de las 23 tablas, conteos de filas, join
familia↔integrantes, encoding UTF-8, versión vigente de BEN-001 (= V002),
BEN-016 con 3 versiones, y que los vacíos quedan como NULL.

---

## M2 — Motor de elegibilidad (determinista)

Responde **"¿esta familia califica a este beneficio?"** con lógica de tres
valores (`SI` / `NO` / `INDETERMINADO`), nivel de confianza
(`CONFIRMADO` / `PRELIMINAR`), traza regla-por-regla y entidad ganadora.
**No decide estado de acceso** (eso es M3) ni usa IA.

Módulos en `app/engine/`:
- `model.py` — tipos (`Tri`, `Nivel`, `Hecho`, `TrazaRegla`, `ResultadoBeneficio`).
- `operators.py` — operadores atómicos presentes en las reglas: `EQ, LT, LTE,
  GT, GTE, IN, BETWEEN, ACTIVE_ON_DATE, RANGE_LOOKUP, COUNT_REL_GTE,
  NOT_EXISTS_WITHIN` (+ `REF_EQ` parcial).
- `facts.py` / `resolver.py` — mapa `campo_dato → origen` (directo / EAV /
  derivado / faltante) y resolución de hechos por hogar/integrante con vigencia
  semiabierta.
- `evaluator.py` — agregación OR entre grupos, AND dentro, cuantificadores
  HOUSEHOLD/EXISTS/COUNT, bindings por rol (misma persona), nivel, monto, traza.
- `service.py` — API de alto nivel: `evaluar_familia(id)` (bajo demanda) y
  `precalcular_todo()` (envoltorio 500×20, ~26 s).

### Uso rápido
```python
from app.engine.service import evaluar_familia
for r in evaluar_familia("FAM-SIM-E3-00100"):
    print(r.id_beneficio, r.resultado.value, r.nivel)
```

### Supuestos sobre datos ausentes (IMPORTANTE)
El dataset no trae algunos datos que ciertas reglas piden. Política:
- **Sin evidencia** → `INDETERMINADO` (se convierte en pregunta para la tía):
  `semanas_gestacion`, `parto_red_publica`, `control_prenatal_red_publica`,
  `residencia_total_anios`, `residencia_ultimos20_anios`, `dias_desde_evento`,
  `documento_terapia_dias`.
- **Con evidencia indirecta** → se asume como `DECLARADO` (no acreditado) y el
  beneficio puede dar `SI` con nivel **PRELIMINAR** (nunca CONFIRMADO). Banderas
  en `config.py`, reversibles por variable de entorno:
  - `SUPONER_ANTECEDENTE_EDAD` (default True): `antecedente_edad_vigente = true`
    si el causante es menor de 18. Habilita **SUF (BEN-001)** y SUF Automático.
  - `SUPONER_CONTROL_VIGENTE` (default True): `dias_desde_control` dentro de
    ventana si el niño tiene control de salud infantil vigente. Habilita el
    Bono Control Niño Sano (BEN-012).

El nivel `PRELIMINAR` es la señal visible de que hubo un supuesto. La traza
muestra siempre el detalle regla-por-regla para auditar la decisión.

### Reevaluación con hechos DECLARADO por la familia

Cuando una regla pide un dato que el dataset no trae (p. ej. `residencia_total_anios`,
`semanas_gestacion`), el beneficio queda `INDETERMINADO` → se convierte en una
pregunta para la tía. Si la familia **declara** ese dato (ficha digital), se
puede reevaluar inyectándolo: el motor lo trata como `DECLARADO` / no acreditado,
de modo que el beneficio puede pasar a `SI` pero siempre con nivel `PRELIMINAR`
(nunca `CONFIRMADO`). Un dato declarado **no** pisa un dato real de la base y, si
viene ilegible, se ignora (sigue INDETERMINADO).

```python
from app.engine.service import reevaluar_con_declarados

declarados = {
    "hogar":      {"dias_desde_evento": 10},
    "integrante": {"INT-...-001": {"residencia_total_anios": 30,
                                    "residencia_ultimos20_anios": 10}},
}
for r in reevaluar_con_declarados("FAM-SIM-E3-00100", declarados):
    print(r.id_beneficio, r.resultado.value, r.nivel)   # SI -> PRELIMINAR
```

Campos declarables: `app.engine.facts.CAMPOS_DECLARABLES` (subconjunto de los
campos ausentes, con su tipo). Puente desde la propuesta del LLM:
`app.genai.caracterizador.declarados_desde_propuesta(propuesta)` convierte una
propuesta estructurada (sección `hechos_declarados`) en el dict `declarados`,
dejando pasar solo campos declarables conocidos. La traza marca cada hecho
declarado con `nota="declarado"` y el resultado añade el motivo
`EVIDENCIA_DECLARADA` — auditable.

### Alcance de M2
Resuelve elegibilidad. Los beneficios que dependen del cruce con accesos
previos / gestiones (BEN-004 Aporte Familiar, BEN-016 Asignación Familiar) o de
datos genuinamente ausentes (BEN-008, 019, 020) quedan `INDETERMINADO` aquí; se
completan en M3 (estado de acceso).

---

## M3 — Estado de acceso + checklist de requisitos

Cruza la elegibilidad (M2) con las **gestiones reales** (`postulaciones` +
último estado + `pagos`) para responder qué pasa de verdad con la familia.
Módulos en `app/access/`.

### Estados (spec §7)
| Estado | Semáforo | Regla |
|---|---|---|
| `ASIGNADO` | azul | SI + gestión con último estado VIGENTE |
| `GESTION_EN_CURSO` | azul | SI + estado POSTULADA/EN_REVISION/DERIVADA/APROBADA |
| `GESTION_RECHAZADA` | verde | SI + estado RECHAZADA (cumple pero se lo negaron) |
| `ELEGIBLE_SIN_ASIGNACION` ⭐ | verde | SI **confirmado** sin gestión — **la brecha** |
| `PENDIENTE_ANTECEDENTES` | amarillo | SI **preliminar** sin gestión (decisión acordada) |
| `SIN_CUPO` | amarillo | elegible pero sobre el cupo (BEN-018; nota simple) |
| `INDETERMINADO` | amarillo | falta un dato → preguntar |
| `NO_APLICA` | gris | no cumple criterios |

Decisión aplicada: un `SI` **preliminar** sin gestión se marca
`PENDIENTE_ANTECEDENTES` (prima sobre la brecha). La brecha pura
(`ELEGIBLE_SIN_ASIGNACION`) la pueblan los `SI` confirmados sin gestión.

### Checklist de requisitos/documentos
Para beneficios con `SI`/`INDETERMINADO`, deriva qué necesita la familia:
modalidad de acceso, si requiere acción, canal (dónde ir), ventana, URL oficial
(de `fuentes`), y los **documentos** mapeados desde los `campo_dato` de las
reglas (p. ej. `tramo_rsh` → "Registro Social de Hogares al día").

```python
from app.access.service import evaluar_acceso_familia
for r in evaluar_acceso_familia("FAM-SIM-E3-00100"):
    print(r.id_beneficio, r.estado.value, r.semaforo)
```

---

## Perfil consolidado de familia

`app/profile/builder.py` arma un objeto único por familia (entrada para la ficha
y la IA) con seis secciones: **identidad** (hogar, jardín, comuna, región, zona),
**rsh** (estado, tramo, vigencia, `rsh_conocido`), **composición** (integrantes,
niños de jardín con nivel/matrícula, persona de referencia), **antecedentes**
(ingreso, residencia, condiciones por integrante con flag de acreditación),
**historial** (accesos previos + postulaciones con su último estado), y
**contexto_recomendacion** derivado:
- `beneficios_elegibles_determinables` — SI (incluye monto y estado de acceso)
- `beneficios_candidatos` — IND por un dato que la familia PODRÍA acreditar
- `beneficios_no_evaluables` — IND por un dato externo/clínico o de gestión
- `datos_faltantes` — todo lo que falta para evaluar más

```python
from app.profile.builder import construir_perfil
perfil = construir_perfil("FAM-SIM-E3-00100")
```

---

## M1 (cruce) — Vistas y precálculo persistido

`app/db/` materializa las **10.000 evaluaciones** (500 familias × 20 beneficios)
y crea las vistas de cruce que consumen Rol 2 (API/priorización) y Rol 3 (front).

### Qué genera
Dos tablas materializadas y tres vistas sobre ellas:

- Tablas: `evaluaciones` (salida del motor, C1, con traza en JSON) y `accesos`
  (estado de acceso M3 + checklist en JSON). PK `(id_familia, id_beneficio)`.
- Vistas:
  - `v_familia_beneficio` — una fila por (familia, beneficio): resultado, nivel,
    estado de acceso, semáforo, monto, modalidad, canal, ventana y fuente.
  - `v_oportunidades` — lo accionable para conversar (ELEGIBLE_SIN_ASIGNACION,
    GESTION_RECHAZADA, PENDIENTE_ANTECEDENTES, INDETERMINADO, SIN_CUPO).
  - `v_brechas` — la brecha estrella: `ELEGIBLE_SIN_ASIGNACION` (califica
    confirmado y nunca lo pidió).
  - `v_ventanas` — días hasta el cierre de inscripción por (familia, beneficio),
    insumo para el eje Urgencia del Rol 2 (§8.1). Trae `dias_hasta_cierre` y una
    bandera `ventana_discrimina` (ver caveat de la ventana más abajo). **No**
    pondera por sí sola; Rol 2 decide el peso.

### Cómo correr
```bash
# Desde backend/ (requiere e3.db ya generada por el loader):
python -m app.db.build_views          # usa e3.db (o E3_DB_PATH)
python -m app.db.build_views --db ... # otra ruta de DB
```
Imprime conteos y el tiempo. **Objetivo: < 30 s** (plan Rol 1). En la máquina de
referencia corre en ~18–19 s gracias a los índices que se crean antes del loop
(`INDICES_BASE` sobre postulaciones, estados, condiciones, antecedentes, etc.).
Conteos verificados contra `e3.db`: `v_oportunidades` ≈ 6.209, `v_brechas`
≈ 1.734, `SIN_CUPO` (BEN-018) = 396.

> Idempotente: se puede volver a ejecutar; recrea tablas y vistas desde cero.

---

## M3b — Ventana de contexto (ficha sintética + `contexto_familia` + filtro)

`app/context/` implementa la capa 4 de la spec (§2.7): el contexto humano de la
familia para decidir tono, formato y urgencia, **sin** decidir elegibilidad y
**sin** datos prohibidos.

- `ficha_sintetica.py` — ficha por familia derivada del dataset. Los campos que
  la ficha de Integra pide pero el dataset E-3 no trae quedan `NO_INFORMADO`
  (nunca se inventan).
- `contexto_familia.py` — objeto **C2** exacto (§2.7.2): `composicion`
  (roles+edades), `rsh`, `ingreso_per_capita_rango`, `senales_vulnerabilidad`,
  `senales_urgencia`, `posible_discapacidad_nino`, `formato_preferido`,
  `idioma_mensaje`, `inconsistencias`, `no_informado`.
- `context_filter.py` — filtro de privacidad hacia el LLM (§2.7.3) por
  **allowlist**: solo pasan `composicion` (rol+edad), `rsh.tramo`,
  `ingreso_per_capita_rango`, `formato_preferido`, `idioma_mensaje`. Un test
  falla si aparece cualquier campo prohibido (nombres, RUT, folio, teléfono,
  nacionalidad, diagnósticos, salud, derivaciones).

```python
from app.context import construir_contexto, filtrar_para_llm
ctx = construir_contexto("FAM-SIM-E3-00100")   # contrato C2 completo (para la tía)
solo_llm = filtrar_para_llm(ctx)               # lo único que puede ver el modelo
```

---

## API `/api/v1` (Rol 2) — arranque para el Rol 3

La capa API vive en `app/api/` y publica los **12 flujos C3** bajo `/api/v1`
como mocks sintéticos válidos (contrato C3 = fuente de verdad del OpenAPI).

### Arranque local (sin AWS ni DB)

```bash
# Desde backend/ (interprete py -3.11). 8000 es el puerto que usa el front
# (BRUJULA_DEV_API_PROXY y npm run check:api, DEC-034):
py -3.11 -m uvicorn app.api.app:app --port 8000 --reload
```

- **App:** `app.api.app:app` (FastAPI construida en `app/api/app.py`).
- **URL base:** `/api/v1`.
- **Healthcheck:** `GET /healthz` → `{"status": "ok"}`.
- **Docs / OpenAPI:** `GET /docs` (Swagger) y el contrato C3 servido tal cual en
  `GET /api/v1/openapi.yaml` y `GET /api/v1/openapi.json`.
- **Ejemplos:** `GET /api/v1/jardines`, `GET /api/v1/familias/FAM-SIM-0001`,
  `POST /api/v1/asistente`.

Por defecto **`E3_MOCK=1`**: todas las rutas responden mocks sintéticos
deterministas, **sin necesidad de DB (`e3.db`) ni de AWS/Bedrock**. El texto de
guion/mensaje/asistente lo genera el `TemplateProvider` (provider `PLANTILLA`),
nunca un LLM; una pregunta de elegibilidad individual al asistente devuelve
`REQUIRES_DETERMINISTIC_EVALUATION` sin invocar Bedrock. Guion y mensaje
validan los `benefit_ids` contra las oportunidades de la familia (propuesta
DEC-060): un ID ajeno responde 422 sin eco; un ASIGNADO se omite con el warning
`BENEFICIO_ASIGNADO_OMITIDO` (422 si todos lo son); GESTION_EN_CURSO,
GESTION_RECHAZADA y SIN_CUPO se nombran con la frase por estado del Rol 4
(instrucción 5 de `content/prompts`). El guion usa solo la primera frase de
cada descripción: 120 palabras como máximo (propuesta DEC-061).

### Integración del motor (`E3_MOCK=0`)

Con `E3_MOCK=0` la API sirve datos calculados por el motor del Rol 1 en vez de
mocks. Todo es local: sin AWS ni red.

```powershell
# Desde backend/: 1) DB desde los CSV, 2) precálculo 500×20 (~20 s, una vez)
py -3.11 -m app.loader.load --force
py -3.11 -m app.db.build_views
# 3) API en modo real (el snapshot se precalienta al arrancar, ~4–5 s)
$env:E3_MOCK='0'; py -3.11 -m uvicorn app.api.app:app --port 8000
```

- **Por qué `build_views`:** la API lee las tablas `evaluaciones` + `accesos`
  (salida exacta de `AccesoService`: motor, acceso y cupo BEN-018) y no evalúa
  en cada request. Con ellas arma una vez por proceso un snapshot en memoria;
  si regeneras la DB, el siguiente request lo toma. Un cursor de paginación
  emitido antes de regenerar la DB responde 422 (lleva una huella del build).
- **Endpoints reales:** `GET /jardines`, `GET /jardines/{id}/familias`,
  `GET /familias/{id}` (los 20 `benefit_results` con traza),
  `GET /familias/{id}/contexto` y `GET /familias/{id}/oportunidades`.
  `POST /conversaciones`, `/guion` y `/mensaje` validan contra los IDs reales
  (`FAM-SIM-E3-00001`…; los IDs mock como `FAM-SIM-0001` dan 404); `/guion` y
  `/mensaje`, además, contra las oportunidades reales de esa familia (DEC-060:
  ajeno → 422, ASIGNADO omitido con warning; guion de 120 palabras como
  máximo, DEC-061). Siguen
  sintéticos el KPI, la preevaluación, el asistente, la ingesta de afiche y el
  texto de guion/mensaje (`TemplateProvider`). `POST /antecedentes` con un ID
  real responde 503 retryable: reevaluar con hechos declarados exige cambiar el
  motor (propuesta DEC-052).
- **C4 = `content/` del Rol 4 (propuesta DEC-048):** en modo real, U/B/V, las
  medianas por jardín, el título, dónde ir, la cita oficial y las preguntas
  sugeridas salen de `content/manifest.yaml` 0.2.1 (adaptador
  `app/priority/content_c4.py`). Se valida fallando cerrado: schema C4, sha256
  de cada archivo (LF) y `content_bundle_hash`, las 6 clases y la suma U/B/V.
  `content/` sigue declarado no publicable (DEC-040) hasta API-T14 y la revisión
  humana. El mock `backend/fixtures/c4_mock/` queda para `E3_MOCK=1` y sus tests
  (`E3_CONTENT_MANIFEST` lo reapunta).
- **Orden (propuesta DEC-053):** primero lo que la familia puede pedir o le
  falta (`ELEGIBLE_SIN_ASIGNACION`, `PENDIENTE_ANTECEDENTES`, `INDETERMINADO`),
  luego `SIN_CUPO` y al final lo que ya tiene o ya postuló. Define `position`,
  `top_benefit_ids` y `top_opportunities`. La prioridad familiar no cambia.
- **Citas y montos (PREG-045/048, propuesta DEC-050 pendiente de confirmar con
  Rol 3 y Rol 4):** BEN-018/019/020 no tienen cita HTTPS en C4: aparecen en
  `benefit_results`, nunca como oportunidad. Sin monto anual (p. ej. BEN-010),
  B queda en 0 con `benefit_estimated=true`; hoy ese flag no distingue
  "mediana default" de "sin monto".
- **Degradación:** sin DB, sin precálculo, con DB ilegible, C4 inválido o una
  invariante rota, las rutas responden los mocks (nunca 500) y el log registra
  `runtime_degradado_a_mock: motivo=<CODIGO>` (`DB_AUSENTE`,
  `PRECALCULO_AUSENTE`, `DB_ILEGIBLE`, `C4_INVALIDO`, `INVARIANTE_MOTOR`).
  El fallo se registra una vez y no se reintenta hasta que cambie la DB o el
  manifest C4 (mtime o tamaño).
- **`why_first`:** frase fija por estado de acceso, con la forma "podría
  calificar… / vale la pena consultar…" (fuente funcional §2.4.2) y sin cifras.
- **Front:** con la API en `:8000`, desde `frontend/` usa `npm run dev:api` y
  `npm run check:api -- http://127.0.0.1:8000/api/v1`. En otro puerto, exporta
  `$env:BRUJULA_DEV_API_PROXY='http://127.0.0.1:<puerto>'`.
- `meta` mantiene `snapshot_id`/hashes constantes de demo (el front compara
  `snapshot_id`); los hashes reales quedan pendientes.

> Estado AWS: `NO_VERIFICADO`. No hay Cognito real; la autorización por scope es
> un stub de demo por header (`X-Demo-Scopes`): la API local no tiene
> autenticación y solo debe escuchar en loopback. Los logs de la app
> (`app.api`) registran solo `request_id`, método, ruta normalizada
> (`/api/v1/familias/{id}`), status y latencia: nunca cuerpos, prompts,
> preguntas, respuestas, identificadores completos ni tokens. El access log
> propio de uvicorn (`uvicorn.access`) pasa por un filtro de la app
> (`FiltroAccessLog`) en ambos modos: deja solo los segmentos fijos de las
> rutas, cambia el resto por `{id}` y descarta la query. No hace falta
> `--no-access-log`. Otros loggers (p. ej. errores de uvicorn) quedan fuera de
> ese filtro.

---

## Supuestos sobre datos ausentes (IMPORTANTE)

El dataset E-3 es sintético y no trae algunos datos que ciertas reglas piden.
Política general: **sin evidencia → `INDETERMINADO`** (se convierte en pregunta
para la tía), nunca `NO`. Con evidencia indirecta → `DECLARADO` y el beneficio
puede dar `SI` con nivel `PRELIMINAR` (nunca `CONFIRMADO`).

Campos que el dataset no trae y se tratan como INDETERMINADO (pregunta):
`semanas_gestacion`, `parto_red_publica`, `control_prenatal_red_publica`,
`residencia_total_anios`, `residencia_ultimos20_anios`, `dias_desde_evento`,
`documento_terapia_dias`.

Supuestos configurables (banderas en `config.py`, reversibles por entorno):
- `E3_SUPONER_ANTECEDENTE_EDAD` (default True): `antecedente_edad_vigente=true`
  si el causante es menor de 18 → habilita SUF (BEN-001) y SUF Automático
  (BEN-002) como PRELIMINAR.
- `E3_SUPONER_CONTROL_VIGENTE` (default True): `dias_desde_control` dentro de
  ventana si el niño tiene control de salud infantil vigente → habilita Bono
  Control Niño Sano (BEN-012) como PRELIMINAR.

### Ventana de acceso (§8.1) — advertencia de datos
Casi **todas** las versiones vigentes tienen `ventana_acceso_hasta = 2026-10-14`.
A la fecha de evaluación (2026-10-13) eso significa que todas "cerrarían mañana".
Si la urgencia dependiera solo de la ventana, **todo** saldría urgente y el eje
no discriminaría. Por eso:
- El Rol 1 expone los datos crudos de ventana (`ventana_desde`, `ventana_hasta`)
  en `v_familia_beneficio` y en la tabla `accesos`, sin ponderarlos.
- La señal de ventana en la priorización (Rol 2) debe venir **configurable y
  apagada por defecto** (`usar_ventana: false`); la urgencia se basa sobre todo
  en la situación de la familia (inseguridad, emergencia, cupo, recién nacido).

### Cupo BEN-018
BEN-018 (Canasta Familiar) tiene cupo contingente (75 en la versión vigente
V037). Los elegibles se ordenan por inseguridad alimentaria desc, ingreso per
cápita asc, id; los primeros 75 entran y el resto queda `SIN_CUPO`. El cupo se
lee de `beneficios_versiones.cupo_contingente` (no está hardcodeado).

---

## Cómo desplegar en AWS

Decisión de arquitectura: **se mantiene SQLite** (no DuckDB). El loader M1 ya
funciona en SQLite y migrar a mitad de hackatón es riesgo sin ganancia para la
demo; SQLite soporta las vistas de cruce que pide la spec. Desviación respecto
de la spec (que sugiere DuckDB), documentada aquí a propósito.

**Vía oficial: zip + Mangum en AWS Lambda** (dueño: Rol 2). El Rol 1 aporta dos
cosas al despliegue: (a) el pipeline reproducible `make data` que genera la
`e3.db` precalculada, y (b) las variables de entorno que la Lambda puede
sobrescribir. El artefacto `e3.db` **no se versiona**: se genera en el build.

> La vía basada en Docker (imagen con la base embebida) existe solo como
> **alternativa / plan B** en `docs/deploy-alternativo/` — p. ej. si el zip
> supera el límite de Lambda (250 MB descomprimido). **No es el camino oficial**
> y no debe desplegarse en paralelo a la vía zip.

### 1) Generar la base (`make data`)

Tanto la vía oficial (zip) como la alternativa (Docker) parten de la misma
`e3.db` generada por este pipeline:

```bash
# Linux/mac (desde backend/):
make data           # loader M1 + precálculo + vistas, en un comando

# Windows (desde backend/, sin `make`):
.\make.ps1 data
```

Equivale a:
```bash
python -m app.loader.load --force   # CSV públicos -> e3.db
python -m app.db.build_views        # 10.000 evaluaciones + vistas de cruce
```

### 2) Empaquetar (zip + Mangum) y desplegar

El empaquetado del artefacto Lambda y la definición de infraestructura son
responsabilidad del Rol 2 (ver su guía). El Rol 1 solo garantiza que:

- `make data` produce una `e3.db` con **10.000 evaluaciones** + las vistas de
  cruce, lista para servir de **solo lectura** desde la Lambda.
- La app lee su configuración por entorno, así que el despliegue puede
  sobrescribir sin tocar código:
  - `E3_DB_PATH` — ruta de la base dentro del paquete Lambda.
  - `E3_FECHA_EVALUACION` — fecha de corte de la evaluación.
  - `E3_LLM_PROVIDER=bedrock` + rol de IAM con `bedrock:InvokeModel` /
    `bedrock:Converse` para la capa GenAI (el stub local no necesita AWS).
- Nada de datos personales en logs ni en lo que viaje al LLM (lo garantiza
  `context_filter.py`, §2.7.3).

El adaptador ASGI (Mangum) y el handler de Lambda los define el Rol 2 al montar
el server FastAPI (`app/api/`).

### Alternativa Docker (plan B)

Documentada en `docs/deploy-alternativo/` (Dockerfile + README). Verificada de
punta a punta (Python 3.14.5-slim + uv, pipeline embebido, aserción de 10.000
evaluaciones en build-time, imagen ≈ 492 MB). Usar solo si la vía zip se bloquea.

---

## Tests del Rol 1

```bash
pip install -r requirements-dev.txt
pytest                      # suite completa
pytest tests/test_cupo.py   # un archivo
```

Cubren (spec §6.7 + §2.7):
- **Operadores** (`test_operators.py`): escalares, `IN`, `BETWEEN` con
  intervalos abiertos/cerrados, `RANGE_LOOKUP` con monto, nulos → INDETERMINADO.
- **Evaluador** (`test_evaluator.py`): versión vigente, SUF PRELIMINAR,
  discapacidad CONFIRMADO, sin RSH → INDETERMINADO, arquetipo brecha, traza.
- **Binding "mismo niño"** (`test_binding.py`): positivo (un niño cumple todo) y
  negativo (edad en un niño, discapacidad en un adulto → no da SI).
- **OR y versiones** (`test_or_versiones.py`): BEN-004 con 3 grupos OR; cambio
  de versión BEN-001 (V001 2025 vs V002 2026, montos distintos) y BEN-016 (3
  versiones).
- **Estado de acceso** (`test_access.py`): los 8 estados y el checklist.
- **Cupo BEN-018** (`test_cupo.py`): cupo = 75, exactamente 75 dentro, existe
  SIN_CUPO, dentro-de-cupo no es SIN_CUPO.
- **Contexto C2 y filtro** (`test_context_filter.py`): forma del contrato,
  NO_INFORMADO, el filtro solo deja campos permitidos, **falla si hay fuga**,
  no muta el original, detecta una fuga inyectada, 500 familias sin fugas.
- **Reevaluación con DECLARADO** (`test_reevaluacion.py`): un IND por dato
  ausente se desbloquea a SI PRELIMINAR al declarar el dato; ilegible se ignora;
  no pisa dato real; puente `declarados_desde_propuesta`.
- **Contrato C2 formal** (`test_contrato_c2.py`): `a_contrato_c2` valida contra
  el JSON Schema `urn:brujula:c2:v1` para las 500 familias (requiere
  `jsonschema`).
- **Coherencia filtro↔mapeo** (`test_mapeo_coherencia.py`): lo que el filtro
  deja pasar al LLM == filas `CONTEXTO_MINIMO_LLM` de `content/mapeo_ficha.csv`.
- **Familias demo** (`test_demo_familias.py`): fija los 3 arquetipos del pitch
  (ver abajo).

---

## 3 familias demo (arquetipos del pitch)

Tres familias reales del dataset, verificadas y fijadas en
`tests/test_demo_familias.py` para la demo y como regresión:

| Arquetipo | Familia | Qué muestra |
|---|---|---|
| **Brecha** | `FAM-SIM-E3-00231` | Varios `ELEGIBLE_SIN_ASIGNACION` — califica confirmado y nunca lo pidió (BEN-005 SI CONFIRMADO sin gestión). |
| **Discapacidad** | `FAM-SIM-E3-00361` | BEN-006 (subsidio discapacidad <18) SI CONFIRMADO por binding de discapacidad severa vigente. |
| **Sin RSH** | `FAM-SIM-E3-00256` | `SIN_REGISTRO`: los beneficios que piden tramo RSH quedan INDETERMINADO (pregunta para la tía), nunca NO. |

---

## Resiliencia a datos mal ingresados (`app/context/sanitizer.py`)

La caracterización de la familia no se rompe ni engaña con datos sucios. Cada
dato clave (fecha/edad, parentesco, sexo, tramo RSH, ingreso, severidad de
discapacidad) pasa por un saneador que:

- **Normaliza** lo inequívoco: `"300.000"`→`300000`, `"hijo"`→`HIJO_HIJA`,
  `"Femenino"`→`F`, `"2015/01/01"`→`2015-01-01`.
- **Marca** lo fuera de rango como `SOSPECHOSO` (p. ej. tramo 45, edad 200).
- **Degrada** lo ilegible a ausente (`ILEGIBLE`) sin inventar valores.
- **Registra** todo lo dudoso en `contexto_familia.inconsistencias` y un
  resumen en `contexto_familia.calidad_datos` (insumo para un KPI de calidad
  de datos). Esto conecta con §2.4.4: lo que no se sabe se convierte en pregunta.

Clasificación por dato: `OK` / `NORMALIZADO` / `SOSPECHOSO` / `ILEGIBLE` / `AUSENTE`.

---

## Base de IA generativa para el Rol 2 (`app/genai/`)

Rol 1 deja los **contratos y un proveedor stub**; Rol 2 implementa Bedrock.

- `provider.py` — `LLMProvider` (interfaz), `StubProvider` (local, sin AWS, para
  tests y plan B §4) y `BedrockProvider` (esqueleto con la guía de la llamada
  Converse de Amazon Bedrock para que Rol 2 lo rellene). Fábrica `get_provider()`
  por entorno (`E3_LLM_PROVIDER=stub|bedrock`).
- `caracterizador.py` — patrón de uso: toma el `contexto_familia` **ya filtrado**
  (`context_filter.filtrar_para_llm`) + texto libre de la tía y pide al modelo
  una caracterización **estructurada** (JSON Schema). La propuesta entra como
  `DECLARADO`/no acreditada → el motor la trataría como PRELIMINAR, nunca
  CONFIRMADO. **El LLM no decide elegibilidad** (spec §2.4.1).

Dependencia: `boto3` (en `requirements.txt`), importado de forma perezosa solo
cuando se usa el `BedrockProvider` real; el stub no lo necesita.

### Pasos para el Rol 2 (AWS Bedrock)
1. Habilitar acceso al modelo Claude (p. ej. un Haiku, rápido/barato) en la
   consola de Bedrock, región `us-east-1` o `us-west-2` (no hay región Chile).
2. Rellenar `BedrockProvider.generar` con `boto3.client("bedrock-runtime").converse(...)`
   y Structured Outputs / Tool Use para forzar el JSON Schema.
3. Rol de IAM mínimo: `bedrock:InvokeModel`, `bedrock:Converse` sobre ese modelo.
4. Dejar el fallback al `StubProvider` si Bedrock falla (plan B §4).

---

## Objetivo y límites del componente (encuadre del equipo)

Implementar el motor de reglas determinista y trazable, la API y el registro de conversaciones/KPI. La integración con Bedrock pertenece exclusivamente a `ia/`.

- **Dueño:** Ingeniería en Computación.
- **Colaboradores:** Ingeniería Mecánica entrega loader, características, acceso, prioridad y QA; Ingeniería Eléctrica consume la API.

### Entradas y salidas

**Entradas:** base derivada de los CSV canónicos, catálogo y reglas, características calculadas, estados de acceso, prioridad y textos validados.

**Salidas:** evaluaciones `SI | NO | INDETERMINADO` con traza, endpoints JSON, datos faltantes, preguntas, oportunidades ordenadas, métricas agregadas y contexto mínimo para la capa de redacción.

### Dependencias y límites

Depende del contrato de `data/` y `database/`; publica un contrato estable para `frontend/` y entrega a `ia/` el contexto mínimo acordado. `ia/` aplica el filtro canónico antes de cualquier envío a Bedrock.

No colocar aquí componentes visuales, CSV canónicos, credenciales, dumps, adaptadores de Bedrock, prompts, otro filtro previo al modelo ni lógica que permita a un LLM decidir elegibilidad o prioridad.

Contexto: [especificación](../docs/especificacion/PROYECTO_3_ESPECIFICACION_v2.md), [roles](../docs/equipo/ROLES_Y_RESPONSABILIDADES.md) y [estructura](../docs/arquitectura/ESTRUCTURA_REPOSITORIO.md).
