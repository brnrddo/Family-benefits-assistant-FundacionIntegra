# Frontend

## Objetivo

Construir la PWA mobile-first para la educadora: lista priorizada, ficha familiar, preguntas, recomendaciones, conversación y KPI, utilizable con poca conexión.

- **Dueño:** Ingeniería Eléctrica.
- **Colaboradores:** Computación entrega contratos/API; Recursos Naturales valida lenguaje, privacidad y pruebas manuales.

## Entradas y salidas

**Entradas:** API o mocks con familias, RSH, evaluaciones, acceso, prioridad, preguntas, recomendaciones y KPI.

**Salidas:** vistas accesibles, aviso referencial, registro de conversación y presentación separada de beneficios personalizados y generales.

## Dependencias y límites

Depende del contrato JSON de `backend/` y de los criterios de `docs/producto/`. Trabaja con mocks acordados hasta tener el API real. El despliegue AWS también pertenece a Ingeniería Eléctrica.

No colocar aquí reglas de elegibilidad, cálculos alternativos de prioridad, secretos, acceso directo a datos canónicos ni datos personales en almacenamiento o logs. No crear scaffolding hasta elegir framework.

Contexto: [especificación](../docs/especificacion/PROYECTO_3_ESPECIFICACION_v2.md), [roles](../docs/equipo/ROLES_Y_RESPONSABILIDADES.md), [estructura](../docs/arquitectura/ESTRUCTURA_REPOSITORIO.md) y [flujo de ficha](../docs/producto/FLUJO_DE_FICHA.md).
