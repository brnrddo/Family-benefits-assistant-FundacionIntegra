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

Los `missing_code` son el enum cerrado de `FamilyContextView.missing_codes` (C3) y espejan exactamente el mapa `MISSING_CODE_FIELD` del cliente del Rol 3 (`frontend/src/api/proposals/addInfo.ts`). `last_child_health_control_date` además se valida como fecha `YYYY-MM-DD` real (el `format: date` del schema del Rol 3), sin cambiar el tipo del campo.

Todo resultado u oportunidad sustentado en un hecho declarado baja a `level = "PRELIMINAR"` y **nunca** queda `CONFIRMADO`: lo declara la tía, no una institución. Un dato declarado "No sé" queda "no informado" en tres lugares coherentes entre sí: el `BenefitResult` que lo sustenta, la `Opportunity` de ese mismo beneficio (hereda los códigos del `BenefitResult`, porque C3 no le da `trace`) y `GET /familias/{id}/contexto`.

Un "No sé" **no borra** el dato que vino del motor: si la familia traía `rsh_band: 40` de C1/C2, declarar `rsh_band: null` deja la banda en `40` y solo agrega el código a "no informado". Borrarla dejaría la vista de contexto contradictoria con sus propios `*_score`, que son del motor. `rsh_band` y `household_income_band` se reflejan en la ficha y el contexto **solo** cuando se declaran con valor conocido.

Si el mismo campo se declara dos veces, gana el último hecho: la tía puede corregirse (declarar "No sé" y después la banda, o al revés).

## Códigos de estado

| Status | Cuándo |
|---|---|
| `200` | reevaluada, o repetición idempotente (misma clave + mismo cuerpo canónico) |
| `409` | misma clave con cuerpo distinto, o la misma clave reusada contra otra familia |
| `422` | cuerpo inválido, `Idempotency-Key` ausente o no-UUID, o familia sin datos que declarar |
| `401` | credencial de demo sin scopes |
| `404` | familia inexistente o fuera de scope |
| `503` | motor real no disponible con `E3_MOCK=0` (sin DB/precálculo/C4 válidos) |

Nunca `201`: la operación no crea un recurso visible. El `404` **no está en la tabla de la propuesta del Rol 3**: se agregó porque todas las rutas `/familias/{id}` de este backend ocultan la existencia con 404 (API-005). Para el cliente, cuyo `expectedStatus` es 200, cae como error de contrato, que es el comportamiento seguro.

## Qué hace y qué NO hace la reevaluación

Con `E3_MOCK=1` (modo de la demo) la reevaluación es **simulada, determinista y acotada**:

- **sí**: resuelve o conserva `missing_codes` (en el `BenefitResult`, en la `Opportunity` del mismo beneficio y en el contexto), baja el nivel a `PRELIMINAR` y refleja `rsh_band` / `income_band` declarados **con valor conocido** (mismo campo y mismo enum de C3, no una inferencia);
- **no**: no cambia ningún `result`, no promueve `INDETERMINADO → SI`, no recalcula U/B/V, `score`, `position` ni los `*_score` del contexto, y no borra datos de C1/C2. Esos números son del motor determinista (Rol 1) y del bundle C4; inventarlos sería decidir elegibilidad.

Con `E3_MOCK=0` (B2) la ruta **reevalúa de verdad con el motor determinista** y devuelve una `FamiliaDetailEnvelope` recalculada (elegibilidad, nivel, `missing_codes`, U/B/V, `score`, `position` y oportunidades), reusando la misma maquinaria que el snapshot. De los campos de la pantalla, el **único** que el motor puede convertir en elegibilidad hoy es `last_child_health_control_date`: se transforma en `dias_desde_control` (días hasta la fecha de evaluación, nunca negativo) del niño o niña **más joven** de la familia (menor de 18) y alimenta la regla `R01203` del subsistema SSyO. Un dato declarado nunca da `CONFIRMADO` (el motor da `PRELIMINAR` como máximo). El resto de los campos **no tiene mapeo al motor** y no mueve elegibilidad por esta vía:

- `household_pregnancy` llega como booleano; el motor pide `semanas_gestacion` (número), que no se puede derivar de un sí/no sin inventar;
- RSH, ingreso, Chile Crece Contigo y SSyO vienen de registros oficiales (no declarables por diseño);
- discapacidad, terapia, vivienda, empleo, agua y alimentación no existen como `campo_dato` del motor.

Si el motor real no puede operar (sin DB, sin precálculo o sin C4 válido) la ruta falla cerrada con `503 UNAVAILABLE` (`retryable: true`). El enganche vive en un único punto de `app/api/routers/antecedentes.py` (helper `_reevaluar_con_motor`) y la reconstrucción de la ficha en `app/api/motor_real.py` (`reconstruir_familia_declarada`); la traducción pantalla→motor está aislada en `app/api/antecedentes_motor.py`.

> **Nota para la demo (efecto visible de declarar la fecha del control).** Declarar `last_child_health_control_date` **no siempre cambia la ficha**, y eso es correcto, no un fallo del cableado. El motor resuelve `dias_desde_control` por dos caminos (ver `app/engine/resolver.py`, con `SUPONER_CONTROL_VIGENTE=True`, el default):
>
> 1. **La familia ya tiene un control infantil vigente en la base.** El motor asume `0 días` por evidencia indirecta y resuelve la regla por su cuenta; el beneficio del control ya daba `SI` (`PRELIMINAR`) sin declaración. En este caso la fecha declarada **no se usa** y la ficha no cambia.
> 2. **La familia NO tiene ese control vigente en la base.** El dato faltaba y el beneficio estaba en `INDETERMINADO`; aquí la fecha declarada → días lo desbloquea a `SI` (`PRELIMINAR`). En este caso el cambio **sí es visible**.
>
> Para mostrar el efecto en la demo, elegir una familia con un niño o niña menor de 18 **sin** control infantil vigente registrado (grupo 2). No es un comportamiento que introduzca B2: es el supuesto preexistente del motor, que ahora decide si una declaración por pantalla tiene efecto observable.

## Idempotencia, persistencia y logs

Misma clave + mismo cuerpo canónico devuelve la **misma** respuesta sin efectos nuevos; misma clave con cuerpo distinto es `409`. El cuerpo canónico incluye el `family_id` del path y se hashea con `exclude_unset=True`: `{"has_rsh": null}` y un cuerpo sin `has_rsh` **no** colisionan, y reusar una clave contra **otra** familia es `409` en vez de devolver la ficha de la primera. No hay cola offline: la operación solo funciona en línea.

La repetición idempotente sirve la respuesta **guardada en el primer POST**. Si entremedio se declararon otros hechos, ese `data` ya no coincide con `GET /familias/{id}`: es la semántica de idempotencia pedida, pero conviene no mostrar las dos vistas juntas en la demo.

Los hechos declarados viven en memoria **por proceso** (mismo criterio que la idempotencia de `conversaciones`): no sobreviven a un reinicio ni se comparten entre workers. Alcanza para la demo y evita que la ficha "vuelva atrás" al refrescar, porque `GET /familias/{id}`, `/contexto` y `/oportunidades` aplican los mismos hechos.

**Retención (limitación de demo, explícita).** Los dos registros en memoria (`app/api/antecedentes_store.py`) no tienen tope de tamaño ni expiración y son del proceso, no del cliente: un hecho declarado cambia la respuesta de las tres rutas GET para cualquier consumidor de ese proceso, y la única forma de vaciarlos es reiniciar el backend (o `reset()` en los tests). Son datos 100 % sintéticos. Una integración real exige store por sesión/familia con TTL, lo que queda fuera de esta tarea.

Logs (API-013): la línea del router lleva solo `request_id`, la ruta normalizada `/familias/{id}/antecedentes`, el status y la latencia. Nunca el cuerpo, los valores declarados ni el nombre de los campos. El middleware preexistente de `app/api/app.py` sí registra el path crudo, que incluye el ID **seudónimo sintético** de la familia; eso es anterior a esta operación y no se modificó aquí (normalizar el path del middleware es una tarea aparte).

## Activación en el frontend (Rol 3)

1. `VITE_PROPOSAL_ADD_INFO=true` en el entorno del front: usa la operación también contra la API real (vacía = solo mocks; `false` = oculta).
2. Verificar con `npm run check:api` desde `frontend/`.

Ninguno de esos comandos se ejecutó desde el backend.

## Preguntas abiertas para el Rol 3

1. **`409` por "snapshot en conflicto" no tiene disparador.** El request cerrado no transporta `snapshot_id` y no se especificó un header tipo `If-Match`, así que hoy el `409` solo cubre clave repetida con cuerpo distinto. Si el conflicto de snapshot importa, hay que acordar cómo viaja.
2. **Confirmar el `404`** para familia inexistente o fuera de scope.
3. **IDs de familia.** Los mocks del Rol 3 usan `FAM-SIM-E3-00002`; este backend sirve `FAM-SIM-0001` / `FAM-SIM-0002` (los que entrega `GET /jardines/{id}/familias`). No se alinearon porque `content/` y `backend/fixtures/` están fuera de alcance en esta tarea.

Todos los datos de este backend son sintéticos (`SYNTHETIC_DEMO_NOT_A_REAL_PERSON`) y no corresponden a ninguna persona real.
