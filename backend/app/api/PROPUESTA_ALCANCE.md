# `GET /api/v1/catalogo/alcance` — propuesta del Rol 2 (B2, SOLO DEMO)

**Qué es.** Indica, por beneficio, si es `NACIONAL` o `LOCAL` (solo para quienes viven en ciertas comunas). Sirve para que la PWA muestre el chip "Disponible en su comuna" en la ficha. Los datos del Rol 1 no traen beneficios por comuna; para la demo se agrega `BEN-DEMO-LOCAL-01`, un beneficio **inventado** (`backend/fixtures/demo_territorial/`), que solo existe en la DB local si se carga con `py -3.11 -m app.demo_territorial.cargar`.

**No está en C3 v1.0.2 y el contrato no se editó.** No aparece en el OpenAPI de `/docs`. La respuesta se valida con `frontend/src/api/proposals/CatalogScopeEnvelopeV1.schema.json` y su `meta` con `EnvelopeMetadata` de C3 (`backend/tests/test_demo_territorial.py`).

## Interfaz

| | |
|---|---|
| Ruta | `GET /api/v1/catalogo/alcance` |
| Scope | `familias:read` |
| Respuesta 200 | `{meta, items: [{benefit_id, scope, simple_title, demo}]}` |
| 503 | DB o C4 ilegibles en modo real |
| IA | ninguna |

```json
{"benefit_id": "BEN-DEMO-LOCAL-01", "scope": "LOCAL",
 "simple_title": "Programa Municipal Sintético de Apoyo Familiar (solo demo)", "demo": true}
```

Con mocks (`E3_MOCK=1` o degradación) todos los beneficios de los mocks son `NACIONAL` y `demo: false`.

## Regla LOCAL / NACIONAL

Un beneficio es `LOCAL` si **todos** los grupos OR de su versión vigente (a la fecha de `evaluaciones`) tienen una regla vigente `comuna_residencia IN [...]` cuya lista no cubre todas las comunas de la tabla `comunas`. Si no, `NACIONAL`. Solo se leen reglas: la API **no filtra por comuna**. Si una familia aplica o no lo decide el motor del Rol 1 con el domicilio de la familia (no el del jardín).

## Qué significa "no sale como oportunidad"

Una `Opportunity` de C3 exige una cita oficial HTTPS. El ejemplo no tiene fuente, así que no aparece en el top de Inicio, en `/oportunidades`, ni en guion o mensaje como oportunidad. Sí aparece en la ficha (`benefit_results`) con su resultado, para que la tía sepa que existe y qué le falta a la familia.

## Privacidad

Sin IDs ni nombres de comuna y sin IDs de familia en la respuesta. Logs: solo `request_id`, ruta normalizada, status y latencia. Todo es sintético y rotulado "SOLO DEMO".

## Propuestas y preguntas

- **DEC-070:** la ficha (`GET /familias/{id}` y `POST /antecedentes`) lista solo `SI`/`INDETERMINADO`; el snapshot y el motor conservan `NO`/`NO_APLICA`.
- **DEC-071:** el ejemplo vive en un fixture aparte, se carga a la SQLite local con un comando idempotente y su presentación (título, dónde ir, texto) es un overlay activo solo si la DB trae el ID; si `content/` lo trae, manda `content/`.
- **DEC-072:** esta ruta, fuera de C3 1.0.2.
- **PREG-070:** el Rol 4 pasa los textos del ejemplo y del chip a `content/` / `es.json`.
- **PREG-071:** incorporar el alcance a la próxima versión de C3.
