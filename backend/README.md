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

El artefacto `e3.db` **no se versiona**: se genera en el build. El empaquetado
está en `backend/`: `Makefile` (target `data`), `make.ps1` (equivalente para
Windows) y `Dockerfile` + `.dockerignore` (en la raíz del repo).

### 1) Regenerar la base localmente (`make data`)

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

### 2) Construir la imagen con `e3.db` embebida

El contexto de build es la **raíz del repo** (el loader lee `../data/publico`),
así que se usa `-f backend/Dockerfile`:

```bash
# desde la raíz del repo:
docker build -f backend/Dockerfile -t e3-backend .

# smoke test: la base embebida debe tener 10.000 evaluaciones
docker run --rm e3-backend
# -> evaluaciones: 10000 / accesos: 10000 / vistas listas: ...
```

El `Dockerfile` corre el pipeline en build-time y verifica el conteo (falla el
build si `evaluaciones != 10000`), de modo que la imagen nunca sale con una base
incompleta.

- El backend (FastAPI, Rol 2) lee `e3.db` de **solo lectura** desde la imagen.
  El `CMD` por defecto es un placeholder (imprime el resumen de la base); Rol 2
  lo reemplaza por el server, p. ej.
  `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.
- Despliegue en App Runner / Lambda: publicar la imagen (ECR) y apuntar el
  servicio a ella. No hace falta un servicio de datos aparte: la base viaja
  dentro de la imagen.
- Nada de datos personales en logs ni en lo que viaje al LLM (lo garantiza
  `context_filter.py`, §2.7.3). El `.dockerignore` excluye `.env`, credenciales,
  `.venv`, cachés y las bases locales.
- Rutas y fecha configurables por entorno: `E3_DB_PATH`, `E3_FECHA_EVALUACION`
  (declaradas con default en el `Dockerfile`; Rol 2 las puede sobrescribir).

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
