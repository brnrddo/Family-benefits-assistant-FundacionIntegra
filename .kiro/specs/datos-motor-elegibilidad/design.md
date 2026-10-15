# Diseño — Rol 1 Datos y motor

**Owner futuro:** `backend/app/{loader,db,engine,access,context}` y `backend/tests`; rama `datos`. Consume [C0](../_shared/contracts/C0-mapeo-ficha.schema.json), produce [C1](../_shared/contracts/C1-salida-motor.schema.json) y [C2](../_shared/contracts/C2-contexto-familia.schema.json). Enlaza [dataset](../../../data/README.md), [diccionario](../../../data/diccionario_datos.md) y [distribución](../../../data/distribucion.md); no copia respuestas internas.

Flujo local obligatorio: cargar bundle público inmutable en DuckDB → validar y crear `v_familia_beneficio`, `v_oportunidades` y `v_brechas` → resolver versión y parámetros → construir candidatos/hechos → evaluar reglas atómicas → combinar AND/OR/bindings ternarios → nivel y traza → estado de acceso/cupo → C1 → contexto/ficha sintética C2. Parámetros y umbrales se leen del bundle; los supuestos sobre campos ausentes son configurables y trazados.

C1 cierra también la semántica entre campos: `SI` siempre tiene nivel no nulo y acceso compatible; `INDETERMINADO` usa `nivel=null` y acceso homónimo; `NO|NO_APLICA` usa `nivel=null` y acceso `NO_APLICA`. El productor rechaza cualquier combinación distinta antes de entregar el contrato.

C2 no es un mapa EAV extensible: cada hecho, inconsistencia, ausencia y señal pertenece al vocabulario cerrado del schema y tiene tipo, enum, rango y longitud explícitos. Agregar un campo exige versionar C2 y revisión de privacidad; nunca se habilita mediante C0 o texto libre.

DuckDB y sus tres vistas son MUST del perfil local. SQLite puede servir localmente. Ninguno activa snapshots cloud. En cloud, la lógica pura Python se invoca dentro de `SnapshotPartitionBuilder` por jardín; S3 es canónico y Rol 2 controla publicación. Rol 1 no llama IA, no define U/B/V ni copy.

Casos obligatorios: todos los operadores y límites de intervalo; dos niños no mezclan bindings; OR BEN-004; fecha 2025 vs 2026; RSH faltante produce IND; arquetipos brecha/discapacidad/tramo alto; rechazo no cambia elegibilidad; BEN-018 reproducible; 500×20 en menos de 30 segundos en el ambiente local documentado. El README futuro registra arquitectura de datos, comando de ejecución, datos faltantes/proxies y la desactivación inicial de la ventana. Estado actual: diseño documentado, implementación/pruebas pendientes.
