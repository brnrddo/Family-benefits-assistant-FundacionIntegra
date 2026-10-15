# Diseño — Apoyo Inteligente para Familias

## Autoridad y enlaces

Este spec interpreta la [fuente inmutable](../../../docs/especificacion/PROYECTO_3_ESPECIFICACION_v2.md). No duplica la [arquitectura AWS](../../../docs/ARQUITECTURA_AWS.md), la [política de privacidad](../../../docs/PRIVACIDAD_DEMO.md), las [decisiones](../_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md) ni los [contratos](../_shared/contracts/). Ante contradicción, se detiene el cambio, se registra `DEC-*` y se corrige primero la autoridad.

## Usuarios y flujo

La tía es usuaria principal; la familia recibe orientación, no usa el MVP; Integra consume agregados. Para una alta nueva, el flujo obligatorio es C0 v2 → expediente C2 v2/C3 2.0.0 → páginas 1–2 `INSCRIPCION_INICIAL=COMPLETA` → normalización y C1 → ranking C4 → `LlmContextV1` → redacción opcional → conversación → KPI. Página 3 permanece visible como `MATRICULA=NO_DISPONIBLE_AUN`, se habilita por evento autorizado y completa el mismo `form_record_id`; una actualización permitida genera evaluación versionada. E-3 sigue un camino separado como snapshot sintético de Demo, no como alta nueva. Las capas de elegibilidad, acceso y U/B/V son deterministas. La IA solo redacta o explica y siempre puede degradar a plantilla.

Precedencia: la ficha inicial completa habilita el alta; RSH observado complementa o corrobora, su ausencia produce `INDETERMINADO` donde corresponda y una discrepancia `RSH_STATUS_MISMATCH` no sobreescribe lo declarado. Un borrador, expediente ausente o request funcionalmente vacío falla cerrado antes del motor. Página 3 no se exige para la primera preevaluación, pero omitirla impide `MATRICULA=COMPLETA` tras habilitación.

Invariantes: resultado ternario; bindings por la misma entidad; umbrales desde versión; toda la configuración numérica U/B/V y prioridad familiar desde C4 cerrado; snapshot/hash en lectura; `CONTROL/ACTIVE` único; C2 y respuestas usan vocabularios cerrados y C2 nunca se trata como LLM-safe; C3 público no acepta contexto/catálogo/prompt/PDF/PII; texto sin promesas; mensaje imprimible como `PrintableCard` estructurado y renderizado por plantilla propia, nunca HTML del modelo; WhatsApp solo vista previa/copiar; datos reales y sistemas estatales fuera.

## Demo e integración

Demo visible: jardín → familia priorizada → tres oportunidades/chips → detalle técnico → guion → vista previa de mensaje → marcar conversado → KPI. Debe mostrar banner sintético, aviso referencial, snapshot y fallback. Perfil AWS solo se presenta según evidencia; el camino local conserva la demo.

Puntos diarios: **10:00** congelar acuerdos/C0–C4; **14:00** integrar lo disponible con mocks/adaptadores; **19:00** demo interna. Gates: privacidad; contratos; elegibilidad sin LLM; snapshot/hash. Adopción retroactiva conserva código conforme, clasifica gaps `CONFORME/PARCIAL/DIVERGE/NO_VERIFICADO` y no marca tareas sin evidencia.

Cierre futuro: un comando equivalente a `make setup && make run` carga datos y levanta backend/PWA; el snapshot local produce 10.000 evaluaciones en menos de 30 segundos en un ambiente registrado; el README operativo explica arquitectura, ejecución, campos ausentes/proxies y `usar_ventana=false`. Estos criterios siguen pendientes y no amplían esta materialización documental.

## Estados de diseño

| Área | Estado actual | Evidencia necesaria para cambiar |
|---|---|---|
| Requisitos y C0–C4 | DOCUMENTADO | revisión humana y parseo documental |
| Aplicación/runtime | NO_IMPLEMENTADO | pruebas de cada tarea futura |
| AWS, región y modelos | NO_VERIFICADO | smoke test fechado y sanitizado |
| Fallback local | DOCUMENTADO_NO_VERIFICADO | ejecución reproducible futura |
| Privacidad Demo | DOCUMENTADA | revisión de payloads/fixtures futura |
