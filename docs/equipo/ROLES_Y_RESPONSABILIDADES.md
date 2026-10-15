# Roles y responsabilidades

El repositorio se organiza por componentes, no por personas. Cada componente tiene una persona dueña que aprueba cambios y coordina los handoffs; cualquier integrante puede colaborar.

## Ownership por componente

| Componente | Dueño principal | Colaboradores | Entregable |
|---|---|---|---|
| `backend/` (`engine`, `api`) | Ingeniería en Computación | Mecánica para contratos de datos; Eléctrica para integración | Motor determinista y API trazable |
| `data/` y `database/` | Ingeniería Mecánica | Computación para contrato del motor | Carga reproducible, modelo tipado y fuente canónica validada |
| Futuras áreas `loader`, `features`, `access`, `priority` y QA | Ingeniería Mecánica | Computación para integrar al backend | Características calculadas, estado de acceso, prioridad y pruebas |
| `frontend/` y despliegue AWS | Ingeniería Eléctrica | Computación para API; Recursos Naturales para lenguaje y pruebas | PWA integrada, mobile-first, desplegada y operable con poca conexión |
| `ia/` | Ingeniería en Computación | Recursos Naturales revisa lenguaje y privacidad | Única integración Bedrock, prompts técnicos y filtro de contexto previo al envío |
| `docs/producto/` | Ingeniería en Recursos Naturales | Todo el equipo valida | Flujo, lenguaje, privacidad, pruebas manuales y pitch |
| `docs/arquitectura/` | Ingeniería en Computación | Mecánica y Eléctrica | Contratos y límites técnicos compartidos |

## Responsabilidades y límites

### 1. Ingeniería en Computación — liderazgo técnico

**Entrega:** arquitectura, motor de reglas determinista, backend/API, contratos técnicos e integración Bedrock.

- Decide la elegibilidad con reglas trazables y conserva `SI | NO | INDETERMINADO`.
- Publica mocks y contratos de API para desbloquear frontend.
- Filtra en `ia/` el contexto enviado a Bedrock y verifica que el modelo solo redacte.
- Integra contribuciones y resuelve decisiones técnicas.

**Límite:** no redefine reglas de dominio, pesos de prioridad ni textos sin validación. Bedrock nunca decide elegibilidad, estado de acceso o prioridad.

### 2. Ingeniería Mecánica — datos y QA

**Entrega:** loader, base ordenada, características calculadas, estado de acceso, prioridad y evidencia de QA.

- Mantiene los 23 CSV de `data/publico/` como fuente canónica.
- Relaciona tablas para construir la ficha; distingue ausencia, `false` y cero.
- Calcula características, estados de acceso y ranking documentado.
- Diseña casos de prueba y reporta discrepancias con trazas.

**Límite:** no cambia contratos de API ni reglas de producto sin coordinar con Computación y Recursos Naturales.

### 3. Ingeniería Eléctrica — experiencia e infraestructura

**Entrega:** PWA, integración extremo a extremo y despliegue AWS.

- Implementa lista priorizada, ficha familiar, preguntas, recomendaciones, conversación y KPI.
- Trabaja primero con mocks y cambia al API real sin alterar el contrato.
- Valida vista móvil, poca conexión y avisos referenciales.
- Mantiene el despliegue y un plan de demo local.

**Límite:** no replica reglas de elegibilidad o prioridad en el navegador ni expone secretos en variables públicas.

### 4. Ingeniería en Recursos Naturales — producto y dominio, sin programar

**Entrega:** criterios de producto, lenguaje simple, privacidad, pruebas manuales, casos de demo y pitch.

- Valida preguntas, recomendaciones, beneficios generales y personalizados.
- Revisa que no se prometa acceso y que siempre aparezca el aviso referencial.
- Prueba el flujo como educadora en un celular y prioriza hallazgos.
- Revisa que nombres, RUT, folios RSH, diagnósticos y datos prohibidos no lleguen a Bedrock.

**Límite:** trabaja en Markdown, planillas y pruebas manuales; no necesita modificar código. Los cambios técnicos se entregan como criterios verificables al dueño correspondiente.

## Handoffs y contratos

Las disciplinas son dueñas de componentes; los rótulos Rol 1–4 de las Specs son workstreams contractuales. [DEC-022](../../.kiro/specs/_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md#decisiones) fija esta correspondencia y traduce los handoffs históricos de la fuente funcional sin crear contratos paralelos.

| Contrato único | Producción por componente → consumo | Contenido | Momento objetivo |
|---|---|---|---|
| C0 · Mapeo de ficha | Recursos Naturales → Mecánica y Computación | Campos útiles, excluidos y preguntas | Día 1, 14:00 |
| C1 · Salida de motor y acceso | Computación y Mecánica → Computación/API | Resultado, nivel, acceso, traza y datos faltantes | Stub Día 1, 14:00; completo Día 1 noche |
| C2 · Contexto familiar | Mecánica → Computación/API | Composición y señales autorizadas, con nulos explícitos | Día 2, 12:00 |
| C3 · API | Computación → Eléctrica | Endpoints y ejemplos JSON, primero con mocks | Día 1, 11:00 |
| C4 · Contenido y configuración | Recursos Naturales → Computación y Eléctrica | Pesos U/B/V, preguntas, textos, privacidad y fuentes | V1 Día 1 noche; final Día 2, 18:00 |

La base tipada alimenta C1/C2 sin crear otro contrato; la prioridad consume C1/C2/C4 y se publica por C3; la PWA desplegada es un entregable. Los contratos se cambian por acuerdo entre quien entrega y quien consume. Si falta una implementación, se conserva el contrato con un mock completamente sintético y rotulado.

## Rutina de los tres días

- **10:00 — acuerdos:** objetivo del día, contrato que cambia, responsables y bloqueos.
- **14:00 — integración:** unir lo disponible, aunque use mocks; comprobar un flujo completo.
- **19:00 — demo interna:** Recursos Naturales conduce una prueba de cinco minutos en celular y registra arreglos priorizados.
- Un bloqueo que dure más de 30 minutos se avisa en el chat con: qué falta, quién lo necesita y qué mock permite continuar.
- Antes de integrar, el dueño revisa su componente y otra ingeniería hace revisión cruzada: Computación↔Mecánica, Eléctrica↔Recursos Naturales.
- Los archivos compartidos (`README.md`, contratos y documentos de arquitectura) se coordinan antes de editar.

Véanse la [estructura del repositorio](../arquitectura/ESTRUCTURA_REPOSITORIO.md), el [flujo de la ficha](../producto/FLUJO_DE_FICHA.md) y la [especificación](../especificacion/PROYECTO_3_ESPECIFICACION_v2.md).
