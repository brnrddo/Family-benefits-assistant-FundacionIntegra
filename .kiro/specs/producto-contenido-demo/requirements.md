# Requisitos — Rol 4 Producto, contenido y demo

## MUST

- **CONT-001 — C0 completo (§2.7).** WHEN se mapea una ficha, THE CONTENT MUST classify cada campo en las cuatro clases, justificarlo y excluir identificadores, contacto, salud y judicial; `permitido_llm` MUST NOT habilitar runtime.
- **CONT-002 — C4 versionado y completo (§§8–9).** THE CONTENT MUST define en subobjetos cerrados todas las señales, umbrales, ventanas, pesos, estados, bonus, anualización, divisor de impacto, equivalencias, medianas, bandas/mapeos y prioridad familiar de §8, además de KPI, preguntas, beneficios, prompts, accesibilidad e `i18n/es.json`; cada archivo MUST tener versión/hash/clase obligatoria y C4 MUST NOT contener reglas normativas.
- **CONT-003 — Lenguaje simple (§§2.4,9).** WHEN texto es visible, IT MUST usar español simple, trato de usted, frases ≤20 palabras, explicar siglas, no prometer y cerrar con aviso referencial donde corresponda.
- **CONT-004 — Fuentes/revisión.** WHEN se publica contenido, IT MUST use fuentes oficiales inventariadas, URL HTTPS, revisión humana y trazabilidad.
- **CONT-005 — Fixtures/demo privados (§§13,16).** ALL familias, conversaciones y assets Demo MUST be wholly synthetic and labeled; activos MUST be inventoried and reviewed for prohibited fields.
- **CONT-006 — Ownership sin código (§18).** Rol 4 MUST edit only `content/` data/content formats and demo/pitch artifacts (CSV/JSON/YAML/Markdown), MUST NOT edit Python/TypeScript or eligibility rules.
- **CONT-007 — Prueba humana (§§14,17).** WHEN validating product, Rol 4 MUST test 360 px, comprehension, three-tap conversation, warnings and fallback, recording prioritized findings for Rol 3.
- **CONT-008 — Pitch/demo (§16).** THE DEMO MUST run ≤4 minutes, identify synthetic/simulated data, explain AWS by need/status/fallback and keep a backup video.
- **CONT-009 — Salida de mensaje estructurada.** Prompts y templates C4 MUST request only the closed text fields of C3 `PrintableCard` and MUST NOT request or include HTML, CSS, handlers or active URLs; citations MUST resolve to inventoried HTTPS sources.

## SHOULD

- **CONT-010 — Accesibilidad/language.** C4 SHOULD keep Polly/Translate disabled by default; IF enabled, it MUST include verified-account evidence, closed voice/language allowlists, limits and canonical Spanish fallback labels after human review.

## COULD

- **CONT-011 — Afiche territorial.** Rol 4 COULD inventory a wholly synthetic flyer and review a Textract draft; MUST NOT publish or formalize rules automatically.

## Fuera de alcance

Código, infraestructura, secrets, datos reales, reglas/umbrales de elegibilidad, HTML generado, publicación automática, claims legales y edición de contratos sin coordinación.
