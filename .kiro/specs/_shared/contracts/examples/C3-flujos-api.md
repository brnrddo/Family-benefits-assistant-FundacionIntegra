# Flujos C3 2.0.0

DATOS SINTETICOS - NO CORRESPONDEN A UNA PERSONA REAL

La única base es `/api/v2`. DEC-023 aprobó la migración in-place porque no existe runtime C3. No hay alias ni ruta legacy.

## Alta y primera preevaluación

1. `POST /api/v2/form-records` crea un expediente sintético con `form_record_id`, páginas `[1,2,3]`, `INSCRIPCION_INICIAL=BORRADOR` y `MATRICULA=NO_DISPONIBLE_AUN`.
2. `PUT /form-records/{form_record_id}/stages/inscripcion-inicial` guarda respuestas tipadas C0 de páginas 1–2. `UNKNOWN` no lleva `value`; se normaliza a `DESCONOCIDO`, `acreditada=false` y `no_informado`.
3. `POST .../inscripcion-inicial/completion` recibe solo una atestación sintética cerrada. Las reglas de completitud permanecen `PENDIENTE_VALIDACION_INTEGRA`; el servidor falla cerrado hasta satisfacerlas.
4. Solo con `INSCRIPCION_INICIAL=COMPLETA`, `POST /form-records/{form_record_id}/preevaluations` ejecuta motor determinista y devuelve evaluación `PRELIMINAR`. Ranking y GenAI ocurren después del gate y motor.
5. `GET /form-records/{form_record_id}/evaluations/{evaluation_id}` obtiene la versión autorizada.

## Matrícula y reevaluación

1. `POST .../matricula/enablement` acepta únicamente `event_type=AUTHORIZED_ENROLLMENT_EVENT` y `validation_status=PENDIENTE_VALIDACION_INTEGRA`; cambia página 3 a `PENDIENTE`.
2. `PUT .../matricula` guarda solo respuestas tipadas permitidas de página 3 en el mismo `form_record_id`.
3. `POST .../matricula/completion` exige página 3 habilitada y completa. Omitirla impide `MATRICULA=COMPLETA`.
4. `PATCH /form-records/{form_record_id}/responses` incrementa `record_version`, conserva procedencia y marca la evaluación anterior `STALE`.
5. `POST /form-records/{form_record_id}/reevaluations` crea una `evaluation_version` nueva sin cambiar el expediente.

Toda mutación exige `Idempotency-Key`. Misma clave y cuerpo devuelve el mismo resultado. Misma clave con otro cuerpo o `expected_record_version` obsoleta devuelve `409`.

## Casos negativos obligatorios

- Sin expediente, con `BORRADOR` o con inscripción funcionalmente vacía no se evalúa (`404`, `409` o `422`).
- Página 3 no puede editarse ni completarse antes de habilitación; después de matrícula no puede omitirse.
- `UNKNOWN` con `value`, o convertido a `false`/`0`, falla.
- Cada mutación admite como máximo una respuesta por `field_id`; repetir un ID con valores iguales, opuestos o estados `ANSWERED`/`UNKNOWN` distintos devuelve `422` antes de persistir, normalizar o evaluar. `x-unique-by: field_id` expresa esta invariante semántica en los tres lotes C3; no se sustituye por `uniqueItems` de objetos.
- Los campos `p1.household.day_caregiver` y `p2.housing.bedroom_count` se conservan respectivamente como hechos C2 `household.day_caregiver` y `housing.bedroom_count`, con procedencia de página/sección/campo; nunca se descartan después de ser aceptados.
- `p2.housing.camp_occupation` y `p2.housing.room_other_home` se conservan como hechos booleanos C2 distintos. La derivación versionada `HOUSING-TYPE-V1` aplica esta tabla: `true/false → CAMP_OR_OCCUPATION`; `false/true → ROOM_IN_OTHER_HOME`; `false/false`, `true/true` o cualquier combinación con `UNKNOWN → valor=null, estado_dato=DESCONOCIDO`. Nunca infiere `ADEQUATE` ni `OTHER`. Son adversariales obligatorios: descartar un hecho, resolver por orden, convertir `UNKNOWN` a booleano o devolver un tipo específico ante conflicto/ausencia.
- Todo `field_id` C0 con destino `C2_CONTEXT` tiene una entrada exacta en `x-c0-field-crosswalk` de C2. La API debe producir ese hecho y su procedencia; si recibe `UNKNOWN`, agrega además el mismo campo a `no_informado`. Los enums pendientes solo pueden materializarse como `DESCONOCIDO` hasta validación.
- Los destinos muchos-a-uno (`composition` desde `p1.household.roles_ages` y `p2.household.roles_ages`; cada `adult.{mother|father|guardian}.household_head_signal` desde la señal de página 1 y la continuación de página 2; `child.possible_disability` desde `p1.nee.possible_disability` y `p3.nee.flag`) se combinan solo con `x-c0-many-to-one-policy-v1`. Cada `field_id` fuente se conserva como hecho con su procedencia; el hecho efectivo usa fórmula versionada con procedencia `CALCULADO` y la regla `EQUAL_OR_SINGLE_ANSWERED`. Dos fuentes respondidas e iguales dan ese valor; una sola respondida da la respondida; ambas `UNKNOWN` o dos valores opuestos cierran a `valor=null`, `estado_dato=DESCONOCIDO`, agregan el campo a `no_informado` y, ante conflicto, registran la inconsistencia (`COMPOSITION_MISMATCH`, `HOUSEHOLD_HEAD_SIGNAL_MISMATCH` o `POSSIBLE_DISABILITY_MISMATCH`) con `campo_destino`, `formula_id` y los dos `fact_id` fuente. Son adversariales obligatorios: dos `field_id` fuente del mismo destino con valores opuestos (por ejemplo `p1.nee.possible_disability=true` y `p3.nee.flag=false`) deben cerrar el efectivo a `DESCONOCIDO` con el conflicto trazado; elegir un valor en silencio, resolver por página u orden de llegada, descartar un hecho fuente o derivar el efectivo sin procedencia `CALCULADO` fallan.
- Las vistas de lectura `FamilyContextView` y `FormEvaluation` proyectan `C2.inconsistencias` en `inconsistency_codes`, incluidos los cierres muchos-a-uno `COMPOSITION_MISMATCH`, `HOUSEHOLD_HEAD_SIGNAL_MISMATCH` y `POSSIBLE_DISABILITY_MISMATCH`. Un conflicto de `child.possible_disability` (negativo `FAM-SIM-0003`) devuelve `inconsistency_codes:["POSSIBLE_DISABILITY_MISMATCH"]` y `missing_codes:["possible_disability"]`; un conflicto de `adult.{mother|father|guardian}.household_head_signal` devuelve `inconsistency_codes:["HOUSEHOLD_HEAD_SIGNAL_MISMATCH"]` y `missing_codes:["household_head_signal"]`, de modo que el consumidor distingue "cerrado por conflicto" de "no respondido". Son adversariales obligatorios: omitir el código de inconsistencia muchos-a-uno al proyectar, o dejar invisible el cierre de jefatura sin `household_head_signal`, fallan.
- `p2.income.band` es la banda total del hogar y se conserva como `income.household_band`. Nunca se copia a `income.per_capita_band`, al score de ingreso ni a `LlmContextV1`; sin una derivación aprobada, `income.per_capita_band` permanece `DESCONOCIDO`, la regla dependiente da `INDETERMINADO` y el ranking excluye esa señal.
- Cada `field_id` queda ligado a su tipo y allowlist exactos: por ejemplo, una banda RSH fuera de `40|50|60|70|80|90|100` y un formato fuera de `TEXT|VISUAL|AUDIO` fallan. Un enum `PENDIENTE_VALIDACION_INTEGRA` acepta solo `UNKNOWN`, nunca `ANSWERED`, hasta aprobación.
- Los antecedentes adultos usan IDs distintos por madre, padre y encargado; un ID genérico `p1.adult.*` o `p2.adult.continuation` falla y no puede colapsar roles.
- RSH ausente conserva el alta y da `INDETERMINADO` donde corresponda.
- Una discrepancia RSH agrega `RSH_STATUS_MISMATCH`; no sobreescribe lo declarado.
- Campos C0 `LOCAL_TIA` o `TOTALMENTE_EXCLUIDO`, propiedades extra, PII, PDF, bytes, base64, URL, claves de almacenamiento, prompts, catálogo, C1/C2 crudo o mapa EAV abierto fallan antes del motor/downstream.
- Logs y evidencia contienen solo `request_id`, operación, ruta normalizada, código, estado, latencia y versiones; nunca bodies, preguntas, respuestas, fichas, prompts ni endpoints privados.

## Flujos existentes

Rol 3 lista jardines y familias, conserva snapshot/hashes y refresca ante `409`. Guion/mensaje envían solo `benefit_ids`; el servidor carga C1/C2/C4 y construye `LlmContextV1` por allowlist. `/asistente` acepta solo `question`; una consulta individual no llama Bedrock. `PrintableCard` contiene texto/citas tipados, nunca markup. Afiche acepta solo `TextractFlyerRequestV1` sintético inventariado. C1 y `Opportunity` conservan las invariantes de resultado/nivel/acceso.
