# Índice de Specs Kiro

Punto único de entrada al **baseline documental**. No afirma que aplicación, infraestructura, contratos runtime o pruebas estén implementados.

## Orden de lectura

- **Equipo:** este índice → [fuente funcional](../../docs/especificacion/PROYECTO_3_ESPECIFICACION_v2.md) → [adenda de ingreso](../../docs/especificacion/ADENDA_FICHA_INGRESO.md) → [DEC-023](./_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md#decisiones) → [spec maestro](./apoyo-inteligente-familias/requirements.md) → [privacidad](../../docs/PRIVACIDAD_DEMO.md) → [arquitectura](../../docs/ARQUITECTURA_AWS.md) → rol.
- **Rol 1:** [requirements](./datos-motor-elegibilidad/requirements.md) → [design](./datos-motor-elegibilidad/design.md) → [tasks](./datos-motor-elegibilidad/tasks.md) → C0/C1/C2.
- **Rol 2 (`api`):** [requirements](./api-priorizacion-genai/requirements.md) → [design](./api-priorizacion-genai/design.md) → [tasks](./api-priorizacion-genai/tasks.md) → C0–C4.
- **Rol 3:** [requirements](./frontend-pwa/requirements.md) → [design](./frontend-pwa/design.md) → [tasks](./frontend-pwa/tasks.md) → C3/C4.
- **Rol 4:** [requirements](./producto-contenido-demo/requirements.md) → [design](./producto-contenido-demo/design.md) → [tasks](./producto-contenido-demo/tasks.md) → C0/C4.
- **Revisión:** [decisiones/supuestos/preguntas](./_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md) → [dependencias/gates](./_shared/DEPENDENCIAS.md) → contratos/ejemplos → tareas/evidencia.

Guía para novatos: [`GUIA_KIRO_EQUIPO.md`](../../docs/GUIA_KIRO_EQUIPO.md). Glosario: [`GLOSARIO.md`](./_shared/GLOSARIO.md).

## Nombres conceptuales y rutas físicas

[DEC-021](./_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md#decisiones) fija las rutas físicas como contrato de navegación. Los nombres conceptuales son solo etiquetas visibles y no son carpetas ni aliases.

| Nombre conceptual | Única ruta física autoritativa |
|---|---|
| `producto-brujula-familiar` | [`apoyo-inteligente-familias/`](./apoyo-inteligente-familias/requirements.md) |
| `rol-1-datos-motor` | [`datos-motor-elegibilidad/`](./datos-motor-elegibilidad/requirements.md) |
| `rol-2-api-priorizacion-genai` | [`api-priorizacion-genai/`](./api-priorizacion-genai/requirements.md) |
| `rol-3-frontend-pwa` | [`frontend-pwa/`](./frontend-pwa/requirements.md) |
| `rol-4-producto-contenido-demo` | [`producto-contenido-demo/`](./producto-contenido-demo/requirements.md) |

## Artefactos, dueños y estado

| Artefacto | Dueño | Consumidores | Rama | Estado | Evidencia de terminado |
|---|---|---|---|---|---|
| [Spec maestro](./apoyo-inteligente-familias/requirements.md) | coordinación | Roles 1–4 | baseline | DOCUMENTADO | triada, IDs PROD y trazabilidad |
| [Adenda de ficha de ingreso](../../docs/especificacion/ADENDA_FICHA_INGRESO.md) | coordinación/Integra | Roles 1–4 | baseline | DOCUMENTADA; validaciones humanas pendientes | expediente único, gate y `PENDIENTE_VALIDACION_INTEGRA` |
| [Rol 1 Datos/motor](./datos-motor-elegibilidad/requirements.md) | Rol 1 | Rol 2 | `datos` | DOCUMENTADO; implementación pendiente | C1/C2, 10.000 resultados y pruebas futuras |
| [Rol 2 API/GenAI/AWS](./api-priorizacion-genai/requirements.md) | Rol 2 | Rol 3 y coordinación | `api` | DOCUMENTADO; implementación/AWS pendientes | C3, seguridad, ranking y smoke tests futuros |
| [Rol 3 PWA](./frontend-pwa/requirements.md) | Rol 3 | tía/Integra | `front` | DOCUMENTADO; implementación pendiente | seis vistas, 360 px y pruebas futuras |
| [Rol 4 Contenido/demo](./producto-contenido-demo/requirements.md) | Rol 4 | Roles 1–3/jurado | `contenido` | DOCUMENTADO; contenido pendiente | C0/C4, revisión humana y demo futura |
| [Privacidad](../../docs/PRIVACIDAD_DEMO.md) | coordinación/Rol 4 | todos | baseline | DOCUMENTADA | cuatro clases, allowlist y prohibiciones |
| [Arquitectura AWS](../../docs/ARQUITECTURA_AWS.md) | Rol 2 | todos | `api` | DOCUMENTADA; AWS NO_VERIFICADO | matriz, perfiles, diagrama y evidencia futura |
| [Guía Kiro](../../docs/GUIA_KIRO_EQUIPO.md) | coordinación | equipo | baseline | DOCUMENTADA | recorrido por rol y adopción retroactiva |

## Mapa de autoridad

1. [Fuente funcional original](../../docs/especificacion/PROYECTO_3_ESPECIFICACION_v2.md), inmutable.
2. [Adenda de Ficha de Ingreso](../../docs/especificacion/ADENDA_FICHA_INGRESO.md) y [DEC-023](./_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md#decisiones), aclaración autoritativa del expediente/gate.
3. [Requirements maestro](./apoyo-inteligente-familias/requirements.md), interpretación con `PROD-*`.
4. C0–C4, única autoridad entre roles. Para altas nuevas: C0 v2/ficha → C2 v2/C3 2.0.0 → gate → motor; RSH nunca sustituye el gate.
5. `design.md` satisface requisitos; `tasks.md` descompone sin agregar alcance.
6. Futuro runtime: bundle E-3 solo para el snapshot sintético, C4 para ranking/contenido y DynamoDB `CONTROL/ACTIVE` para los seis campos activos.

## Contratos C0–C4

| Contrato | Productor | Consumidores | Plazo | Cambio compatible / evidencia |
|---|---|---|---|---|
| [C0 Mapeo ficha v2](./_shared/contracts/C0-mapeo-ficha.schema.json) ([ejemplo](./_shared/contracts/examples/C0-normalizado.md); [`content/mapeo_ficha.csv`](../../content/mapeo_ficha.csv)) | Rol 4 | Roles 1/2 | Día 1 14:00 | gate documental de altas; versión + revisión privacidad; `permitido_llm` no habilita |
| [C1 Salida motor](./_shared/contracts/C1-salida-motor.schema.json) ([ejemplo](./_shared/contracts/examples/C1-salida-motor.md)) | Rol 1 | Rol 2 | stub Día 1 14:00; completo noche | schema/hash; no alterar resultado |
| [C2 Contexto/expediente v2](./_shared/contracts/C2-contexto-familia.schema.json) ([ejemplo](./_shared/contracts/examples/C2-contexto-familia.md)) | Rol 1 | Rol 2 | Día 2 12:00 | tres páginas/dos etapas; ampliar C2 no amplía `LlmContextV1` |
| [C3 API 2.0.0 `/api/v2`](./_shared/contracts/C3-api.openapi.yaml) ([flujos](./_shared/contracts/examples/C3-flujos-api.md)) | Rol 2 | Rol 3 | mocks Día 1 11:00 | único archivo/base; migración in-place DEC-023, sin aliases |
| [C4 Contenido](./_shared/contracts/C4-contenido-manifest.schema.json) ([ejemplo](./_shared/contracts/examples/C4-manifest.md)) | Rol 4 | Roles 2/3 | v1 noche; final Día 2 18:00 | nuevo bundle/versión/hash; ranking §8 completo, seis clases obligatorias y accesibilidad condicionada |

Schemas de seguridad: [LlmContextV1](./_shared/contracts/schemas/LlmContextV1.schema.json), envelopes **internos, nunca requests públicos**, de [generación familiar](./_shared/contracts/schemas/FamilyGenerationRequestV1.schema.json) y [asistente](./_shared/contracts/schemas/AssistantRequestV1.schema.json), además de [afiche Textract](./_shared/contracts/schemas/TextractFlyerRequestV1.schema.json) y [error](./_shared/contracts/schemas/ErrorResponse.schema.json). C3 define requests públicos mínimos y una respuesta funcional cerrada por ruta.

## Integración, AWS y gates

- **10:00:** acuerdos del día, privacidad y contratos.
- **14:00:** integrar lo disponible; mocks/adaptadores si un bloqueo supera 30 minutos.
- **19:00:** demo interna de cinco minutos y evidencia.

Perfiles: **Demo AWS viable** condicionada a smoke tests y fallback loopback; **Escala Integra** condicionada a gobierno/seguridad. DuckDB solo local. Gates: sintéticos/privacidad; C0–C4; elegibilidad y U/B/V sin LLM; parámetros versionados; `CONTROL/ACTIVE` único; evidencia AWS fechada.

## Si hay contradicción

Detenga la tarea. No acomode silenciosamente el contrato al código. Registre `DEC-*`, `SUP-*` o `PREG-*` en el [registro compartido](./_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md), asigne responsable y evidencia, corrija primero fuente interpretada/contrato y luego consumidores. Preserve avances conformes mediante un adaptador temporal probado si el equipo lo aprueba.
