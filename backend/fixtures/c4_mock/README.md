# Mock C4 de desarrollo (Rol 2)

DATOS SINTETICOS - NO CORRESPONDEN A UNA PERSONA REAL

Este bundle JSON es un **mock de desarrollo del Rol 2** y **NO es autoridad de contrato**.
La autoridad de C4 vive en `content/` (YAML/CSV/MD, dueño Rol 4, `content/manifest.yaml`).
Queda pendiente el adaptador JSON→YAML para que el Rol 2 consuma el bundle autoritativo
(ver `DEC-022` en `.kiro/specs/_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md`).

Notas de lectura:

- `files[].path` y `canonical_i18n` declaran rutas `content/...` porque el schema cerrado C4
  las fija (`canonical_i18n` es `const`, `path` tiene pattern `^content/`). Son identificadores
  lógicos del contrato, no rutas de disco: ninguna capa runtime las resuelve a archivos.
- `content_bundle_hash` es un placeholder de 64 ceros, no el hash canónico del Rol 4.
- Los valores numéricos son demostrativos y no provienen de datos reales.
- Para apuntar a otro bundle, usar la variable de entorno `E3_CONTENT_MANIFEST`.
