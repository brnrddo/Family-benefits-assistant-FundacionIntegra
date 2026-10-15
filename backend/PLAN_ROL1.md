# Rol 1 · Datos y motor de elegibilidad — Plan de specs y alcances (2 días)

> Fuente de verdad: `hola/PROYECTO_3_ESPECIFICACION_v2.md`.
> Este documento acota **solo el Rol 1** y **solo lo necesario para la demo de 2 días**.
> Dueño: Rol 1. Entrega a otros: contrato **C1** (salida del motor, §6.6) y **C2** (`contexto_familia`, §2.7.2).

---

## 0. Alcance (qué entra y qué NO)

**Entra (MUST del Rol 1):**
- M1 Base de datos + vistas de cruce (`v_familia_beneficio`, `v_oportunidades`, `v_brechas`).
- M2 Motor de elegibilidad determinista con traza (ya existe; se cierra y testea).
- M3 Estado de acceso + cupo BEN-018 (ya existe; se cierra y testea).
- M3b Ventana de contexto: ficha sintética + `contexto_familia` + filtro de campos prohibidos.
- Precálculo de las 10.000 evaluaciones (500×20) en < 30 s.
- Tests obligatorios §6.7 + parte de datos del README.
- Soporte a AWS: la base y el precálculo deben correr igual en la nube del equipo.

**NO entra (de otros roles o fuera de los 2 días):**
- Priorización U/B/V (`priority/ranking.py`) → Rol 2.
- API FastAPI, Bedrock, caché, KPIs → Rol 2.
- Frontend → Rol 3.
- Contenido/YAML/prompts → Rol 4.
- COULD: ingesta de afiche, alertas de ventana, modo reunión.

---

## 1. Decisiones tomadas (revisables)

| Tema | Decisión | Razón |
|---|---|---|
| **DuckDB vs SQLite** | **Mantener SQLite** (lo ya construido). Crear las vistas de cruce igual. | El loader M1 ya funciona en SQLite; migrar a DuckDB a mitad de hackatón es riesgo sin ganancia para la demo. SQLite soporta las vistas que pide §2.6. **Desviación documentada en README.** |
| **`profile/` vs `context/`** | Añadir `app/context/` con el **contrato C2 exacto** (§2.7.2). Reusar lo útil de `profile/builder.py`. | C2 es lo que consume Rol 2; debe cumplirse al pie de la letra, incluido el filtro de campos prohibidos. |
| **AWS** | Base + precálculo empaquetados para correr en la nube del equipo (App Runner / Lambda). SQLite viaja como artefacto; sin servicio de datos aparte. | La spec deja la base local para la demo pero pide misma nube. SQLite en el contenedor es lo más simple y portable. |

> Si el equipo exige DuckDB literal, es un bloque aparte de medio día (reescribir loader + revalidar). No está en este plan por riesgo.

---

## 2. Estado actual (lo ya hecho)

- ✅ **M1 loader** → `app/loader/load.py` (23 CSV a SQLite `e3.db`, UTF-8, NULL en vacíos).
- ✅ **M2 motor** → `app/engine/{model,operators,facts,resolver,evaluator,service}.py`.
- ✅ **M3 acceso** → `app/access/{model,service}.py` (8 estados, cupo BEN-018, checklist).
- ✅ **Perfil** → `app/profile/builder.py` (base para `contexto_familia`).
- ⚠️ Falta: vistas de cruce nombradas, `app/context/` con C2 + filtro, precálculo persistido, tests §6.7 completos, README de supuestos, empaquetado AWS.

---

## 3. Entregables por día

### Día 1
1. **Vistas de cruce** (`app/db/views.sql` + `app/db/build_views.py`):
   - `v_familia_beneficio`: una fila por (familia, beneficio) con resultado, nivel, estado de acceso.
   - `v_oportunidades`: subconjunto accionable (SI/IND con acción) por familia.
   - `v_brechas`: pares ELEGIBLE_SIN_ASIGNACION (la brecha).
2. **`app/context/`**:
   - `ficha_sintetica.py`: ficha por familia derivada del dataset; campos no derivables = `NO_INFORMADO`.
   - `contexto_familia.py`: objeto C2 exacto (§2.7.2) + `inconsistencias` + `no_informado`.
   - `context_filter.py` (o acordado con Rol 2): deja pasar solo campos permitidos (§2.7.3).
3. **Precálculo** persistido (tabla `evaluaciones` + `accesos`) para que Rol 2/3 lean rápido.

### Día 2
4. **Ficha digital → hechos DECLARADO → reevaluación** (soporte a S2 / KPI #2).
5. **Tests obligatorios §6.7** completos (operadores, binding, OR BEN-004, versiones, sin RSH→IND, arquetipos).
6. **Test del filtro** C2 (falla si aparece un campo prohibido).
7. **README de datos**: supuestos (ventana §8.1, campos ausentes), cómo correr, cómo desplegar en AWS.
8. **Sembrar** 3 familias demo verificadas (brecha, discapacidad, sin RSH).

---

## 4. Contratos que entrego

- **C1 (§6.6)**: JSON por (familia×beneficio) con `resultado`, `nivel`, `motivos`, `datos_faltantes`, `entidad_ganadora`, `traza`, `monto_estimado`, `fuentes`. → ya lo produce el motor; se congela su forma.
- **C2 (§2.7.2)**: `contexto_familia` filtrado, sin nombres/RUT/salud/diagnóstico. Plazo spec: Día 2, 12:00.

---

## 5. Definición de terminado (Rol 1)

- [ ] Vistas de cruce creadas y consultables.
- [ ] 10.000 evaluaciones precalculadas en < 30 s con traza.
- [ ] `contexto_familia` para las 500 familias; test de filtro pasando.
- [ ] Tests §6.7 verdes.
- [ ] README con supuestos (incl. ventana de acceso) y cómo correr/desplegar.
- [ ] Base + precálculo corren igual en la nube del equipo (AWS).

---

## 6. AWS (lo mínimo del Rol 1)

- La DB SQLite y el precálculo se generan en el build del contenedor (o un script `make data`).
- El artefacto `e3.db` queda dentro de la imagen → el backend en App Runner/Lambda lo lee de solo lectura.
- Nada de datos personales en logs ni en lo que viaje al LLM (lo asegura el filtro C2).
- Documentar en README el comando de regeneración para que cualquiera reproduzca la base en la nube.
