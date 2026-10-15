# Flujo de la ficha familiar

La PWA ayuda a la educadora o directora a preparar una conversación breve con cada familia. Orienta; no determina derechos ni postula por la familia.

## Flujo de punta a punta

```text
23 CSV canónicos
  → loader y base tipada
  → características calculadas
  → motor de reglas (SI | NO | INDETERMINADO + traza)
  → estado de acceso
  → datos faltantes convertidos en preguntas
  → prioridad determinista
  → ficha y recomendaciones
  → conversación registrada
  → KPI de familias informadas
```

1. **Datos:** el loader relaciona familias, integrantes, RSH, condiciones, catálogo, reglas y gestiones. Ausencia de un dato no equivale a `false` ni a cero.
2. **Reglas:** el motor evalúa cada beneficio con versiones y reglas trazables. El resultado es `SI`, `NO` o `INDETERMINADO`; un rechazo previo no cambia los criterios.
3. **Acceso:** se distingue si ya lo recibe, está en trámite, fue rechazado, podría solicitarlo, está pendiente de antecedentes o falta información.
4. **Preguntas:** cada dato faltante genera una pregunta simple para la conversación. Una respuesta declarada produce una reevaluación preliminar, no una certeza.
5. **Prioridad:** urgencia, ayuda estimada, vulnerabilidad y estado de acceso producen un orden auditable y una razón visible.
6. **Ficha:** la educadora ve qué conversar, por qué, qué falta, dónde consultar y cuál es el siguiente paso.
7. **Conversación:** registra beneficios mencionados, canal, fecha y siguiente paso, sin notas sensibles.
8. **KPI:** el registro alimenta porcentaje de familias informadas, familias nuevas informadas y principales brechas.

## Contenido visible de la ficha

- Identificador interno y composición familiar sin RUT.
- Estado y tramo del Registro Social de Hogares, cuando exista.
- Las tres oportunidades prioritarias con estado, urgencia, ayuda estimada y explicación del orden.
- Requisitos cumplidos y traza técnica disponible bajo detalle.
- Datos faltantes y preguntas sugeridas para obtenerlos.
- Recomendaciones concretas: qué hacer, dónde consultar, qué llevar y fuente oficial.
- Beneficios ya asignados o en trámite, separados de las oportunidades.
- Guion de conversación y mensaje para la familia.
- Acción para marcar la conversación y el siguiente paso.

Toda vista, guion y mensaje incluye: **“Orientación referencial; no determina derechos. Confirmar en la institución.”**

## Beneficios personalizados y generales

### Personalizados

Se muestran cuando existe una evaluación para esa familia. `SI` puede transformarse en una oportunidad o estado de acceso; `INDETERMINADO` se muestra como “Preguntar primero”; `NO` no se presenta como recomendación. Nunca se afirma que una familia recibirá el beneficio.

### Generales

Son información útil para todas las familias, independiente de sus datos, por ejemplo canales oficiales, actualización del Registro Social de Hogares o servicios territoriales. Viven en una sección separada, **“Información para todas las familias”**, y no reciben una etiqueta de elegibilidad ni alteran la prioridad personalizada.

Esta separación evita que una recomendación general parezca una conclusión del motor.

## Uso de Bedrock

El motor determinista decide reglas, acceso y prioridad. Bedrock recibe únicamente resultados calculados, catálogo, fuentes y contexto familiar filtrado para:

- redactar una explicación en lenguaje simple;
- preparar un guion breve para la educadora;
- redactar un mensaje o tarjeta para la familia.

Bedrock nunca decide elegibilidad, inventa requisitos, completa datos faltantes ni reordena beneficios. Nunca recibe nombres, RUT, folio RSH, teléfono, nacionalidad, diagnósticos, datos de salud o derivaciones judiciales. Si Bedrock no está disponible, las plantillas deterministas mantienen el flujo.

## Conversación y medición

La educadora confirma qué beneficios mencionó, canal y siguiente paso. El KPI principal es familias con al menos una conversación sobre el total; para familias nuevas se mide si fueron informadas dentro de 30 días. Los indicadores agregados no exponen datos personales.

Véanse la [especificación](../especificacion/PROYECTO_3_ESPECIFICACION_v2.md) y los [roles del equipo](../equipo/ROLES_Y_RESPONSABILIDADES.md).
