# Dependencias, ownership e integración

## Autoridades

1. [`PROYECTO_3_ESPECIFICACION_v2.md`](../../../PROYECTO_3_ESPECIFICACION_v2.md) es la fuente funcional original e inmutable.
2. El [spec maestro](../apoyo-inteligente-familias/requirements.md) interpreta la fuente con requisitos `PROD-*`.
3. Los contratos de [`contracts/`](./contracts/) son la única autoridad de interfaces C0–C4.
4. Cada `design.md` decide cómo satisfacer requisitos; cada `tasks.md` descompone trabajo futuro sin ampliar alcance.
5. C4 gobierna ranking/contenido; el bundle público E-3 gobierna elegibilidad; `CONTROL/ACTIVE` será la única autoridad runtime de activación.

## Mapa por rol

| Rol / rama | Ownership futuro | Produce | Consume | Dependencias de entrada |
|---|---|---|---|---|
| Producto / coordinación | Specs y gates | `PROD-*` | C0–C4 | fuente funcional |
| Rol 1 / `datos` | `backend/app/{loader,db,engine,access,context}`, `backend/tests` | C1, C2 | C0 | E-3 público, C0 |
| Rol 2 / `api` | `backend/app/{api,auth,priority,genai,tracking}`, `infrastructure/` | C3, snapshots, tracking | C0, C1, C2, C4 | stubs C1/C2 y C4 |
| Rol 3 / `front` | `frontend/` | PWA y evidencia UX | C3, C4 | mocks C3 |
| Rol 4 / `contenido` | `content/`, demo, pitch | C0, C4 | requisitos funcionales | fuente, privacidad |

## Plazos contractuales

| Contrato | Productor | Consumidores | Entrega acordada | Cambio compatible |
|---|---|---|---|---|
| C0 | Rol 4 | Roles 1 y 2 | Día 1, 14:00 | agregar valor solo con versión y revisión de privacidad |
| C1 | Rol 1 | Rol 2 | stub Día 1, 14:00; completo noche | campos opcionales solo si schema/version lo permite |
| C2 | Rol 1 | Rol 2 | Día 2, 12:00 | nunca ampliar `LlmContextV1` implícitamente |
| C3 | Rol 2 | Rol 3 | mocks Día 1, 11:00 | cambios incompatibles usan `/api/v2` |
| C4 | Rol 4 | Roles 2 y 3 | v1 Día 1 noche; final Día 2, 18:00 | nuevo bundle, versión y hash |

## Gates y bloqueos

Orden: privacidad/fixtures → contratos → motor → API/auth/snapshot → frontend contra mocks → contenido validado → E2E/IaC. Un gate falla si hay datos reales/campos prohibidos, elegibilidad o ranking decidido por LLM, contrato divergente, umbral normativo hardcodeado o autoridad activa distinta de `CONTROL/ACTIVE`.

Si un bloqueo supera 30 minutos, se acuerda un mock o adaptador temporal en el borde del contrato. No se crea un contrato paralelo. Toda divergencia se registra como `DEC-*` y se resuelve primero en la autoridad documental.

Puntos diarios: **10:00** acuerdos y contratos; **14:00** integración con lo disponible; **19:00** demo interna de cinco minutos y evidencia.
