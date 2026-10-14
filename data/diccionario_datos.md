# Diccionario de datos E-3

El contrato normativo completo es `especificacion_e3.md`. CSV: UTF-8, coma, encabezado, fechas ISO-8601, timestamps RFC 3339, booleanos `true/false`, intervalos `[desde,hasta)`. Los vacíos representan nulidad permitida. PK/FK, tipos, enums y cardinalidades corresponden a §9 de la especificación.

## Público
`comunas`, `jardines`, `familias`, `integrantes`, `rsh_historial`, hechos EAV, relaciones, accesos habilitantes, catálogo/versiones/parámetros/reglas/fuentes, gestiones/estados/causantes/pagos y JSON consolidado. `id_version_concesion` gobierna decisiones, términos y pagos.

## Interno
`elegibilidad_esperada`, `detalle_reglas`, `causantes_evaluaciones`, vínculos de gestiones, asignación, brechas, arquetipos, excepciones y reporte. `SI` usa `CONFIRMADO|PRELIMINAR`; `NO|INDETERMINADO` no usa nivel.
