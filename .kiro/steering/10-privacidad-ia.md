---
inclusion: always
---
# Privacidad e IA

Lea #[[file:docs/PRIVACIDAD_DEMO.md]] y #[[file:.kiro/specs/_shared/contracts/schemas/LlmContextV1.schema.json]].

- Solo fixtures completamente sintéticos y rotulados; enmascarar parcialmente no anonimiza.
- Allowlist y serialización cerrada antes de cualquier servicio downstream; Guardrails es segunda barrera.
- Nunca cuerpos, prompts, respuestas, identificadores completos, secretos o endpoints privados en logs/evidencia.
- El asistente no decide elegibilidad individual. Ante duda, falle cerrado o use plantilla.
