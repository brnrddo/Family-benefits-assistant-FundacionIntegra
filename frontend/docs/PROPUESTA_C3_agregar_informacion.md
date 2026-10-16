# Propuesta C3: agregar información a una familia existente

**Estado:** PROPUESTA del frontend (DEC-039, PREG-039). No es parte de C3 v1.0.2 ni edita el contrato. Para Rol 2, con el motor de Rol 1.

## Operación

`POST /api/v1/familias/{id}/antecedentes` · `operationId: addFamiliaAntecedentes` · scope `familias:write` · header obligatorio `Idempotency-Key` (UUID).

- **Request** `AddFamilyInfoRequestV1` (schema cerrado en `frontend/src/api/proposals/AddFamilyInfoRequestV1.schema.json`): `data_classification: SYNTHETIC_DEMO_NOT_A_REAL_PERSON` y al menos uno de los 18 campos cerrados de `PreevaluationRequest`, con sus mismos tipos y enums. Una clave ausente significa "sin cambio". `null` significa "No sé"; en `housing_type`, "No sé" es `UNKNOWN`. No lleva `garden_id`, `commune_id`, nombres, identificadores, contacto ni texto libre.
- **Respuesta 200**: `FamiliaDetailEnvelope` de C3 sin cambios, con la ficha re-evaluada. Los resultados que usan datos declarados van en `PRELIMINAR`. La UI la usa tal cual y no infiere elegibilidad.

| Status | Significado | Front |
|---|---|---|
| 200 | Re-evaluada, o repetición con la misma clave y el mismo cuerpo | Refresca la ficha |
| 201 | No se usa: no crea un recurso visible | Error contractual |
| 409 | Misma clave con otro cuerpo, o snapshot en conflicto | Error seguro y clave nueva |
| 422 | Cuerpo inválido o familia sin datos que declarar | Error seguro |
| 401 | Sin sesión o token inválido | Error seguro de sesión |
| 503 | Motor no disponible | Reintento manual con la misma clave |

**GET previo** `GET /api/v1/familias/{id}/antecedentes` (scope `familias:read`, también fuera de C3): `data` = `family_id`, `pregnancy_weeks_threshold` (umbral N del motor) y, opcional, `declared_fields` (DEC-093: nombres de campo ya declarados en el proceso, nunca valores). La pantalla lo pide siempre: con N arma la pregunta de semanas y con `declared_fields` no vuelve a preguntar lo ya declarado. Si falla, pregunta sin filtro y semanas sin número.

## Idempotencia y privacidad

La misma clave con el mismo cuerpo canónico devuelve la misma respuesta sin efectos nuevos. Solo funciona en línea: no hay cola offline. En `escala` queda oculta hasta que Integra apruebe el uso de datos reales.

Los logs registran solo `request_id`, la ruta normalizada `/familias/{id}/antecedentes`, el status y la latencia. Nunca el cuerpo. El nombre de trato del niño o niña no viaja nunca (DEC-038).

## Relación con Rol 1

Esta operación cubre el pendiente "ficha digital → hechos `DECLARADO` → reevaluación" de `backend/HANDOFF_ROL1.md` (rama `rol1/datos-motor-contexto-genai`). Cada campo se guarda como hecho `estado_dato=DECLARADO`, `acreditada=false`, y el motor re-evalúa la familia.

## Activación en el front

Variable `VITE_PROPOSAL_ADD_INFO`:

- Vacía: la función está activa solo con mocks.
- `true`: la usa también con la API real. Actívela cuando Rol 2 publique la ruta y pase `npm run check:api`.
- `false`: la oculta.

El mock (`src/mocks/handlers.ts`) simula la re-evaluación con datos sintéticos, y `src/mocks/proposals/` trae un ejemplo de request y respuesta.
