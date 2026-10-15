# Flujo de la Ficha de Inscripción y Matrícula

La PWA ayuda a la educadora o directora a ingresar y orientar una familia. Orienta; no determina derechos ni postula por ella. La regla completa está en la [adenda de ingreso](../especificacion/ADENDA_FICHA_INGRESO.md).

## Un expediente de tres páginas y dos etapas

La Ficha de Inscripción y Matrícula Integra, formato declarado 2019, es un único expediente identificado por `form_record_id`:

1. **Inscripción inicial:** páginas 1–2 se guardan como borrador. Solo `INSCRIPCION_INICIAL=COMPLETA` habilita el alta y la primera preevaluación.
2. **Preevaluación:** las respuestas tipadas permitidas producen hechos `DECLARADO`, `acreditada=false`. El resultado sustentado por ellos es `PRELIMINAR`.
3. **Matrícula diferida:** página 3 permanece visible en el mismo expediente como `NO_DISPONIBLE_AUN`. No se exige para la primera preevaluación.
4. **Matrícula concretada:** un evento autorizado cambia página 3 a `PENDIENTE`. Desde entonces debe completarse; no es una ficha separada ni opcional.
5. **Reevaluación:** cambios permitidos crean una evaluación determinista versionada y conservan `form_record_id` y procedencia por página/sección/hecho.

```text
Páginas 1–2 BORRADOR
  → INSCRIPCION_INICIAL COMPLETA (gate)
  → normalización tipada
  → motor (SI | NO | INDETERMINADO + traza)
  → resultado PRELIMINAR cuando usa hechos declarados
  → prioridad y preguntas
  → ficha/recomendaciones
  → evento autorizado de matrícula
  → página 3 PENDIENTE → COMPLETA en el mismo expediente
  → reevaluación determinista versionada cuando corresponde
```

Un expediente ausente, un borrador o un request funcionalmente vacío no se evalúan. “No sé” se conserva como `DESCONOCIDO` + nulo + `no_informado`; nunca equivale a `false` ni a cero. Página 3 no puede editarse antes de habilitación y omitirla impide declarar `MATRICULA=COMPLETA`.

## E-3 y Registro Social de Hogares

Los 23 CSV E-3 son un snapshot completamente sintético de Demo. Permiten probar motor y ranking, pero no representan una nueva postulación y no sustituyen el gate.

El Registro Social de Hogares (RSH) complementa o corrobora la ficha; nunca la sustituye. Sin RSH, la familia conserva su alta y las reglas dependientes quedan `INDETERMINADO`. Una discrepancia agrega `RSH_STATUS_MISMATCH` y no sobreescribe lo declarado.

## Flujo posterior al gate

1. **Reglas:** el motor evalúa versiones y reglas trazables. Un rechazo previo no cambia criterios.
2. **Acceso:** distingue asignado, en trámite, rechazado, brecha, cupo, antecedentes o información faltante.
3. **Preguntas:** cada faltante autorizado genera copy C4 revisado; C4 no decide elegibilidad.
4. **Prioridad:** urgencia, ayuda estimada, vulnerabilidad y acceso producen un orden auditable.
5. **Ficha visible:** muestra hasta tres oportunidades, razón, faltantes, lugar y siguiente paso.
6. **Conversación/KPI:** registra campos cerrados sin notas sensibles ni doble conteo.

Toda vista, guion y mensaje incluye: **“Orientación referencial; no determina derechos. Confirmar en la institución.”** Mensaje/WhatsApp es una capacidad SHOULD de vista previa; no forma parte del gate y no envía automáticamente.

## Privacidad y uso de IA

C0 mapea la plantilla vacía, no respuestas. Formularios reales completados y RSH personal permanecen fuera del repositorio y de la cuenta AWS del evento. La API no acepta PDF, bytes, base64, URL, claves de almacenamiento, PII, prompts, catálogo ni mapas EAV abiertos.

Orden seguro: gate → motor determinista → ranking U/B/V → allowlist `LlmContextV1` → Bedrock o plantilla. Bedrock solo redacta; nunca decide elegibilidad, acceso, gate o prioridad. Datos locales permanecen locales y campos totalmente excluidos no se capturan ni persisten.

Véanse la [especificación inmutable](../especificacion/PROYECTO_3_ESPECIFICACION_v2.md), la [adenda](../especificacion/ADENDA_FICHA_INGRESO.md), la [privacidad](../PRIVACIDAD_DEMO.md) y los [roles](../equipo/ROLES_Y_RESPONSABILIDADES.md).
