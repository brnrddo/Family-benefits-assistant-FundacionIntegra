# Diseño — Rol 2 API, priorización, GenAI y AWS

**Workstream contractual:** rama `api`; coordina C3, ranking, GenAI, tracking y arquitectura AWS. Según [DEC-022](../_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md#decisiones), Computación aprueba `backend/` e `ia/`, Mecánica la futura área `priority` y Eléctrica infraestructura/despliegue. Arquitectura transversal: [`ARQUITECTURA_AWS.md`](../../../docs/ARQUITECTURA_AWS.md). Privacidad: [`PRIVACIDAD_DEMO.md`](../../../docs/PRIVACIDAD_DEMO.md).

## Primer paso exacto

Al iniciar implementación, **antes de ranking, Bedrock o despliegue**, publicar mocks de los doce flujos C3 bajo `/api/v1` con stubs C1/C2/C4 totalmente sintéticos y snapshot/hashes constantes. Entregar OpenAPI al Rol 3 dentro de la primera hora. No esperar al motor.

## Autoridad C0–C4

| Contrato | Entrada/salida de Rol 2 | Autoridad y prohibición |
|---|---|---|
| C0 | entrada | clasificación; `permitido_llm` no habilita runtime |
| C1 | entrada | resultado/acceso/traza del Rol 1; Rol 2 no lo modifica |
| C2 | entrada | hechos/UI; nunca se envía completo a IA |
| C3 | salida | única API/mocks; OpenAPI versionada; mensajes imprimibles estructurados, nunca markup generativo |
| C4 | entrada | configuración numérica completa de §8, KPI, prompts, accesibilidad y copy; no contiene reglas de elegibilidad |

## Ranking y validación C4

Entrada: C1, acceso, señales C2 autorizadas y C4 validado. Salida: U/B/V `[0,1]`, puntaje, señales, `B_estimado`, posición, hashes y explicación determinista. C4 aporta sin números hardcodeados: pesos U/B/V; agregación, señales, umbrales, ventanas y score base de urgencia; anualización, divisor de impacto, equivalencias de servicios y medianas por jardín/default; ponderaciones y mapeos RSH/ingreso/señales de vulnerabilidad; pesos de los siete estados, bonus de acción y límite de pregunta resoluble; top, multiplicador V, bonus de no conversada/nueva y días de familia nueva. Desempate: puntaje, U y B descendentes; ID ascendente.

El futuro `python -m backend.app.contracts.validate_content --manifest content/manifest.yaml` valida schema, existencia/hash y unicidad de rutas, presencia de `WEIGHTS`, `QUESTIONS`, `BENEFITS`, `PROMPT`, `ACCESSIBILITY` e `I18N`, suma U/B/V con tolerancia `1e-6`, rangos/ventanas ordenados sin solape, IDs y referencias entre archivos, estados completos y activación accesible coherente. Configuración inválida detiene publicación. Esta materialización solo define la tarea; no crea el validador.

## API, auth y errores

C3 define doce flujos: jardines; familias por jardín; ficha; contexto minimizado; oportunidades; guion; mensaje; conversaciones; preevaluación; KPI; asistente; ingesta opcional. Cada ruta tiene request y respuesta funcional cerrados; no existen `data` o `items` arbitrarios. `BenefitResult` y `Opportunity` replican las invariantes C1: `SI` exige nivel no nulo y acceso compatible; `INDETERMINADO` exige `nivel=null` y acceso homónimo; `NO|NO_APLICA`, cuando el schema los admite, exige `nivel=null` y acceso `NO_APLICA`. La preevaluación enumera propiedades tipadas de ficha y no acepta un mapa EAV. JSON lógico ≤64 KiB, IDs/cursores/límites cerrados, campos extra rechazados. Cognito exige access token, `client_id` y scope; tabla Authorization restringe jardín/región/nacional. 400 JSON/MIME, 401 authn, 403 operación visible, 404 inexistente/fuera de scope, 409 idempotencia/snapshot/asset, 422 semántica/seguridad, 429 límite, 503 dependencia sin fallback.

## Snapshot y pipeline

`CONTROL/ACTIVE` contiene exactamente `snapshot_id`, `eligibility_bundle_hash`, `content_bundle_hash`, `content_version`, `published_at`, `generation`. Cada request lee una vez con consistencia fuerte. Activar/rollback valida destino y reemplaza seis campos en `TransactWriteItems` con condición de generación; carrera=`SUPERSEDED`. Pipeline: ingesta → validación → normalización → Map por jardín → validación global → smoke test verde → activación → evento. Inline 50 jardines Demo; Distributed hasta 1.200 Escala. Fallback cloud invoca la misma Lambda; DuckDB solo localhost.

## GenAI, tarjeta segura y caché

C3 separa la frontera pública de la interna. Guion/mensaje aceptan públicamente solo `benefit_ids` (1–3) existentes y autorizados; `/asistente`, solo `question`. Ningún cliente puede enviar contexto, catálogo, prompt, versión de prompt ni operación. El servidor carga C1 y C2 autorizados, recupera catálogo/prompts desde C4 y construye `FamilyGenerationRequestV1` o `AssistantRequestV1` como envelopes exclusivamente internos.

Flujo fijo: request público cerrado → carga C1/C2/C4 autorizada → envelope interno cerrado → filtro integral del payload boto3 → Guardrails INPUT → Converse → schema/grounding → Guardrails OUTPUT → postvalidación → caché. `FamilyGenerationRequestV1` cubre explicación/guion/mensaje; `AssistantRequestV1`, catálogo. `TemplateProvider` conserva HTTP 200 y warning ante fallos recuperables. Pregunta individual se detecta determinísticamente y no llama Bedrock. Logs no capturan texto.

La operación mensaje nunca solicita ni acepta HTML. Bedrock devuelve únicamente strings estructurados de `PrintableCard`; el servidor postvalida longitudes, IDs y grounding, y adjunta/contrasta cada `SourceCitation` con el catálogo C4 autorizado. C3 no transporta tags, atributos, CSS, handlers ni URLs activas fuera de citas HTTPS tipadas. Rol 3 renderiza `CARD_V1` mediante una plantilla React propia con escape normal; strings que parezcan `<script>`, handlers, CSS, URLs o markup malformado siguen siendo texto inerte. Guardrails no reemplaza schema, postvalidación ni render seguro.

Caché: SHA-256 del envelope filtrado + operación + versiones de prompt/catálogo/modelo/Guardrail/bundles; escritura condicional y comprobación explícita de expiración. RAG baseline léxico/determinista. S3 Vectors y alternativas excluyentes solo tras benchmark.

## Afiche, accesibilidad y observabilidad

`TextractFlyerRequestV1` no es envelope Bedrock. Solo ID/MIME/hash de asset sintético inventariado; backend valida objeto, firma, 1 B–5 MiB, 64–4096 px y ≤16 MP antes de Textract. Resultado siempre requiere revisión humana.

Polly/Translate empiezan deshabilitados. Una activación C4 exige estado `VERIFICADO_EN_CUENTA`, ID de evidencia sanitizada, al menos una voz/idioma permitido, límites y clave i18n de fallback; cambia versión/hash C4. Solo reciben texto postvalidado y fallan a texto/español. El validador C4 impide activar una capacidad incompleta.

CloudWatch futuro: API/errors/auth, Lambda/DynamoDB, caché, Bedrock/fallback/Guardrails, jobs, edad snapshot, tracking/KPI; alarmas sin PII. Cada smoke test cambia solo componente/región/operación probados. Estado actual de todo AWS: `NO_VERIFICADO`.
