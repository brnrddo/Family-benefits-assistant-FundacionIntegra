# Requisitos — Rol 3 Frontend PWA

## MUST

- **FE-001 — Seis vistas (§14).** THE SYSTEM MUST ofrecer Inicio, Ficha familia, Marcar conversado, Familia nueva, KPI y Asistente consumiendo C3.
- **FE-002 — Mobile/accesible (§§2.1,13,14).** WHEN viewport=360 px, THE SYSTEM MUST mantener contraste, letra/controles grandes, teclado/foco, lectura simple y flujo de conversación en tres toques.
- **FE-003 — Sin lógica duplicada (§§6–8).** THE SYSTEM MUST display C1/U/B/V from C3 and MUST NOT recalculate eligibility, access or ranking.
- **FE-004 — Copy y aviso (§§2.4,9,14).** THE SYSTEM MUST import canonical `content/i18n/es.json`, show referential notice in ficha/guion/message and display U/B/V chips plus deterministic “por qué”.
- **FE-005 — Estados C3.** WHEN API loads/fails/falls back, THE SYSTEM MUST show loading, empty, error, retry, `provider=PLANTILLA`, snapshot age and safe messages without echoing values.
- **FE-006 — Poca conexión (§2.4; diseño).** Demo MAY cache only synthetic data with TTL/snapshot and queue a minimal synthetic conversation; pending MUST NOT increase confirmed KPI. Escala MUST keep family context in memory and disable queue until approved.
- **FE-007 — Reconexión/logout.** WHEN reconnecting, THE SYSTEM MUST handle 201/409/401/503 distinctly; logout MUST clear permitted cached context and warn before deleting unsent Demo queue.
- **FE-008 — WhatsApp preview (§3 SHOULD).** THE SYSTEM MUST offer preview/copy only and MUST NOT send, apply or promise on behalf of a family.
- **FE-009 — Tarjeta imprimible segura.** WHEN C3 returns `PrintableCard`, THE SYSTEM MUST render `CARD_V1` only with an owned template and normal framework escaping; MUST NOT inject API/model strings as HTML, CSS, attributes or active URLs, and MUST accept links only from typed HTTPS `SourceCitation` entries.
- **FE-012 — Expediente de inscripción y matrícula por etapas (PROD-015; C3 v2).** WHEN la tía gestiona una familia nueva, THE SYSTEM MUST mostrar a 360 px el progreso de páginas 1–2, guardado de borrador, `INSCRIPCION_INICIAL=BORRADOR|COMPLETA` y errores cerrados sin eco de valores. Página 3 MUST ser visible como parte pendiente del mismo expediente, bloqueada mientras `NO_DISPONIBLE_AUN`, editable solo tras evento de matrícula y nunca descrita como opcional o ajena una vez matriculada. La UI MUST enviar “No sé” como `UNKNOWN`, consumir `/api/v2` y MUST NOT calcular gate, elegibilidad ni ranking ni capturar campos excluidos.

## SHOULD

- **FE-010 — Audio/language fallback.** THE SYSTEM SHOULD preserve the structured printable card and visible canonical Spanish when audio/translation is unavailable.

## COULD

- **FE-011 — Afiche admin.** Authorized catalog UI COULD submit only metadata for an inventoried synthetic asset and show pending human review.

## Fuera de alcance

Business WhatsApp, storage of real context, direct AWS SDK calls from UI, eligibility logic, editing C4 inside components, rendering model-provided markup and unapproved analytics identifiers.
