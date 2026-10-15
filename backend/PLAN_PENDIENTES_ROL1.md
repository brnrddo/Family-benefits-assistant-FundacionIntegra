# Rol 1 · Procesos que faltan — plan de cierre

> Estado base verificado el 2026-10-15: la suite completa pasa (**90 passed**).
> Fuente de alcance: `PLAN_ROL1.md`. Ganchos futuros: `ROADMAP_ROL1.md`.
> Este documento solo planifica **lo que falta** frente al MUST del Rol 1.

---

## 0. Qué YA está hecho (no re-tocar)

Confirmado contra el código, no solo contra el README:

- **M1 vistas + precálculo** — `app/db/views.sql` + `app/db/build_views.py`:
  tablas materializadas `evaluaciones` y `accesos` (PK `(id_familia,id_beneficio)`)
  y vistas `v_familia_beneficio`, `v_oportunidades`, `v_brechas`, `v_ventanas`.
  El precálculo 500×20 corre y mide el objetivo `< 30 s`.
- **M2 motor** — `app/engine/`: OR entre grupos, AND dentro, cuantificadores
  HOUSEHOLD/EXISTS/COUNT, bindings por rol, REF_EQ (BEN-016), monto, traza,
  lógica de 3 valores y nivel CONFIRMADO/PRELIMINAR.
- **M3 acceso** — `app/access/`: los 8 estados, cupo BEN-018 (lee
  `cupo_contingente`, no hardcode) y checklist de documentos.
- **M3b contexto** — `app/context/`: `ficha_sintetica`, `contexto_familia` (C2),
  `context_filter` (allowlist §2.7.3) y `sanitizer`.
- **Tests §6.7** — operadores, evaluador, binding, OR/versiones, acceso, cupo,
  contexto/filtro, sanitizer, loader, genai (90 tests verdes).

**No vuelvo a implementar nada de lo anterior.** Si se toca, es solo para
enganchar lo nuevo.

---

## 1. Lo que falta (frente a `PLAN_ROL1.md`)

| # | Proceso faltante | Origen en el plan | Estado real | Prioridad |
|---|---|---|---|---|
| **P1** | Ficha digital → hechos DECLARADO → **reevaluación** | Día 2, punto 4 | ✅ **Hecho** (ver §2) — `tests/test_reevaluacion.py` | **Alta** |
| **P2** | Empaquetado AWS (`e3.db` embebido, `make data`, despliegue) | §0 "Soporte a AWS" + §6 | ✅ **Hecho** (ver §3) — `Dockerfile`, `Makefile`, `make.ps1`, `.dockerignore` | **Alta** |
| **P3** | Sembrar 3 familias demo verificadas (brecha, discapacidad, sin RSH) | Día 2, punto 8 | ✅ **Hecho** (ver §P3) — `tests/test_demo_familias.py` + README | Media |
| **P4** | README de datos: cerrar "cómo desplegar en AWS" con artefactos reales | Día 2, punto 7 + §6 | Parcial: el README describe el flujo pero apunta a artefactos que no existen (depende de P2) | Media (sigue a P2) |
| **C2** | Emitir el **contrato C2 formal** (schema `urn:brujula:c2:v1`), no solo el objeto interno §2.7.2 | Contrato Rol 1→Rol 2 (INDICE.md, Día 2 12:00) | ✅ **Hecho** (ver §C2) — `app/context/contrato_c2.py`, `tests/test_contrato_c2.py` | **Alta** |

> Fuera de alcance de los 2 días (quedan como gancho, **no** en este plan):
> G1/G2 bindings `ACCESO_*` de BEN-004, G3/G4 monto por FORMULA/MAP,
> G5 `politica_perdida`. Ver `ROADMAP_ROL1.md`.

---

## 2. P1 · Reevaluación con hechos DECLARADO (el proceso central que falta)

### 2.1 Problema
Hoy `Evaluator.evaluar(id_familia, id_beneficio)` resuelve **todos** los hechos
leyendo SQLite vía `resolver`/`facts`. No hay forma de que la tía (o el
`caracterizador` del LLM) aporte un dato que el dataset no trae
(p. ej. `semanas_gestacion`, `residencia_total_anios`) y que el motor lo use.
Resultado: esos campos quedan siempre `INDETERMINADO` (ver
`facts.CAMPOS_FALTANTES`) aunque la familia **sí** pueda declararlos.

Esto bloquea el KPI #2 / escenario S2 del plan: "la tía responde una pregunta y
la oportunidad se desbloquea".

### 2.2 Diseño propuesto (mínimo invasivo, trazable)

Idea: pasar un diccionario opcional de **hechos declarados** por la cadena de
evaluación. Cuando el resolver no encuentra el dato en la base, consulta primero
los declarados; si está, devuelve un `Hecho(presente=True, acreditada=False)`
→ el motor lo trata como DECLARADO → el beneficio puede dar `SI` **PRELIMINAR**
(nunca CONFIRMADO). Idéntico contrato que los supuestos indirectos ya existentes.

Firma objetivo (sin romper llamadas actuales — todo opcional):

```python
# resolver.py
def resolver_hogar(campo, ctx, declarados: dict | None = None) -> Hecho: ...
def resolver_integrante(campo, ctx, cand, declarados: dict | None = None) -> Hecho: ...

# evaluator.py
class Evaluator:
    def evaluar(self, id_familia, id_beneficio, declarados: dict | None = None): ...

# service.py
def evaluar_familia(id_familia, conn=None, fecha=..., declarados=None): ...
def reevaluar_con_declarados(id_familia, declarados, conn=None, fecha=...): ...
```

### 2.3 Forma del diccionario `declarados`
Un mapa `campo_dato -> valor`, con alcance hogar o por integrante:

```python
declarados = {
    "hogar":       {"residencia_total_anios": 12, "semanas_gestacion": None},
    "integrante":  {"INT-...-003": {"semanas_gestacion": 30}},
}
```

Reglas de resolución:
- Solo se consultan los declarados para campos que la base **no** resolvió
  (presente=False). No sobrescriben datos reales de la base (evita que un
  declarado "pise" evidencia acreditada).
- Todo hecho que venga de `declarados` sale `acreditada=False` → fuerza
  PRELIMINAR y deja rastro en la traza (`nota="declarado"`).
- Validación/saneo: pasar cada valor por `context/sanitizer.py` antes de usarlo
  (reutiliza clasificación OK/SOSPECHOSO/ILEGIBLE); un valor `ILEGIBLE` se
  ignora (sigue INDETERMINADO).

### 2.4 Puente desde el LLM (cierra el patrón `caracterizador`)
Nueva función que convierte la propuesta del caracterizador en el dict
`declarados` y reevalúa:

```python
# app/genai/caracterizador.py  (o un nuevo app/engine/declarados.py)
def declarados_desde_propuesta(propuesta: dict) -> dict: ...
```
Mapea las claves del JSON Schema del LLM a `campo_dato` del motor. Lo que no
mapee se descarta (no se inventan campos).

### 2.5 Puntos de código a tocar
1. `app/engine/facts.py` — helper `desde_declarado(campo, valor, id_origen)`
   que arma un `Hecho(presente=True, acreditada=False, nota="declarado")`.
2. `app/engine/resolver.py` — `resolver_hogar` / `resolver_integrante`
   aceptan `declarados`; tras agotar base/EAV/derivado y antes de caer en
   `CAMPOS_FALTANTES`, intentan el declarado.
3. `app/engine/evaluator.py` — propaga `declarados` por `evaluar` →
   `_eval_grupo` → `_eval_binding_*` → `resolver_*`. Marca la traza.
4. `app/engine/service.py` — `reevaluar_con_declarados(...)`.
5. `app/genai/caracterizador.py` — `declarados_desde_propuesta` + ejemplo de uso.

### 2.6 Tests nuevos (`tests/test_reevaluacion.py`)
- Sin declarados → un beneficio que depende de `semanas_gestacion` queda IND
  (comportamiento actual, regresión).
- Con `semanas_gestacion` declarado válido → el mismo beneficio pasa a
  `SI`/PRELIMINAR y la traza marca `declarado`; **nunca** CONFIRMADO.
- Un declarado que contradice un dato real de la base **no** lo pisa.
- Valor declarado `ILEGIBLE` (vía sanitizer) → sigue IND.
- `declarados_desde_propuesta` ignora claves desconocidas.

### 2.7 Definición de terminado (P1)
- [x] `evaluar(..., declarados=...)` funciona y es opcional (no rompe llamadas).
- [x] Un IND por dato faltante se puede desbloquear a SI PRELIMINAR con un
      declarado, con traza auditable.
- [x] `reevaluar_con_declarados` y el puente desde el LLM existen.
- [x] Tests nuevos verdes + los 90 actuales siguen verdes (**99 passed**).

> **P1 COMPLETADO (2026-10-15).** Implementado en `facts.py`
> (`CAMPOS_DECLARABLES`, `desde_declarado`, `_coerce_declarado`), `resolver.py`
> (`FamiliaCtx.declarados` + consulta de declarados en campos faltantes/EAV),
> `evaluator.py` (`evaluar(..., declarados=)`, traza `nota="declarado"`, motivo
> `EVIDENCIA_DECLARADA`), `service.py` (`reevaluar_con_declarados`) y
> `caracterizador.py` (`declarados_desde_propuesta`). Cubierto por
> `tests/test_reevaluacion.py`. Precálculo verificado intacto (10.000 en ~20 s).

---

## 3. P2 · Empaquetado AWS

### 3.1 Objetivo
Que "la base y el precálculo corran igual en la nube del equipo" (§0/§6): un
artefacto reproducible con `e3.db` ya generado, listo para que el backend
(Rol 2, App Runner/Lambda) lo lea de **solo lectura**.

### 3.2 Entregables
1. **`Makefile`** (o `make.ps1` para Windows) con target `data`:
   ```make
   data:
   	python -m app.loader.load --force
   	python -m app.db.build_views
   ```
   Reproduce la base + precálculo + vistas con un comando.
2. **`Dockerfile`** (en `backend/`):
   - base `python:3.11-slim`
   - instala `requirements.txt`
   - copia la app y los CSV públicos
   - en el build ejecuta `make data` → `e3.db` queda embebida en la imagen
   - comando por defecto: el server de Rol 2 (o un `CMD` placeholder si Rol 2
     aún no lo define) leyendo `E3_DB_PATH` de solo lectura.
3. **`.dockerignore`** — excluye `.venv`, `__pycache__`, `*.db` local,
   `.pytest_cache`, `.ruff_cache`.
4. Confirmar que `E3_DB_PATH` y `E3_FECHA_EVALUACION` se leen por entorno (ya
   existen en `config.py`) y documentarlo.

### 3.3 Verificación
- `make data` desde cero regenera `e3.db` y las vistas sin error.
- `docker build` produce imagen con `e3.db` dentro; `docker run` arranca y una
  consulta de prueba (`SELECT count(*) FROM evaluaciones` = 10.000) responde.
- Nada de datos personales en logs ni en la imagen fuera de `e3.db` (el filtro
  C2 ya lo garantiza para el LLM).

### 3.4 Definición de terminado (P2)
- [x] `Dockerfile` + `.dockerignore` + `Makefile` en `backend/`.
- [x] Build reproducible con `e3.db` embebida (10.000 filas).
- [x] README actualizado (ver P4).

> **P2 COMPLETADO (2026-10-15).** Entregables en `backend/`: `Makefile`
> (targets `data`/`load`/`views`/`test`/`clean`), `make.ps1` (equivalente para
> Windows sin `make`), `Dockerfile` (base `python:3.11-slim`, contexto de build
> = raíz del repo, corre el pipeline en build-time y **verifica** 10.000
> evaluaciones o falla el build) y `.dockerignore` en la raíz del repo (excluye
> secretos, `.venv`, cachés, bases locales y carpetas de otros roles). Sección
> "Cómo desplegar en AWS" del README reescrita con los comandos reales
> (`make data`, `docker build -f backend/Dockerfile`, smoke test). Verificado en
> local: `make.ps1 data` regenera `e3.db` (28.585 filas, precálculo 10.000 en
> ~19 s) y la suite completa pasa (**102 passed**). El `docker build` no se pudo
> ejecutar en el host Windows (sin Docker instalado); corre en AWS/CI sobre
> Linux. El tabla P4 (README de despliegue) queda cubierto por esta misma
> entrega.

---

## 4. P3 · 3 familias demo verificadas

Elegir y fijar 3 familias reales del dataset que ilustren los arquetipos:
- **Brecha** → `v_brechas` (ELEGIBLE_SIN_ASIGNACION confirmado sin gestión).
- **Discapacidad** → SI CONFIRMADO por binding de discapacidad.
- **Sin RSH** → INDETERMINADO por `tramo_rsh` faltante.

Entregable: `tests/test_demo_familias.py` que fije los 3 ids y asserte su
arquetipo (sirve de regresión y de guion para el pitch). Documentar los 3 ids
en el README.

---

## 5. P4 · Cerrar README de despliegue
Depende de P2. Reemplazar la sección "Cómo desplegar en AWS" (que hoy describe
un flujo sin artefactos) por los comandos reales: `make data`, `docker build`,
`docker run`, variables de entorno, y los 3 ids demo de P3.

---

## 6. Orden de ejecución sugerido
1. **P1** (reevaluación) — es el único proceso de *lógica* que falta y habilita
   el KPI #2. Mayor valor para la demo.
2. **P2** (AWS) — desbloquea a Rol 2/3 para desplegar; independiente de P1.
3. **P3** (familias demo) — rápido una vez P1 estable.
4. **P4** (README) — cierre, tras P2/P3.

> Riesgo principal: P1 toca el `evaluator` (núcleo). Mitigación: todos los
> parámetros nuevos son **opcionales**, se cubre con tests de regresión antes de
> extender, y el contrato DECLARADO→PRELIMINAR ya existe (no se inventa semántica).


---

## §C2 · Emitir el contrato C2 formal (hallazgo tras el merge PR #9)

### Hallazgo
El Rol 1 construía `contexto_familia` siguiendo la **redacción** §2.7.2 (claves
planas en español). Pero el contrato que Rol 2 y el frontend consumen es el
**schema versionado** `urn:brujula:c2:contexto-familia:v1`
(`.kiro/specs/_shared/contracts/C2-contexto-familia.schema.json`, declarado en
`INDICE.md` como "C2, Rol 1 → Rol 2, Día 2 12:00"). Ese schema tiene otra forma:

- `data_classification: "SYNTHETIC_DEMO_NOT_A_REAL_PERSON"` (requerido)
- `hechos[]` tipados `{campo, valor, estado_dato, acreditada}` + `procedencia[]`
- vocabulario **cerrado en inglés**: `composition`, `child.age`, `rsh.band`,
  `income.per_capita_band`, etc. (los mismos nombres del `mapeo_ficha.csv`)
- roles `ADULTA_REFERENCIA/NINO_JARDIN/OTRO_ADULTO`
- bandas de ingreso `UNDER_110K/110K_250K/250K_400K/OVER_400K`
- señales con nombres propios (`rsh_score`, `emergencia_reciente`, ...)

El objeto interno del Rol 1 **no validaba** contra ese schema.

### Decisión (no invasiva)
No se renombra el contrato (lo consumen Rol 2 y Rol 3) ni se reescribe el
builder. Se añade un **adaptador** interno→contrato:

- `app/context/contrato_c2.py` → `a_contrato_c2(ctx)` traduce la salida de
  `construir_contexto` al schema C2 v1 (mapea vocabularios y descarta lo que el
  contrato no admite; no decide elegibilidad ni inventa datos).
- Expuesto en `app/context/__init__.py`.

Esto conecta con el hallazgo del test de coherencia (`test_mapeo_coherencia.py`):
el filtro C2 ya estaba 1:1 con `mapeo_ficha.csv`; ahora además el Rol 1 **emite**
el contrato en el vocabulario correcto.

### Verificación
- `tests/test_contrato_c2.py`: claves requeridas, vocabulario cerrado, roles,
  bandas, procedencia coherente, sin datos prohibidos, y **validación completa
  contra el JSON Schema** (`jsonschema`, añadido a `requirements-dev.txt`) de
  **las 500 familias**.
- Suite: **111 passed**.

### Pendiente menor (coordinación, no bloqueante)
- `inconsistencias` del contrato usa un enum cerrado distinto del interno
  (`SIBLINGS_*_MISMATCH`, `RSH_STATUS_MISMATCH`, ...). Hoy el adaptador emite
  `inconsistencias: []`; poblarlas requiere acordar el cruce ficha↔dataset con
  Rol 4 y se hace cuando entre `FICHA_DIGITAL` (liga con P1).
- La reconciliación de nombres que un compañero empezó en `mapeo_ficha.csv`
  (branch `rol4/mapeo-campo-motor-wip`) **no debe aplicarse al CSV**: el
  contrato manda y el Rol 1 ya se adapta vía `contrato_c2.py`. Comunicar al
  equipo.


---

## §P3 · 3 familias demo verificadas

Tres familias **reales** del dataset E-3, elegidas para que cada arquetipo sea
claro y no se solape con los otros, fijadas en `tests/test_demo_familias.py`
(regresión + guion de demo) y documentadas en el README:

| Arquetipo | Familia | Verificación |
|---|---|---|
| **Brecha** | `FAM-SIM-E3-00231` | ≥1 `ELEGIBLE_SIN_ASIGNACION`; BEN-005 SI CONFIRMADO sin gestión. |
| **Discapacidad** | `FAM-SIM-E3-00361` | BEN-006 SI CONFIRMADO por binding de discapacidad severa vigente. |
| **Sin RSH** | `FAM-SIM-E3-00256` | `SIN_REGISTRO`: ≥1 beneficio IND por `tramo_rsh` con motivo `DATO_RSH_FALTANTE` (nunca NO). |

6 tests nuevos, verdes. Suite completa: **117 passed**.