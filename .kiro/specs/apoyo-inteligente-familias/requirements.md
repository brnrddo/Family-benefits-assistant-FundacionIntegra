# Requisitos — Apoyo Inteligente para Familias

Fuente funcional inmutable: [`PROYECTO_3_ESPECIFICACION_v2.md`](../../../docs/especificacion/PROYECTO_3_ESPECIFICACION_v2.md). Prioridades RFC 2119. Cada criterio es verificable y toda persona/hogar de Demo es sintético.

## MUST

### PROD-001 — Orientación para la tía (§§0, 2.1–2.5)
WHEN una tía autorizada abre su jardín, THE SYSTEM MUST mostrar familias y hasta tres oportunidades priorizadas para conversar, con motivo, faltantes, acción, lugar y fuente.

### PROD-002 — Decisiones deterministas (§§2.4, 6–8)
WHEN se evalúa una oportunidad, THE SYSTEM MUST resolver elegibilidad, acceso y ranking U/B/V de forma determinista, trazable y versionada; el LLM MUST NOT alterarlos.

### PROD-003 — Resultado y preguntas (§§2.4, 6.4, 9.3)
IF falta un hecho, THE SYSTEM MUST devolver `INDETERMINADO` y una pregunta revisada, no inferir `NO`; IF un `SI` usa hechos declarados, MUST ser `PRELIMINAR`.

### PROD-004 — Privacidad y sintéticos (§§2.7, 13)
BEFORE cualquier servicio downstream procesa contexto, THE SYSTEM MUST aplicar clasificación, minimización, allowlist cerrada y rotulado conforme a [`PRIVACIDAD_DEMO.md`](../../../docs/PRIVACIDAD_DEMO.md); datos reales MUST quedar fuera de Demo.

### PROD-005 — Contratos e integración (§18)
WHEN dos roles intercambian datos, THE SYSTEM MUST usar C0–C4 versionados como única interfaz y conservar snapshot, hashes y `request_id` según corresponda.

### PROD-006 — Conversación y KPI (§§1.6, 11)
WHEN la tía confirma una conversación, THE SYSTEM MUST registrarla idempotentemente y actualizar KPI de familias informadas sin doble conteo; fallos MUST NOT mostrar incremento confirmado.

### PROD-007 — Mobile y acceso limitado (§§2.1, 2.4, 14)
WHEN se usa un viewport de 360 px o baja conexión, THE SYSTEM MUST conservar lectura clara, controles grandes, estado de carga/error y edad del dato; datos vencidos MUST NOT presentarse como vigentes.

### PROD-008 — Aviso y no postulación (§§2.4, 3, 9)
WHEN se muestra ficha, guion o mensaje, THE SYSTEM MUST incluir “Orientación referencial; no determina derechos. Confirmar en la institución.”; MUST NOT postular por la familia ni prometer derechos.

### PROD-009 — AWS-first recuperable (§4 y diseño aprobado)
WHEN se usa AWS, THE SYSTEM MUST asignar cada servicio a una necesidad, evidencia y fallback; IF Cognito no está verificado, MUST NOT exponer contexto familiar en una API cloud anónima.

### PROD-010 — Snapshot consistente (diseño aprobado §§3–4, 10)
WHEN se publica un snapshot, THE SYSTEM MUST validar 500×20 resultados Demo, hashes y particiones antes de actualizar transaccionalmente los seis campos de `CONTROL/ACTIVE`; un fallo MUST conservar el activo anterior.

### PROD-014 — Cierre operativo reproducible (§17)
BEFORE declarar terminado el MVP, THE SYSTEM MUST disponer de un comando equivalente a `make setup && make run`, precalcular 10.000 evaluaciones en menos de 30 segundos en el ambiente documentado y explicar en el README futuro arquitectura, ejecución y supuestos de datos faltantes, incluida la desactivación inicial de la ventana.

## SHOULD

### PROD-011 — Familia nueva y mensaje (§§3, 9.2, 10)
WHEN la tía completa una ficha digital sintética con “No sé”, THE SYSTEM SHOULD crear hechos `DECLARADO`, preevaluación `PRELIMINAR` y vista previa para copiar a WhatsApp o imprimir; la tarjeta MUST cruzar C3 como campos estructurados y renderizarse con una plantilla propia, nunca como markup generado; THE SYSTEM MUST NOT enviar WhatsApp automáticamente.

### PROD-012 — Asistente y accesibilidad (§§3, 9, 14)
WHEN se consulta información general, THE SYSTEM SHOULD responder desde catálogo/fuentes con fallback; Polly/Translate SHOULD ser recuperables y una consulta individual MUST volver al motor sin Bedrock.

## COULD

### PROD-013 — Catálogo territorial (§3 COULD)
IF un asset sintético está inventariado y aprobado, THE SYSTEM COULD usar Textract para crear un borrador `PENDIENTE_REVISION`; MUST NOT publicarlo ni convertirlo en regla automáticamente.

## Fuera de alcance

- Postulación en nombre de familias; integración real con RSH, IPS u otros sistemas estatales.
- Datos reales, documentos parcialmente enmascarados, diagnósticos, contacto o material judicial.
- WhatsApp Business, decisiones de elegibilidad generativas, Bedrock multimodal, audio de entrada y agentes con acceso al motor.
- Implementación de aplicación, infraestructura, dependencias o tests en esta materialización documental.
