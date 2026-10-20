# IA generativa

## Objetivo

Integrar Amazon Bedrock para redactar explicaciones, guiones y mensajes en lenguaje simple a partir de resultados deterministas. Esta es la única ubicación de la integración generativa.

- **Dueño:** Ingeniería en Computación.
- **Colaborador principal:** Ingeniería en Recursos Naturales revisa lenguaje, privacidad y utilidad.

## Entradas y salidas

**Entradas:** salida del motor, prioridad ya calculada, catálogo, fuentes y contexto mínimo entregado por backend.

**Salidas:** explicación, guion y mensaje estructurados, siempre con aviso referencial y sin promesas.

## Dependencias y límites

Depende del contrato de `backend/` y de los criterios de producto. Aquí viven el adaptador Bedrock, los prompts técnicos y el único filtro de contexto previo al envío al modelo. Debe funcionar como capa de redacción reemplazable; si falla, el flujo conserva plantillas deterministas.

No colocar aquí elegibilidad, estado de acceso, prioridad, datos personales, credenciales ni prompts con nombres, RUT, folio RSH, teléfono, nacionalidad, diagnósticos, salud o antecedentes judiciales. Bedrock no completa datos faltantes ni inventa beneficios.

Contexto: [especificación](../../especificacion/PROYECTO_3_ESPECIFICACION_v2.md), [roles](../equipo/ROLES_Y_RESPONSABILIDADES.md), [estructura](../equipo/ESTRUCTURA_REPOSITORIO_INICIAL.md) y [flujo de ficha](../../producto/FLUJO_DE_FICHA.md).
