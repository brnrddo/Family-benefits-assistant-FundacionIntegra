# Adenda — Ficha de Inscripción y Matrícula como puerta de ingreso

**Estado:** `PENDIENTE_VALIDACION_INTEGRA`  
**Alcance:** aclaración funcional de la Ficha de Inscripción y Matrícula Integra, formato declarado 2019. Complementa, sin modificar, [`PROYECTO_3_ESPECIFICACION_v2.md`](./PROYECTO_3_ESPECIFICACION_v2.md).

## Regla funcional

La Ficha de Inscripción y Matrícula Integra es **un solo expediente de exactamente tres páginas**. El expediente usa un único `form_record_id` sintético en Demo y atraviesa dos etapas:

1. `INSCRIPCION_INICIAL`: comprende exactamente las páginas 1 y 2, destinadas a inscripción y priorización. Su estado es `BORRADOR | COMPLETA`. Una familia nueva no puede darse de alta ni evaluarse hasta que esta etapa esté `COMPLETA` y exista la atestación autorizada correspondiente.
2. `MATRICULA`: comprende exactamente la página 3 del mismo expediente. Su estado es `NO_DISPONIBLE_AUN | PENDIENTE | COMPLETA`. No se exige para la primera preevaluación; se habilita al concretarse el evento autorizado de matrícula y entonces es obligatoria para cerrar la matrícula. No es una ficha separada, ajena, descartable ni opcional una vez matriculada.

La primera evaluación de hechos declarados es `PRELIMINAR`. Completar o actualizar campos tipados permitidos de la página 3 puede generar una reevaluación determinista versionada sin cambiar `form_record_id` ni borrar procedencia.

## Registro Social de Hogares

El Registro Social de Hogares (RSH) complementa o corrobora la ficha y nunca la sustituye ni satisface el gate de alta. Su ausencia conserva el expediente y produce `INDETERMINADO` donde una regla lo requiere. Una discrepancia se registra como `RSH_STATUS_MISMATCH`; no se sobreescribe silenciosamente lo declarado.

## Privacidad y Demo

El PDF plantilla no existe en este workspace y no se incorpora ni redistribuye mientras el permiso siga sin confirmar. La Demo recibe solo una atestación de etapa y el subconjunto sintético, tipado y permitido por C0/C2/C3. Formularios reales completados, RSH personal, documentos parcialmente ocultos, identificadores, contacto, domicilio, folios, códigos y datos excluidos permanecen fuera del repositorio y de la cuenta AWS del evento.

E-3 es un snapshot completamente sintético para Demo; no representa un alta real y no elimina el gate para familias nuevas. C0 mapea metadatos de la plantilla vacía, no respuestas. C3 no acepta PDF, bytes, base64, URL, claves de almacenamiento, PII, prompts, catálogo ni mapas EAV abiertos. El LLM recibe exclusivamente `LlmContextV1`, construido por allowlist después del gate, motor determinista y ranking.

## Pendientes de validación humana

Hasta respuesta formal de Integra, la referencia exacta de versión, el permiso de redistribución, las reglas de completitud de páginas 1–2, el evento que habilita página 3 y los campos permitidos de página 3 que disparan reevaluación permanecen `PENDIENTE_VALIDACION_INTEGRA`. Los contratos usan defaults cerrados y no inventan respuestas ni obligatoriedad de campos.
