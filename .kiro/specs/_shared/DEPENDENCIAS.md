# Dependencias, ownership e integración

## Autoridades

1. [`PROYECTO_3_ESPECIFICACION_v2.md`](../../../docs/especificacion/PROYECTO_3_ESPECIFICACION_v2.md) es la fuente funcional original e inmutable.
2. [`ADENDA_FICHA_INGRESO.md`](../../../docs/especificacion/ADENDA_FICHA_INGRESO.md) y [DEC-023](./DECISIONES_SUPUESTOS_PREGUNTAS.md#decisiones) aclaran el expediente único y el gate sin modificar la fuente.
3. El [spec maestro](../apoyo-inteligente-familias/requirements.md) interpreta ambas autoridades con requisitos `PROD-*`.
4. Los contratos de [`contracts/`](./contracts/) son la única autoridad de interfaces C0–C4. C0 v2, C2 v2 y C3 2.0.0 migraron in-place; C1, C4 y `LlmContextV1` no cambian.
5. Cada `design.md` satisface requisitos y cada `tasks.md` descompone trabajo futuro sin ampliar alcance.
6. C4 gobierna ranking/contenido; E-3 gobierna el snapshot sintético; `CONTROL/ACTIVE` será la única autoridad runtime de activación.

## Mapa por workstream contractual

Los rótulos Rol 1–4 y sus ramas identifican workstreams de Specs. El ownership humano se fija en [DEC-022](./DECISIONES_SUPUESTOS_PREGUNTAS.md#decisiones).

| Workstream / rama | Alcance contractual | Produce | Consume | Dependencias de entrada |
|---|---|---|---|---|
| Producto / coordinación | Specs y gates | `PROD-*` | C0–C4 | fuente + adenda/DEC-023 |
| Rol 1 / `datos` | datos, motor, contexto y normalización de expediente | C1, C2 v2 | C0 v2 | E-3 sintético o expediente inicial completo |
| Rol 2 / `api` | API, ranking, GenAI, tracking y AWS | C3 2.0.0, snapshots, tracking | C0, C1, C2, C4 | gate C2 y stubs/C4 |
| Rol 3 / `front` | PWA por etapas | PWA y evidencia UX | C3 `/api/v2`, C4 | mocks C3 v2 |
| Rol 4 / `contenido` | mapeo, copy, demo y pitch | C0 v2, C4 | requisitos/adenda/privacidad | plantilla vacía; nunca respuestas |

## Plazos contractuales

| Contrato | Productor | Consumidores | Entrega acordada | Cambio compatible |
|---|---|---|---|---|
| C0 v2 | Rol 4 | Roles 1 y 2 | Día 1, 14:00 | revisión de privacidad/Integra; `permitido_llm` no habilita |
| C1 | Rol 1 | Rol 2 | stub Día 1, 14:00; completo noche | invariantes resultado/nivel/acceso |
| C2 v2 | Rol 1 | Rol 2 | Día 2, 12:00 | expediente/páginas/etapas; nunca amplía `LlmContextV1` |
| C3 2.0.0 | Rol 2 | Rol 3 | mocks Día 1, 11:00 | única base `/api/v2`, sin alias legacy |
| C4 | Rol 4 | Roles 2 y 3 | v1 Día 1 noche; final Día 2, 18:00 | nuevo bundle/versión/hash; no decide gate/elegibilidad |

## Gates y bloqueos

Orden de alta nueva: privacidad y fixture sintético → adenda/DEC-023 → C0 v2 → expediente C2 v2 con `INSCRIPCION_INICIAL=COMPLETA` → normalización/motor C1 → C3 `/api/v2` → ranking U/B/V → allowlist `LlmContextV1` → GenAI/plantilla → frontend/E2E. Página 3 permanece `NO_DISPONIBLE_AUN`, luego se habilita y completa en el mismo expediente al concretar matrícula.

RSH complementa/corrobora; nunca satisface el gate. Sin RSH, el alta persiste y las reglas dependientes quedan `INDETERMINADO`. Una discrepancia produce `RSH_STATUS_MISMATCH` sin sobreescritura.

E-3 es un camino separado para el snapshot sintético Demo. No representa una nueva postulación y sus 23 CSV no sustituyen la ficha.

Un gate falla ante: borrador/no ficha/request funcionalmente vacío; página 3 anticipada u omitida tras matrícula; datos reales/campos prohibidos; `UNKNOWN` convertido a falso/cero; contrato divergente; elegibilidad/ranking por LLM; umbral normativo hardcodeado; body en logs; o autoridad activa distinta de `CONTROL/ACTIVE`.

Si un bloqueo supera 30 minutos, se acuerda un mock/adaptador en el borde. No se crea contrato paralelo. Toda divergencia se registra como `DEC-*` y se resuelve primero en autoridad documental.

Puntos diarios: **10:00** acuerdos/contratos; **14:00** integración; **19:00** demo interna y evidencia.
