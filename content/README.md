# content/ — contenido del Rol 4

Datos y textos que consumen los demás roles: mapeo C0 de la ficha y bundle C4 (ranking, preguntas, beneficios, prompts, accesibilidad, i18n y activos demo). Solo CSV, JSON, YAML, Markdown y un PNG sintético; sin código ni reglas de elegibilidad. No contiene datos de personas.

Estado: **0.2.1, no publicable** (DEC-040): valores completos (DEC-041 a DEC-045) y copy del catálogo i18n 1.2.0; falta API-T14 y revisión humana. Ninguna capa runtime debe activarlo.

| Archivo | Clase | Consumidor |
|---|---|---|
| `mapeo_ficha.csv` | C0 (fuera del bundle C4) | Rol 1 (motor) y Rol 2 |
| `manifest.yaml` | instancia C4 (no se lista a sí mismo) | Rol 2 |
| `pesos_priorizacion.yaml` | `WEIGHTS` | Rol 2 (ranking U/B/V) |
| `accessibility.yaml` | `ACCESSIBILITY` | Roles 2 y 3 |
| `beneficios.yaml` | `BENEFITS` | Rol 2 (catálogo y prompts) |
| `preguntas.yaml` | `QUESTIONS` | Rol 2 |
| `i18n/es.json` | `I18N` (canónico, DEC-010) | Rol 3 (PWA) |
| `prompts/*.md` (4) | `PROMPT` | Rol 2 (GenAI con plantilla de respaldo) |
| `demo/inventario_activos.yaml` | `SYNTHETIC_ASSET_MANIFEST` | Roles 2 y 4 |
| `demo/*` (fixtures, salidas de referencia, afiche) | vía inventario | Roles 2 y 4 |
| `VALORES_RANKING.md` | explicación de los valores (fuera del bundle C4) | equipo e Integra |
| `.gitattributes` | fin de línea LF para los hashes (DEC-045, fuera del bundle C4) | Git |

Hashes: `files[].sha256` y `content_bundle_hash` siguen SUP-041; `ranking` y `accessibility` del manifiesto son copia idéntica de sus archivos (SUP-040). Al editar un archivo listado hay que recalcular su hash y el del bundle. Las fixtures de `content/demo/` (`familias_demo.yaml`, `salidas_referencia_prompts.json`) conservan su versión 0.1.0: es la versión del set de fixtures y sus bytes no cambiaron.

Preguntas pendientes: PREG-045 (beneficios sin fuente HTTPS), PREG-047 (semántica de `amount`), PREG-048 (BEN-010 sin monto), PREG-008 (Textract) y PREG-009 (voces e idiomas).

Validación oficial: la futura tarea API-T14 (`python -m backend.app.contracts.validate_content --manifest content/manifest.yaml`), aún no implementada. Mientras tanto, el Rol 4 usa un validador local fuera del repositorio.
