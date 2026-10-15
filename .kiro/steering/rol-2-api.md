---
inclusion: fileMatch
fileMatchPattern: "{backend/app/{api,auth,priority,genai,tracking}/**,infrastructure/**}"
---
# Rol 2 — API/AWS

Lea #[[file:.kiro/specs/api-priorizacion-genai/requirements.md]], #[[file:.kiro/specs/api-priorizacion-genai/design.md]] y #[[file:.kiro/specs/_shared/contracts/C3-api.openapi.yaml]].

Owner: Rol 2, rama `api`. Primer paso: mocks C3. Consuma C0/C1/C2/C4 sin cambiar elegibilidad. Filtre payload integral antes de Guardrails/Bedrock; preserve plantilla. AWS permanece no verificado hasta evidencia fechada.
