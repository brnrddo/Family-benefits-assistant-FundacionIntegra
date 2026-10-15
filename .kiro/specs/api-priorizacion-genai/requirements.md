# Requisitos — Rol 2 API, priorización, GenAI y AWS

Vínculos: [PROD](../apoyo-inteligente-familias/requirements.md), [C0–C4](../_shared/contracts/), [decisiones](../_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md).

## MUST

- **API-001 — Primer desbloqueo (PROD-005; C3).** WHEN inicia implementación, Rol 2 MUST publicar primero mocks de todos los endpoints C3 dentro de la primera hora, usando stubs sintéticos C1/C2/C4, para desbloquear Rol 3.
- **API-002 — Ranking U/B/V (PROD-002; C1,C2,C4; DEC-006).** WHEN recibe oportunidad, THE SYSTEM MUST calcular U/B/V, puntaje de oportunidad y prioridad familiar únicamente desde el C4 cerrado: pesos de ejes/componentes, señales y ventanas de urgencia, anualización/divisor/equivalencias/medianas de beneficio, bandas de vulnerabilidad, pesos de estado, bonus y top/ventana de familia; MUST excluir señales desconocidas, marcar B estimado y desempatar por puntaje/U/B descendente e ID ascendente.
- **API-003 — Inmutabilidad de decisión (PROD-002; C1).** THE SYSTEM MUST NOT permitir que texto generado modifique elegibilidad, nivel, acceso, U/B/V o posición.
- **API-004 — C3 completo y cerrado (PROD-005; C1,C3).** THE SYSTEM MUST implementar `/api/v1`, endpoints, requests públicos mínimos, respuestas funcionales específicas sin objetos abiertos ni markup generativo, cursores, límites, `request_id`, snapshot/hashes, idempotencia y error cerrado exactamente según OpenAPI. C3 MUST rechazar combinaciones incoherentes: `SI` sin nivel o con acceso indeterminado/no aplicable; `INDETERMINADO` sin nivel nulo/acceso homónimo; y `NO|NO_APLICA` sin nivel nulo/acceso `NO_APLICA`.
- **API-005 — Authn/authz (PROD-004/009; C3; DEC-003/004/011).** BEFORE una ruta cloud, THE SYSTEM MUST validar access token Cognito (`iss/exp/nbf/token_use/client_id/scopes`) y scope DynamoDB; MUST rechazar ID token y ocultar recursos fuera de scope con 404.
- **API-006 — Snapshot activo (PROD-010; C1,C4; DEC-006/015).** WHEN atiende o publica, THE SYSTEM MUST usar solo `CONTROL/ACTIVE` con seis campos, lectura consistente y activación/rollback transaccional por generación.
- **API-007 — Frontera pública y envelopes internos (PROD-004/012; C0,C1,C2,C3,C4; DEC-007).** Public C3 requests MUST accept only authorized benefit IDs or a filtered question and MUST NOT accept context, catalog, prompt, prompt version or operation from the client. BEFORE Bedrock, THE SYSTEM MUST load authorized C1/C2/C4, build `LlmContextV1` by allowlist and one of two internal closed envelopes, filter the full boto3 payload and apply Guardrails INPUT.
- **API-008 — Salida segura/fallback (PROD-008/011/012; C3,C4; DEC-014/018).** AFTER Converse, THE SYSTEM MUST validar JSON/schema/grounding, Guardrails OUTPUT y reglas de negocio; el mensaje imprimible MUST ser `PrintableCard` estructurado sin HTML/CSS/handlers y sus citas MUST provenir de C4; cualquier fallo recuperable MUST descartar toda la salida y usar `TemplateProvider`.
- **API-009 — Solo dos operaciones de texto (PROD-012; C3).** THE SYSTEM MUST limitar Bedrock a generación familiar y asistente de catálogo; consultas individuales al asistente MUST retornar `REQUIRES_DETERMINISTIC_EVALUATION` sin Bedrock.
- **API-010 — Tracking idempotente (PROD-006; C3; DEC-012).** WHEN registra conversación, THE SYSTEM MUST validar clave/body/snapshot, no aceptar notas libres Demo y no duplicar KPI.
- **API-011 — KPI y supresión (PROD-006; C3,C4).** WHEN calcula KPI, THE SYSTEM MUST hacerlo reproducible por familia/período/snapshot, devolver divisor cero como null y aplicar supresión/complementaria configurable en Escala.
- **API-012 — Pipeline blue/green (PROD-009/010; C1,C4; DEC-015).** WHEN recalcula, THE SYSTEM MUST usar `SnapshotPartitionBuilder` por jardín, validar particiones/hashes/conteos y activar solo tras smoke test; fallo conserva activo.
- **API-013 — Observabilidad privada (PROD-004/009).** THE SYSTEM MUST registrar métricas/códigos/latencia/request ID sin body, prompt, respuesta, ID completo, token, account ID ni endpoint privado.
- **API-014 — Evidencia AWS (PROD-009; DEC-017/018).** A service/model/region MUST remain `NO_VERIFICADO` until a dated synthetic smoke test records region, operation and sanitized outcome.
- **API-019 — Arranque y README operativo (PROD-014; §17).** BEFORE cierre, Rol 2 MUST provide one command equivalent to `make setup && make run` and MUST coordinate a README future that documents architecture, execution and data assumptions, including `usar_ventana=false`; the command MUST load data and start backend/frontend without undocumented manual steps.

## SHOULD

- **API-015 — RAG y caché (PROD-012; DEC-009).** THE SYSTEM SHOULD use deterministic catalog retrieval first and cache by filtered envelope/version hashes; vector alternatives SHOULD be mutually exclusive and benchmarked.
- **API-016 — Accesibilidad recuperable (PROD-012; C4; DEC-019).** Polly/Translate SHOULD remain disabled by default; IF C4 enables either capability, THE SYSTEM MUST require `VERIFICADO_EN_CUENTA`, a sanitized smoke-test evidence ID, closed voice/language allowlists and fallback labels, and MUST send only safe postvalidated text or fall back to text/canonical Spanish.

## COULD

- **API-017 — Afiche sintético (PROD-013; C3; DEC-013).** IF an inventoried synthetic asset passes hash/MIME/size/dimension checks, THE SYSTEM COULD call Textract and create only a human-review draft.
- **API-018 — Opciones de escala (DEC-019/020).** AgentCore, S3 Tables, Macie and AWS review agents COULD be evaluated within their documented limits, never as eligibility dependencies.

## Fuera de alcance

Datos reales, API cloud anónima, WhatsApp Business, HTML/CSS generado por LLM, Bedrock multimodal, Transcribe actual, publicación automática de afiches, cambio de retención sin aprobación y cualquier decisión generativa de derechos.
