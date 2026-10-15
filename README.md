# AWS Breaking Barriers — Apoyo Inteligente para Familias

PWA para Fundación Integra creada durante un hackathon de tres días. Relaciona datos sintéticos familiares con reglas de beneficios, muestra ficha, RSH, oportunidades, datos faltantes, preguntas y recomendaciones, y ordena las conversaciones por prioridad. También mantiene información general para todas las familias.

La elegibilidad, el estado de acceso y la prioridad son deterministas y trazables. Amazon Bedrock se usa únicamente para redactar explicaciones, guiones y mensajes a partir de resultados ya calculados y datos filtrados.

## Documentación principal

- [Especificación del proyecto](./docs/especificacion/PROYECTO_3_ESPECIFICACION_v2.md)
- [Adenda: ficha de ingreso obligatoria](./docs/especificacion/ADENDA_FICHA_INGRESO.md)
- [Roles y responsabilidades](./docs/equipo/ROLES_Y_RESPONSABILIDADES.md)
- [Estructura del repositorio](./docs/arquitectura/ESTRUCTURA_REPOSITORIO.md)
- [Flujo de la ficha familiar](./docs/producto/FLUJO_DE_FICHA.md)
- [Guía para contribuir](./CONTRIBUTING.md)

## Estructura y ownership

| Ruta | Contenido | Dueño principal |
|---|---|---|
| `backend/` | Motor determinista, backend y API | Ingeniería en Computación |
| `data/` y `database/` | Fuente canónica, loader, características, acceso, prioridad y QA | Ingeniería Mecánica |
| `frontend/` | PWA e integración | Ingeniería Eléctrica |
| `ia/` | Única integración Bedrock, filtro de contexto y redacción | Ingeniería en Computación |
| `docs/producto/` | Producto, dominio, lenguaje, privacidad, pruebas y pitch | Ingeniería en Recursos Naturales |
| `docs/equipo/` y `docs/arquitectura/` | Acuerdos y contratos compartidos | Equipo; coordina Computación |

No se usan carpetas personales. Cada tarea se realiza en el componente al que pertenece y la aprueba su dueño.

## Flujo del producto

```text
Alta nueva: páginas 1–2 de la ficha → INSCRIPCION_INICIAL COMPLETA (gate)
→ hechos tipados DECLARADO → motor → PRELIMINAR → prioridad/preguntas
→ página 3 pendiente del mismo expediente al concretar matrícula → reevaluación
→ conversación → KPI

Snapshot Demo: E-3 sintético → base tipada → motor → prioridad → ficha
```

La Ficha de Inscripción y Matrícula formato declarado 2019 es un solo expediente de tres páginas. Páginas 1–2 son obligatorias antes de crear o evaluar una familia nueva. Página 3 no se exige para la primera preevaluación, pero permanece dentro del mismo `form_record_id` y debe completarse al concretar matrícula. RSH complementa o corrobora; nunca sustituye la ficha. Los beneficios personalizados provienen del motor. Los beneficios generales se muestran en una sección independiente y nunca aparentan ser una evaluación familiar. Todo resultado incluye el aviso de orientación referencial.

## Empezar en Kiro

1. Clone el repositorio con `Git: Clone` desde la paleta de comandos (`Ctrl+Shift+P`).
2. Lea la especificación y el documento de roles.
3. En **Source Control**, ejecute **Pull**.
4. Cree una rama para una tarea concreta y coordine si tocará un archivo compartido.
5. Trabaje en el componente correspondiente; use mocks acordados si depende de otra área.
6. Revise el diff y la validación del componente, haga un commit claro y luego **Push**.

Los detalles están en [CONTRIBUTING.md](./CONTRIBUTING.md).

## Datos

Los 23 CSV de `data/publico/` son canónicos únicamente para el snapshot E-3 completamente sintético. `data/publico/dataset_e3.json` no debe usarse como única fuente porque omite `condiciones_integrante.csv`. E-3 no representa una nueva postulación, no sustituye la ficha y no satisface el gate de alta. El mapeo versionado de la plantilla vacía está en `content/mapeo_ficha.csv`; no contiene respuestas ni autoriza redistribuir el PDF.

## Seguridad y privacidad

- Copie `.env.example` a `.env` y complete valores solo localmente.
- Nunca suba claves, contraseñas, `.env`, bases locales, dumps ni datos reales.
- Nunca envíe a Bedrock nombres, RUT, folios RSH, teléfonos, diagnósticos o datos de salud.
- Si se expone un secreto, avise inmediatamente para rotarlo.

## Specs Kiro

El baseline trazable y los contratos entre componentes se consultan en:

- [Índice de Specs Kiro](./.kiro/specs/INDICE.md)
- [Spec maestro del producto](./.kiro/specs/apoyo-inteligente-familias/requirements.md)
- [Guía Kiro para el equipo](./docs/GUIA_KIRO_EQUIPO.md)
- [Arquitectura AWS-first](./docs/ARQUITECTURA_AWS.md)
- [Política de privacidad y anonimización](./docs/PRIVACIDAD_DEMO.md)
