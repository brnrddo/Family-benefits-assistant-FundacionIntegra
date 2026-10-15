---
inclusion: fileMatch
fileMatchPattern: "{backend/**,infrastructure/**}"
---
# AWS-first

Lea #[[file:docs/ARQUITECTURA_AWS.md]] y #[[file:.kiro/specs/api-priorizacion-genai/design.md]].

- Cada servicio requiere necesidad, perfil, estado, costo/limitación y fallback.
- No declare región, modelo, permiso o servicio disponible sin smoke test fechado en la cuenta.
- Demo sin Cognito usa solo loopback; nunca API cloud anónima con contexto familiar.
- DuckDB/SQLite son fallback local. Cloud usa `SnapshotPartitionBuilder`; `CONTROL/ACTIVE` es único puntero activo.
