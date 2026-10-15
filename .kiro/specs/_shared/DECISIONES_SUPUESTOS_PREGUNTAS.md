# Decisiones, supuestos y preguntas

Origen: diseño aprobado de coordinación, cuyo artefacto de trabajo permanece local y no se enlaza desde el repositorio. Los tipos se mantienen separados. Responsable de registrar evidencia: dueño indicado; coordinación aprueba cambios.

## Decisiones

| ID | Decisión | Responsable | Estado / verificación |
|---|---|---|---|
| DEC-001 | Fuente original inmutable; C0–C4 son interfaces únicas. | Coordinación | APROBADA; revisión de diffs. |
| DEC-002 | Stack futuro: Python/FastAPI/Pydantic/Mangum, React/Vite/TypeScript/Tailwind/Workbox y CDK Python. | Roles 2 y 3 | APROBADA; versiones se fijarán al implementar. |
| DEC-003 | Cognito es obligatorio en cloud; sin auth solo loopback. | Rol 2 | APROBADA; smoke test pendiente. |
| DEC-004 | JWT y tabla de scopes autorizan; grupos no sustituyen tenant. | Rol 2 | APROBADA; pruebas futuras. |
| DEC-005 | S3 canónico, DynamoDB serving blue/green; DuckDB/SQLite solo local; Athena solo analítico. | Roles 1 y 2 | APROBADA; AWS no verificado. |
| DEC-006 | Elegibilidad pertenece al bundle E-3, ranking/contenido a C4 y `CONTROL/ACTIVE` es única autoridad runtime con seis campos indivisibles. | Roles 1, 2 y 4 | APROBADA; pruebas transaccionales futuras. |
| DEC-007 | Dos envelopes cerrados para Bedrock; filtro de payload integral. Textract usa contrato separado y asset sintético inventariado. | Rol 2 | APROBADA; pruebas SDK futuras. |
| DEC-008 | Asistente solo informa catálogo; consulta individual vuelve `REQUIRES_DETERMINISTIC_EVALUATION` sin Bedrock. | Rol 2 | APROBADA; adversariales futuros. |
| DEC-009 | Recuperación determinista es baseline; S3 Vectors candidato y otras alternativas RAG son excluyentes. | Rol 2 | APROBADA; benchmark pendiente. |
| DEC-010 | `content/i18n/es.json` es copy canónico importado directamente. | Roles 3 y 4 | APROBADA; validación futura. |
| DEC-011 | Demo: HTTP API y Amplify. Escala: REST regional + WAF y S3 + CloudFront OAC. | Rol 2 | APROBADA; cuenta no verificada. |
| DEC-012 | Demo no captura texto libre; offline solo sintético y deshabilitado en escala hasta aprobación. | Roles 2 y 3 | APROBADA; UX/pruebas futuras. |
| DEC-013 | Afiche manual baseline; Textract opcional; Bedrock multimodal deshabilitado hasta nueva decisión. | Roles 2 y 4 | APROBADA. |
| DEC-014 | LLM jamás decide elegibilidad; todo texto es referencial. | Todos | APROBADA; gate permanente. |
| DEC-015 | Cloud calcula con `SnapshotPartitionBuilder` por jardín: Inline Map Demo y Distributed Map Escala; Glue normaliza y Athena analiza. | Roles 1 y 2 | APROBADA; topologías no verificadas. |
| DEC-016 | Adopción retroactiva conserva avances, congela contratos y usa matriz de gaps/adaptadores trazados. | Todos | APROBADA; aplicación por rama futura. |
| DEC-017 | Procedencia del evento no equivale a disponibilidad; AWS requiere smoke test fechado. | Rol 2 | APROBADA; estados iniciales no verificados. |
| DEC-018 | Modelo configurable; selección por benchmark sintético. Retención no cambia sin aprobación. | Rol 2 | APROBADA; modelo/región pendientes. |
| DEC-019 | Polly/Translate SHOULD recuperables; Transcribe/AgentCore COULD con decisión y contrato nuevos. | Roles 2 y 4 | APROBADA; no verificados. |
| DEC-020 | S3 Tables solo analítica; Macie solo detecta; agentes AWS solo apoyan revisión/operación. | Rol 2 | APROBADA; fuera del núcleo Demo. |
| DEC-021 | Las rutas físicas del pedido son el contrato de navegación y prevalecen. Los nombres del árbol original son solo etiquetas conceptuales: `producto-brujula-familiar` → `apoyo-inteligente-familias/`; `rol-1-datos-motor` → `datos-motor-elegibilidad/`; `rol-2-api-priorizacion-genai` → `api-priorizacion-genai/`; `rol-3-frontend-pwa` → `frontend-pwa/`; `rol-4-producto-contenido-demo` → `producto-contenido-demo/`. Existe una sola tríada autoritativa por área, sin aliases ni duplicados. | Coordinación | APROBADA por decisión explícita de revisión; comprobar enlaces desde `INDICE.md`. |
| DEC-022 | Los rótulos Rol 1–4 y las ramas de las Specs son workstreams contractuales, no equivalencias uno-a-uno con las disciplinas. El ownership humano se resuelve por componente: Computación aprueba `backend/` (motor/API/tracking) e `ia/`; Mecánica, `data/`, `database/` y futuras áreas loader/features/access/priority/QA; Eléctrica, `frontend/` y despliegue; Recursos Naturales, `docs/producto/`, contenido, privacidad, pruebas manuales y pitch. C0–C4 conservan un significado único: C0 mapeo de ficha, C1 salida de motor/acceso, C2 contexto familiar, C3 API y C4 contenido/configuración. Los handoffs históricos rotulados C1–C6 en la fuente funcional se traducen así: datos tipados alimentan C1/C2 sin contrato adicional; salida del motor y acceso forman C1; prioridad consume C1/C2/C4 y se publica por C3; API es C3; producto/lenguaje es C4; PWA/despliegue es un entregable, no otro contrato. | Coordinación y dueños de componente | APROBADA para reconciliar la reorganización por componentes con DEC-021 sin duplicar tríadas ni contratos. |

## Supuestos

| ID | Supuesto | Responsable | Estado / método de resolución |
|---|---|---|---|
| SUP-001 | E-3 es sintético; no autoriza material real. | Rol 1 | VIGENTE; contrastar documentación local. |
| SUP-002 | Snapshot demo `2026-10-13T23:59:59-03:00`, configurable. | Roles 1 y 2 | VIGENTE; prueba futura con reloj inyectado. |
| SUP-003 | Ramas `datos`, `api`, `front`, `contenido`; Rol 2 usa `api`. | Coordinación | VIGENTE; verificar rama antes de trabajar. |
| SUP-004 | Adopción real agrega consentimiento, región, retención, recuperación y dispositivos. | Integra/coordinación | PENDIENTE; aprobación de gobierno. |
| SUP-005 | Observaciones cualitativas usan enums; texto libre queda fuera. | Roles 2 y 4 | VIGENTE; nueva decisión para cambiarlo. |

## Preguntas abiertas

| ID | Pregunta | Responsable | Estado / método de resolución |
|---|---|---|---|
| PREG-001 | ¿Qué región, modelos y Guardrail funcionan en la cuenta? | Rol 2 | ABIERTA; enumeración e invocación sintética fechada. |
| PREG-002 | ¿Qué servicios, cuotas, permisos y bootstrap están habilitados? | Rol 2 | ABIERTA; smoke tests sanitizados. |
| PREG-003 | ¿Integra aprobará consentimiento, finalidades y retención? | Integra | ABIERTA; sin aprobación no hay datos reales. |
| PREG-004 | ¿Baseline determinista basta o S3 Vectors mejora métricas frente a alternativas? | Rol 2 | ABIERTA; benchmark sintético comparativo. |
| PREG-005 | ¿Se autorizan observaciones cualitativas y qué redacción requieren? | Integra | ABIERTA; por defecto no. |
| PREG-006 | ¿Qué persistencia de dispositivo se aprueba? | Integra/Rol 3 | ABIERTA; memoria y escala sin cola. |
| PREG-007 | ¿Qué umbral y reglas de supresión KPI se aprueban? | Integra/Rol 2 | ABIERTA; Demo rotulada. |
| PREG-008 | ¿Textract alcanza calidad suficiente en afiches sintéticos? | Roles 2 y 4 | ABIERTA; prueba con inventario sintético. |
| PREG-009 | ¿Qué voces e idiomas cumplen accesibilidad y revisión humana? | Roles 2 y 4 | ABIERTA; fallback texto/español. |
| PREG-010 | ¿Hay consentimiento, redacción y retención para Transcribe? | Integra | ABIERTA; sin sí explícito no hay endpoint. |
| PREG-011 | ¿AgentCore mejora el asistente sin ampliar acceso? | Rol 2 | ABIERTA; comparación; nunca motor. |
