# `POST /api/v1/familias/{id}/antecedentes` — propuesta del Rol 3 implementada en servidor

**Qué es.** La operación `addFamiliaAntecedentes` la **propuso el Rol 3** (DEC-039 / PREG-039, `frontend/docs/PROPUESTA_C3_agregar_informacion.md`) y el Rol 2 la implementó en el backend. Permite que la tía agregue antecedentes de una familia **existente**: cada campo declarado queda como hecho `estado_dato=DECLARADO`, `acreditada=false`, y la ficha se reevalúa.

**No está en C3 v1.0.2 y el contrato no se editó.** `.kiro/specs/_shared/contracts/C3-api.openapi.yaml` queda intacto en `1.0.2`: el Rol 3 lo fija por hash y su cliente generado se compila contra él. Agregar una ruta al YAML sin acuerdo de equipo rompería ese hash y convertiría una propuesta en contrato. Por eso la operación se sirve, pero **no aparece** en el OpenAPI que publica `/docs` (que sigue siendo el YAML C3 tal cual). Queda pendiente incorporarla a la próxima versión de C3 por acuerdo del equipo; hasta entonces el request se valida con el schema del Rol 3 (`frontend/src/api/proposals/AddFamilyInfoRequestV1.schema.json`) y la respuesta se valida contra componentes de C3 sin modificarlos (`backend/tests/test_api_antecedentes.py`).

## Interfaz

| | |
|---|---|
| Ruta | `POST /api/v1/familias/{id}/antecedentes` |
| `operationId` | `addFamiliaAntecedentes` |
| Scope | `familias:write` |
| Header obligatorio | `Idempotency-Key` (UUID) |
| Request | `AddFamilyInfoRequestV1` (cerrado) |
| Respuesta 200 | `FamiliaDetailEnvelope` de C3, **sin cambios de forma** |
| IA | **ninguna**; esta ruta no llama Bedrock |

El request es un subconjunto cerrado de los 18 campos de `PreevaluationRequest` (C3) con idénticos tipos, enums y rangos, más `data_classification`. **No** acepta `garden_id`, `commune_id`, `demo_notice_accepted`, nombres, identificadores, contacto ni texto libre. Cualquier propiedad extra → `422`.

```json
{
  "data_classification": "SYNTHETIC_DEMO_NOT_A_REAL_PERSON",
  "has_rsh": true,
  "household_income_band": "UNDER_110K"
}
```

La respuesta usa el **mismo serializador** que `GET /familias/{id}` (`app/api/serializers.py::familia_detail_data`), así que ambas fichas no pueden derivar de forma.

## Semántica de los campos

| En el cuerpo | Significa | Efecto |
|---|---|---|
| clave **ausente** | sin cambio | ningún hecho, nada se modifica |
| valor conocido | dato declarado | hecho `DECLARADO`; su `missing_code` deja de faltar |
| `null` | "No sé" | hecho **DESCONOCIDO**; el `missing_code` sigue faltando. **Nunca** se degrada a `false` ni `0` |
| `housing_type: "UNKNOWN"` | "No sé" | igual que `null` |

Los `missing_code` son el enum cerrado de `FamilyContextView.missing_codes` (C3) y espejan exactamente el mapa `MISSING_CODE_FIELD` del cliente del Rol 3 (`frontend/src/api/proposals/addInfo.ts`).

Todo resultado u oportunidad sustentado en un hecho declarado baja a `level = "PRELIMINAR"` y **nunca** queda `CONFIRMADO`: lo declara la tía, no una institución. Un dato declarado "No sé" también aparece como "no informado" en `GET /familias/{id}/contexto`, que es el campo que C3 tiene para eso.

## Códigos de estado

| Status | Cuándo |
|---|---|
| `200` | reevaluada, o repetición idempotente (misma clave + mismo cuerpo canónico) |
| `409` | misma clave con cuerpo distinto |
| `422` | cuerpo inválido, `Idempotency-Key` ausente o no-UUID, o familia sin datos que declarar |
| `401` | credencial de demo sin scopes |
| `404` | familia inexistente o fuera de scope |
| `503` | motor no disponible |

Nunca `201`: la operación no crea un recurso visible. El `404` **no está en la tabla de la propuesta del Rol 3**: se agregó porque todas las rutas `/familias/{id}` de este backend ocultan la existencia con 404 (API-005). Para el cliente, cuyo `expectedStatus` es 200, cae como error de contrato, que es el comportamiento seguro.

## Qué hace y qué NO hace la reevaluación

Con `E3_MOCK=1` (modo de la demo) la reevaluación es **simulada, determinista y acotada**:

- **sí**: resuelve o conserva `missing_codes`, baja el nivel a `PRELIMINAR` y refleja `rsh_band` / `income_band` declarados (mismo campo y mismo enum de C3, no una inferencia);
- **no**: no cambia ningún `result`, no promueve `INDETERMINADO → SI`, no recalcula U/B/V, `score` ni `position`. Esos números son del motor determinista (Rol 1) y del bundle C4; inventarlos sería decidir elegibilidad.

Con `E3_MOCK=0` la ruta responde `503 UNAVAILABLE` (`retryable: true`, que es el reintento manual que espera el Rol 3) en vez de devolver una simulación como si fuera reevaluación real: `FamiliaDetailEnvelope` es cerrado y no tiene dónde avisar que el dato es simulado. El enganche del motor real está en un único punto de `app/api/routers/antecedentes.py`.

## Idempotencia, persistencia y logs

Misma clave + mismo cuerpo canónico devuelve la **misma** respuesta sin efectos nuevos; misma clave con cuerpo distinto es `409`. El cuerpo canónico se hashea con `exclude_unset=True`, de modo que `{"has_rsh": null}` y un cuerpo sin `has_rsh` **no** colisionan. No hay cola offline: la operación solo funciona en línea.

Los hechos declarados viven en memoria **por proceso** (mismo criterio que la idempotencia de `conversaciones`): no sobreviven a un reinicio ni se comparten entre workers. Alcanza para la demo y evita que la ficha "vuelva atrás" al refrescar, porque `GET /familias/{id}`, `/contexto` y `/oportunidades` aplican los mismos hechos.

Logs (API-013): solo `request_id`, la ruta normalizada `/familias/{id}/antecedentes`, el status y la latencia. Nunca el cuerpo, los valores declarados, el nombre de los campos ni identificadores.

## Activación en el frontend (Rol 3)

1. `VITE_PROPOSAL_ADD_INFO=true` en el entorno del front: usa la operación también contra la API real (vacía = solo mocks; `false` = oculta).
2. Verificar con `npm run check:api` desde `frontend/`.

Ninguno de esos comandos se ejecutó desde el backend.

## Preguntas abiertas para el Rol 3

1. **`409` por "snapshot en conflicto" no tiene disparador.** El request cerrado no transporta `snapshot_id` y no se especificó un header tipo `If-Match`, así que hoy el `409` solo cubre clave repetida con cuerpo distinto. Si el conflicto de snapshot importa, hay que acordar cómo viaja.
2. **Confirmar el `404`** para familia inexistente o fuera de scope.
3. **IDs de familia.** Los mocks del Rol 3 usan `FAM-SIM-E3-00002`; este backend sirve `FAM-SIM-0001` / `FAM-SIM-0002` (los que entrega `GET /jardines/{id}/familias`). No se alinearon porque `content/` y `backend/fixtures/` están fuera de alcance en esta tarea.

Todos los datos de este backend son sintéticos (`SYNTHETIC_DEMO_NOT_A_REAL_PERSON`) y no corresponden a ninguna persona real.
