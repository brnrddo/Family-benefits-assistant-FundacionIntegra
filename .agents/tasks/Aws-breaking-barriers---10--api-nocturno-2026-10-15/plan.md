# Plan de implementación — Rol 2 API / priorización / filtro GenAI (trabajo nocturno)

Rama `api` (checkout actual, NO worktree, confirmado por `git status`). Motor Rol 1 presente en `backend/app/engine/service.py`. Base verde: `py -3.11 -m pytest` = 90 tests OK.

## Contexto verificado durante la exploración

- **Intérprete de pruebas:** el `python` por defecto del shell es un venv del sandbox SIN pytest. Usar siempre `py -3.11 -m pytest` desde `backend/` (confirmado: 90 passed). `pip`/`py -3.11` ya tienen `pytest 9.1.1`, `fastapi 0.136.3`, `httpx 0.28.1`, `jsonschema 4.26.0`. `requirements.txt` fija `fastapi==0.115.6`, `uvicorn==0.34.0`, `boto3==1.35.90`; `requirements-dev.txt` fija `pytest==8.3.4`, `ruff==0.8.6`. Hay que **añadir** `httpx` y `jsonschema` fijados a dev-requirements (TestClient + validación de contrato en tests).
- **C3 es la autoridad** (`.kiro/specs/_shared/contracts/C3-api.openapi.yaml`, OpenAPI 3.1, `servers: /api/v1`, 12 operaciones). Disclaimer `const` EXACTO (con tildes): `Orientación referencial; no determina derechos. Confirmar en la institución.`
- **C4 es la autoridad numérica del ranking** (`C4-contenido-manifest.schema.json` → `ranking.{axis_weights,urgency,benefit_impact,vulnerability,opportunity_score,family_priority}`). NO existe `content/` todavía → el plan crea un bundle C4 provisional marcado como tal.
- Motor existente a **reutilizar, no reimplementar**: `engine/service.py` (`evaluar_familia`, `precalcular_todo`, `beneficios`), `engine/model.py` (`Tri`, `Nivel`, `ResultadoBeneficio`), `access/model.py` (`EstadoAcceso`), `context/contexto_familia.py` (`construir_contexto`), `context/context_filter.py` (`filtrar_para_llm`, `contiene_campo_prohibido`), `genai/provider.py` (`LLMProvider`, `StubProvider`, `BedrockProvider`, `get_provider`), `config.py`.
- NO tocar `backend/app/{engine,access,context,loader,db}` salvo para importarlos. NO modificar specs/contratos/data.

## Mapeo de los 12 endpoints C3 → routers (todos bajo `/api/v1`)

| # | operationId | método + ruta | router | scope | respuesta (envelope) |
|---|---|---|---|---|---|
| 1 | listJardines | GET /jardines | jardines | jardines:read | JardinListEnvelope |
| 2 | listFamiliasByJardin | GET /jardines/{id}/familias | jardines | familias:read | FamiliaListEnvelope |
| 3 | getFamilia | GET /familias/{id} | familias | familias:read | FamiliaDetailEnvelope |
| 4 | getContextoFamilia | GET /familias/{id}/contexto | familias | familias:read | FamiliaContextEnvelope |
| 5 | listOportunidades | GET /familias/{id}/oportunidades | familias | familias:read | OpportunityListEnvelope |
| 6 | createGuion | POST /familias/{id}/guion | genai | genai:write | ScriptGenerationEnvelope |
| 7 | createMensaje | POST /familias/{id}/mensaje | genai | genai:write | MessageGenerationEnvelope |
| 8 | createConversacion | POST /familias/{id}/conversaciones | tracking | conversaciones:write | ConversationEnvelope (201) |
| 9 | createPreevaluacion | POST /familias/nueva/preevaluacion | familias | familias:write | PreevaluationEnvelope |
| 10 | getKpi | GET /kpi | kpi | kpi:read | KpiEnvelope |
| 11 | askCatalogAssistant | POST /asistente | genai | asistente:write | AssistantEnvelope |
| 12 | ingestSyntheticFlyer | POST /catalogo/ingesta-afiche | catalogo | catalogo:admin | FlyerDraftEnvelope |

Nota de ruteo: declarar `/familias/nueva/preevaluacion` ANTES de `/familias/{id}` para que FastAPI no capture `nueva` como `{id}` (o usar un prefijo distinto). `Id` pattern `^[A-Z0-9][A-Z0-9_-]*$` haría que `nueva` (minúscula) no valide como `{id}`, pero el orden explícito evita ambigüedad.

## Algoritmo U/B/V (§8) y de dónde salen los números

Todo número de negocio sale de `ranking.*` del bundle C4. CERO hardcode. Agregado por oportunidad: `score = axis_weights.u*U + axis_weights.b*B + axis_weights.v*V` (ponderado), más el peso de estado y bonus de `opportunity_score`.

- **U (urgencia)** `[0,1]`: `aggregation=MAX` sobre señales activas (`recent_emergency`, `newborn_expiry`, `therapy_document_expiry`, `limited_quota`, `food_insecurity`, `precarious_housing`, `application_windows`); `use_window=false` en Demo (sin ventanas temporales → usar `default_score` cuando no hay señal). Señales desconocidas/no derivables NO entran.
- **B (beneficio/impacto)** `[0,1]`: monto anualizado = `monto × annualization_multipliers[periodicidad]`; servicios usan `service_equivalences`; proporción sobre ingreso mensual del hogar (mediana por jardín `garden_income_medians`, si no `default_monthly_household_income`), saturando a 1 en `max_income_share_for_full_score`. Si el monto es estimado por mediana/equivalencia → marcar `benefit_estimated=true`.
- **V (vulnerabilidad)** `[0,1]`: suma ponderada de `component_weights` sobre componentes conocidos (`rsh_scores`, `income_band_scores`, `health_coverage_scores`, `cse`, `female_head_program_score`, `possible_child_disability_score`); `unknown_signals_excluded=true` → los componentes sin dato se excluyen del numerador Y del denominador (renormalizar por pesos presentes).
- **Prioridad familiar:** top `family_priority.top_opportunity_count` oportunidades; `× vulnerability_multiplier`; `+ not_informed_bonus` si no conversada; `+ new_family_bonus` si edad < `new_family_max_age_days`.
- **Desempate:** `score` desc, `U` desc, `B` desc, `benefit_id` asc.
- **Config inválida** (suma U/B/V ≠ 1 ± 1e-6, falta clase, mediana ausente sin default) → fallar cerrado al cargar C4.

## Filtro de allowlist y TemplateProvider

- `genai/llm_context.py`: construir `LlmContextV1` por **allowlist positiva** desde C1 + señales C2 autorizadas (reutiliza el espíritu de `context_filter.filtrar_para_llm`). Validar contra `LlmContextV1.schema.json` con `jsonschema`. Ejecutar `contiene_campo_prohibido` sobre el payload completo y FALLAR si aparece cualquier clave prohibida (nombre, RUT, folio, teléfono, dirección, nacionalidad, diagnóstico, QR). Beneficios → mapear a `benefits[]` con `benefit_id/result/level/access_state/...`.
- `genai/template_provider.py`: `TemplateProvider` determinista produce `ScriptContent`, `MessageContent` (con `PrintableCard`/`CARD_V1`, strings puros, citas tipadas desde C4, nunca HTML) y `AssistantEnvelope`, solo con campos permitidos. Postvalida longitudes/IDs/citas HTTPS.
- `BedrockProvider`: queda como stub con import perezoso de boto3 (ya existe); `/guion`, `/mensaje`, `/asistente` usan `TemplateProvider` por defecto (`provider: "PLANTILLA"`). `/asistente` detecta pregunta individual → `intent=REQUIRES_DETERMINISTIC_EVALUATION` sin Bedrock.

## Archivos a crear

- `backend/app/api/__init__.py`, `app.py` (crea FastAPI, monta routers, sirve el YAML C3 como OpenAPI y `/docs`, `/healthz`), `deps.py` (config E3_MOCK, snapshot/hashes constantes, auth stub por scope), `errors.py` (ErrorResponse cerrado + handlers 400/401/403/404/409/422/429/503), `models.py` (Pydantic de C3), `mock_data.py` (fixtures sintéticos rotulados).
- `backend/app/api/routers/{jardines,familias,genai,tracking,kpi,catalogo}.py`.
- `backend/app/priority/__init__.py`, `config.py` (carga/valida C4), `scoring.py` (U/B/V, agregación, desempates, prioridad familiar).
- `backend/app/genai/llm_context.py`, `template_provider.py`.
- `content/` bundle C4 provisional marcado PROVISIONAL (manifest + WEIGHTS/QUESTIONS/BENEFITS/PROMPT/ACCESSIBILITY/I18N).
- Tests en `backend/tests/`: `test_api_mocks.py`, `test_priority.py`, `test_genai_filter.py`, `test_api_runtime_flag.py`.
- Doc de avances: `.agents/tasks/.../AVANCES_ROL2.md`.

## Archivos a modificar

- `backend/requirements-dev.txt`: añadir `httpx==0.28.1`, `jsonschema==4.26.0` (fijados).
- `backend/README.md`: sección de arranque uvicorn para Rol 3.

## Plan de pruebas

- Mocks: cada ruta 2xx valida contra el schema C3 (jsonschema contra el YAML); coherencia (familias referencian jardines; oportunidades respetan invariantes `oneOf`); errores cerrados; disclaimer exacto; snapshot/hashes constantes.
- Ranking: cada eje, agregación, desempates, señales desconocidas, B estimado por mediana, config C4 inválida.
- Filtro: rechaza PII (varios adversariales), TemplateProvider valida contra schema C3, `PrintableCard` sin HTML, ningún log con cuerpos/prompts.
- Runtime flag: E3_MOCK=0 sin DB degrada a mocks con warning; nunca rompe.
- Verificación global: `py -3.11 -m pytest` desde `backend/` (no `python -m pytest`).

## Preguntas abiertas / ambigüedades del contrato (para la Fundación / Rol 4)

1. Mapeo de bandas: `Opportunity.result` solo admite `SI`/`INDETERMINADO`, pero `BenefitResult` admite además `NO`/`NO_APLICA`. Las oportunidades deben filtrar a solo `SI`/`INDETERMINADO`.
2. C4 real lo entrega Rol 4; el bundle provisional de pesos NO es autoridad final (documentarlo).
3. `vulnerability_signals.rsh_score/income_score` en `FamilyContextView` vs. bandas de C2: confirmar fórmula de normalización con Rol 1/Rol 4.
4. `last_health_control_date` y señales de vivienda no están en el dataset E-3 (ver `contexto_familia.py`); en mocks van sintéticas, en runtime quedan `null`/`missing_codes`.
5. Preevaluación: NO implementar lógica de ingreso mínimo ni gate nuevo (depende de la reunión); solo mock que respeta el contrato y `level=PRELIMINAR`.
