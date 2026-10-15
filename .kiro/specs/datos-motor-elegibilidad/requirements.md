# Requisitos — Rol 1 Datos y motor

## MUST

- **DAT-001 — Carga pública DuckDB (§§3 M1, 5).** WHEN se inicia el perfil local, THE SYSTEM MUST cargar E-3 en DuckDB y validar CSV/JSON, PK/FK, enums, nulidad, vigencia y fecha configurable sin leer `interno_no_distribuir`.
- **DAT-002 — Versiones (§§5.2, 6.1).** WHEN se evalúa una fecha, THE SYSTEM MUST elegir la versión con intervalo `[desde,hasta)`; sin versión MUST devolver `NO_APLICA`.
- **DAT-003 — Operadores (§6.3).** THE SYSTEM MUST implementar `EQ`, `LT`, `LTE`, `GT`, `GTE`, `IN`, `BETWEEN`, `ACTIVE_ON_DATE`, `RANGE_LOOKUP`, `REF_EQ`, `COUNT_REL_GTE` y `NOT_EXISTS_WITHIN` desde parámetros, sin umbrales hardcodeados.
- **DAT-004 — AND/OR/bindings (§§6.2, 6.4).** WHEN reglas comparten binding, THE SYSTEM MUST exigir la misma entidad; MUST combinar AND dentro de grupo y OR entre grupos y conservar candidato ganador.
- **DAT-005 — Tres valores/nivel (§6.4).** IF falta o se desconoce un dato, THE SYSTEM MUST producir `INDETERMINADO`; `SI` MUST llevar nivel no nulo y ser `CONFIRMADO` solo con hechos observados/acreditados, si no `PRELIMINAR`; `INDETERMINADO|NO|NO_APLICA` MUST llevar `nivel=null`.
- **DAT-006 — C1 trazable (§6.6).** FOR EACH familia×beneficio, THE SYSTEM MUST producir C1 con versión, snapshot/hashes, motivos, faltantes, binding, traza, monto, fuentes y acceso.
- **DAT-007 — Estado de acceso (§7).** WHEN hay evaluación y gestiones, THE SYSTEM MUST distinguir ocho estados sin permitir que un rechazo cambie criterios.
- **DAT-008 — Cupo BEN-018 (§7).** WHEN BEN-018 es `SI`, THE SYSTEM MUST ordenar por inseguridad descendente, ingreso per cápita ascendente e ID, y marcar fuera del cupo 75 como `SIN_CUPO`.
- **DAT-009 — C2 y ficha sintética (§2.7).** WHEN se genera contexto, THE SYSTEM MUST producir C2 con hechos, procedencia, inconsistencias, no informados y señales usando solo claves, tipos, enums, rangos y longitudes del schema cerrado; MUST NOT inventar campos, aceptar texto libre ni asumir que C2 es LLM-safe.
- **DAT-010 — Reproducibilidad y tiempo (§§5, 6.6, 17).** WHEN corre el snapshot Demo local, THE SYSTEM MUST producir exactamente 10.000 evaluaciones reproducibles en menos de 30 segundos y validar hashes/conteos en el ambiente de referencia documentado.
- **DAT-012 — Vistas DuckDB locales (§§2.6, 3 M1, 18).** WHEN termina la carga local, THE SYSTEM MUST crear `v_familia_beneficio`, `v_oportunidades` y `v_brechas` en DuckDB; estas vistas MUST NOT activar ni servir snapshots cloud.
- **DAT-013 — Supuestos operativos (§§8.1, 12, 17).** BEFORE cierre del MVP, Rol 1 MUST documentar en el README futuro los supuestos de datos faltantes, proxies y `usar_ventana=false`, además del tramo de ejecución de datos reproducible.

## SHOULD

- **DAT-011 — Ficha digital (§10).** WHEN recibe respuestas sintéticas opcionales, THE SYSTEM SHOULD crear hechos `DECLARADO`, mantener “No sé” como desconocido y reevaluar `PRELIMINAR`.

## COULD

No hay capacidades COULD asignadas al Rol 1 en este baseline.

## Fuera de alcance

Priorización U/B/V, endpoints, GenAI, copy, infraestructura AWS, respuestas internas esperadas y modificación de datasets públicos. DuckDB es obligatorio para el perfil local, pero no es datastore ni evaluador cloud.
