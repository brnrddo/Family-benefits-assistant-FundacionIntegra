# Beneficio territorial SOLO DEMO

DATOS SINTETICOS - NO CORRESPONDEN A UNA PERSONA REAL

**SOLO DEMO — beneficio inventado para mostrar la capacidad territorial; no existe.**

`beneficio_local_demo.json` (`data_classification: SYNTHETIC_DEMO_NOT_A_REAL_PERSON`) trae las filas de dos beneficios inventados para cuatro tablas del loader (`beneficios`, `beneficios_versiones`, `reglas_elegibilidad`, `parametros_version`), con exactamente las columnas de los CSV de `data/publico/` (`null` = celda vacía). Ninguno tiene filas de fuentes: no hay URL ni cita oficial.

- `BEN-DEMO-LOCAL-01` (comunal), versión `V-DEMO-LOCAL-01`: `comuna_residencia IN ["COM-001"]` y `tramo_rsh LTE 60`.
- `BEN-DEMO-REGIONAL-01` (regional), versión `V-DEMO-REGIONAL-01`: `region_residencia IN ["REG-SIM-01"]` y `tramo_rsh LTE 60`.

`region_residencia` lo deriva el motor desde la comuna de residencia vía la tabla `comunas` (`region_codigo`). Una familia en `COM-001` (que pertenece a `REG-SIM-01`) aplica a ambos; una en `COM-011` (`REG-SIM-03`) no aplica a ninguno. Ambos vigentes del 2026-01-01 al 2026-10-14.

## Procedimiento

Desde `backend/`:

1. `py -3.11 -m app.loader.load --force`
2. `py -3.11 -m app.demo_territorial.cargar` (idempotente; `--db RUTA` para otra DB)
3. `py -3.11 -m app.db.build_views`

Para volver al dataset original basta con repetir los pasos 1 y 3. `data/` no se modifica.
