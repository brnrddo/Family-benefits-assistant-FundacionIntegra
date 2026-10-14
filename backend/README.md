# Backend

## Objetivo

Implementar el motor de reglas determinista y trazable, la API y el registro de conversaciones/KPI. La integración con Bedrock pertenece exclusivamente a `ia/`.

- **Dueño:** Ingeniería en Computación.
- **Colaboradores:** Ingeniería Mecánica entrega loader, características, acceso, prioridad y QA; Ingeniería Eléctrica consume la API.

## Entradas y salidas

**Entradas:** base derivada de los CSV canónicos, catálogo y reglas, características calculadas, estados de acceso, prioridad y textos validados.

**Salidas:** evaluaciones `SI | NO | INDETERMINADO` con traza, endpoints JSON, datos faltantes, preguntas, oportunidades ordenadas, métricas agregadas y contexto mínimo para la capa de redacción.

## Dependencias y límites

Depende del contrato de `data/` y `database/`; publica un contrato estable para `frontend/` y entrega a `ia/` el contexto mínimo acordado. `ia/` aplica el filtro canónico antes de cualquier envío a Bedrock. Hasta elegir stack no se crea scaffolding.

No colocar aquí componentes visuales, CSV canónicos, credenciales, dumps, adaptadores de Bedrock, prompts, otro filtro previo al modelo ni lógica que permita a un LLM decidir elegibilidad o prioridad.

Contexto: [especificación](../docs/especificacion/PROYECTO_3_ESPECIFICACION_v2.md), [roles](../docs/equipo/ROLES_Y_RESPONSABILIDADES.md) y [estructura](../docs/arquitectura/ESTRUCTURA_REPOSITORIO.md).
