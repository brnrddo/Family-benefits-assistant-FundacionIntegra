# Requisitos — Rol 4 Producto, contenido y demo

## MUST

- **CONT-001 — C0 completo (§2.7; DEC-023).** WHEN se mapea la plantilla vacía, THE CONTENT MUST materializar C0 v2 con una fila identificable por campo/grupo de exactamente tres páginas, dos etapas y cuatro clases; incluir página/sección/obligatoriedad/disponibilidad/tipo/opciones/destinos/normalización/justificación, revisión por dos roles y cero respuestas. Cada destino `C2_CONTEXT` MUST tener una entrada exacta en `x-c0-field-crosswalk`. La banda `p2.income.band` MUST declararse como ingreso total del hogar, solo `C2_CONTEXT`, sin derivación directa a ingreso per cápita, motor o LLM. Los campos `p2.housing.camp_occupation` y `p2.housing.room_other_home` MUST conservar destinos C2 separados y documentar la derivación versionada `HOUSING-TYPE-V1`; solo dos combinaciones inequívocas producen tipo y las demás fallan a valor nulo/`DESCONOCIDO`. Cuando varios `field_id` apuntan al mismo destino C2 (`composition`, cada `adult.{mother|father|guardian}.household_head_signal` y `child.possible_disability`), C0 MUST inventariar una fila por `field_id` fuente y rol; la combinación determinista del hecho efectivo la fija C2 (`x-c0-many-to-one-policy-v1`) y C0/C4 MUST NOT definir precedencia ni resolver el valor efectivo. Antecedentes repetidos MUST separar madre, padre y encargado por atributo, incluida la continuación de página 2, sin grupos genéricos que pierdan rol o cardinalidad. Identificadores, contacto cloud, salud detallada y judicial MUST quedar excluidos o locales según política; `permitido_llm` MUST NOT habilitar runtime ni ampliar `LlmContextV1`.
- **CONT-002 — C4 versionado y completo (§§8–9).** THE CONTENT MUST define en subobjetos cerrados todas las señales, umbrales, ventanas, pesos, estados, bonus, anualización, divisor de impacto, equivalencias, medianas, bandas/mapeos y prioridad familiar de §8, además de KPI, preguntas, beneficios, prompts, accesibilidad e `i18n/es.json`; cada archivo MUST tener versión/hash/clase obligatoria y C4 MUST NOT contener reglas normativas.
- **CONT-003 — Lenguaje simple (§§2.4,9).** WHEN texto es visible, IT MUST usar español simple, trato de usted, frases ≤20 palabras, explicar siglas, no prometer y cerrar con aviso referencial donde corresponda.
- **CONT-004 — Fuentes/revisión.** WHEN se publica contenido, IT MUST use fuentes oficiales inventariadas, URL HTTPS, revisión humana y trazabilidad.
- **CONT-005 — Fixtures/demo privados (§§13,16).** ALL familias, conversaciones y assets Demo MUST be wholly synthetic and labeled; activos MUST be inventoried and reviewed for prohibited fields.
- **CONT-006 — Ownership sin código (§18).** Rol 4 MUST edit only `content/` data/content formats and demo/pitch artifacts (CSV/JSON/YAML/Markdown), MUST NOT edit Python/TypeScript or eligibility rules.
- **CONT-007 — Prueba humana (§§14,17).** WHEN validating product, Rol 4 MUST test 360 px, comprehension, three-tap conversation, warnings and fallback, recording prioritized findings for Rol 3.
- **CONT-008 — Pitch/demo (§16).** THE DEMO MUST run ≤4 minutes, identify synthetic/simulated data, explain AWS by need/status/fallback and keep a backup video.
- **CONT-009 — Salida de mensaje estructurada.** Prompts y templates C4 MUST request only the closed text fields of C3 `PrintableCard` and MUST NOT request or include HTML, CSS, handlers or active URLs; citations MUST resolve to inventoried HTTPS sources.
- **CONT-012 — Preguntas y copy del expediente por etapa.** C4 `QUESTIONS` e `I18N` MUST etiquetar únicamente preguntas y copy con `INSCRIPCION_INICIAL|MATRICULA`, claves cerradas y estados visibles para borrador, gate completo, página 3 no disponible, pendiente y completa. El copy MUST tener revisión humana, no prometer admisión y MUST NOT definir completitud, habilitación, hechos, elegibilidad, acceso ni ranking.

## SHOULD

- **CONT-010 — Accesibilidad/language.** C4 SHOULD keep Polly/Translate disabled by default; IF enabled, it MUST include verified-account evidence, closed voice/language allowlists, limits and canonical Spanish fallback labels after human review.

## COULD

- **CONT-011 — Afiche territorial.** Rol 4 COULD inventory a wholly synthetic flyer and review a Textract draft; MUST NOT publish or formalize rules automatically.

## Fuera de alcance

Código, infraestructura, secrets, datos reales, reglas/umbrales de elegibilidad, HTML generado, publicación automática, claims legales y edición de contratos sin coordinación.
