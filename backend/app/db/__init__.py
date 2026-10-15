"""Vistas de cruce y precálculo persistido (M1 · Rol 1).

Materializa las 10.000 evaluaciones (500 familias × 20 beneficios) del motor
(M2) y del estado de acceso (M3) en tablas SQLite (`evaluaciones`, `accesos`)
y crea las vistas de cruce que consumen Rol 2/3:

- ``v_familia_beneficio`` : una fila por (familia, beneficio) con resultado,
  nivel, estado de acceso y monto.
- ``v_oportunidades``     : subconjunto accionable (SI/INDETERMINADO con acción).
- ``v_brechas``           : pares ELEGIBLE_SIN_ASIGNACION (la brecha estrella).
"""
