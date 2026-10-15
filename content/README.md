# Bundle C4 — PROVISIONAL (NO autoritativo)

DATOS SINTETICOS - NO CORRESPONDEN A UNA PERSONA REAL

Este bundle C4 es **PROVISIONAL** y existe solo para desbloquear el ranking
determinista U/B/V del Rol 2 (FEAT-001) mientras el contenido autoritativo lo
produce el Rol 4. **No** es la autoridad final de contenido ni de los números
de negocio de §8: cuando el Rol 4 publique el bundle C4 definitivo (con
`content_bundle_hash` real y revisión humana), este directorio se reemplaza.

Alcance y límites:

- Valida contra `.kiro/specs/_shared/contracts/C4-contenido-manifest.schema.json`.
- Las seis clases obligatorias (`WEIGHTS`, `QUESTIONS`, `BENEFITS`, `PROMPT`,
  `ACCESSIBILITY`, `I18N`) apuntan a archivos reales bajo `content/`.
- Los `sha256` de cada archivo en `manifest.json` corresponden al contenido real.
- `content_bundle_hash` es un placeholder consistente de 64 hex; no es el hash
  canónico del Rol 4.
- Polly y Translate están deshabilitados (`enabled=false`) con `evidence_state`
  `NO_VERIFICADO`, allowlists vacías y claves i18n de fallback.
- Ningún archivo C4 reemplaza parámetros normativos de elegibilidad: la
  elegibilidad y el acceso los decide el motor del Rol 1 (C1).

Los valores numéricos (pesos, umbrales, medianas, bonus) son demostrativos y
no provienen de datos reales.
