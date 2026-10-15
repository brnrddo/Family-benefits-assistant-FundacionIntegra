# Plan de arreglos para la demo (dos personas en paralelo)

**Fecha:** 2026-10-15 · **Estado:** vigente · **Prioridad:** rapidez

Dos personas trabajan al mismo tiempo. El reparto es **por archivos**: nadie edita
un archivo de la otra persona, así nada se sobrescribe ni se pierde. Pruebas
mínimas: **un test por comportamiento clave** y la suite completa **una sola vez
al final**.

---

## 1. Qué se arregla

| # | Arreglo | Quién |
|---|---|---|
| 1 | Chat: la tía cuenta la situación de una familia (texto libre) y recibe beneficios del catálogo relacionados | B |
| 2 | Quitar las preguntas generales de ejemplo del asistente | B |
| 3 | "Agregar información": preguntas Sí / No / No sé que se responden ahí mismo, y el beneficio pasa de "falta información" a "aplica" o "no aplica" | A |
| 4 | Sesión de una tía ficticia con nombres de niños y jardines, y familias elegidas para mostrar cada caso | B |
| 5 | Orden visual de beneficios | A, **después** de lo demás |
| * | Perfil de la profe en el encabezado | B |
| 6 | Quitar "Ver guion" y "Mensaje y tarjeta" | A (botones) / B (rutas y páginas) |
| 7 | Búsqueda de niño en Inicio | B |
| 8 | Quitar "Familia nueva" manual | B |

Decisiones tomadas:

- **Chat:** texto libre; cada mensaje se responde solo; el historial se ve en
  pantalla y no se guarda. Responde "apoyos del catálogo relacionados con lo que
  cuenta" y nunca "le corresponde". Sale como `CATALOG_INFO`, sin cambiar C3.
- **Agregar información:** un dato declarado da como máximo **SI PRELIMINAR**,
  nunca CONFIRMADO. Las respuestas viven en memoria del backend (se pierden al
  reiniciar).
- **Demo:** motor real (`E3_MOCK=0`) con familias elegidas de **2 o 3 jardines**.
  Nombres de niños y jardines solo en el teléfono, rotulados sintéticos.

## 2. Por qué falla hoy "Agregar información"

- El motor manda sus nombres de campo (`semanas_gestacion`, `tramo_rsh`…) y la
  pantalla solo reconoce los de C3 (`pregnancy`, `rsh_band`…). Por eso sale
  "No hay preguntas para responder", "Un dato del hogar" y preguntas repetidas.
- El motor acepta solo 8 campos declarados (`engine/facts.py`), y el embarazo
  nunca cambia nada: `_candidatos("GESTANTE")` siempre devuelve vacío
  (`engine/evaluator.py`).
- El acceso no se recalcula: si un beneficio pasa a SI queda con acceso
  INDETERMINADO, combinación inválida, y el endpoint responde 503.

## 3. Reparto de archivos

| | Persona A · "Ficha y motor" | Persona B · "Demo y asistente" |
|---|---|---|
| Rama / worktree | `arreglos-ficha` en `.worktrees/ficha` | `arreglos-demo` en `.worktrees/demo` |
| Frontend | `features/family/`, `features/add-info/`, `features/new-family/questions.tsx`, `api/proposals/`, `domain/benefitGroups.ts`, `domain/presentation.ts` | `main.tsx`, `router.tsx`, `features/system/`, `features/home/`, `features/assistant/`, `features/demo-session/` (nueva), `features/script/`, `features/message/`, `features/new-family/NewFamilyPage*`, `offline/localNamesSeed.*`, `config/profile.ts`, `e2e/` |
| Backend | `engine/`, `access/`, `api/routers/antecedentes.py`, `api/antecedentes_*.py`, `api/models_antecedentes.py`, `api/motor_real.py` | `genai/template_provider.py`, `genai/content_catalog.py`, `api/routers/genai.py` |
| Nadie toca | `C3-api.openapi.yaml`, `genai/provider.py`, `auth/`, `infrastructure/` | |

Archivos compartidos, con reglas:

- **Textos** (`content/i18n/es.json`, `frontend/src/i18n/es.mock.ts`,
  `frontend/src/i18n/catalog.ts`): A solo agrega claves `family.*` y
  `add_info.*`; B solo `assistant.*`, `demo.*`, `home.*` y `nav.*`. Cada clave
  nueva va junto a su bloque, nunca al final del archivo.
- **Registro de decisiones** (`.kiro/specs/_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md`):
  nadie lo edita mientras trabaja. A tiene reservados DEC-081 a DEC-084 y B
  DEC-085 a DEC-089; se escriben en la tarea 7.
- **Fixtures MSW:** solo se agregan nuevas; las existentes no se modifican.

Antes de abrir el PR: `git fetch` y rebase sobre `main`. Nunca `--force`,
`reset --hard` ni `clean -fd`.

## 4. Tareas

Orden: A hace 1 → 2 → 3; B hace 4 y 5 en paralelo, luego 6. Al final, 7 juntos.

### Tarea 1 (A) · Preguntas Sí/No en "Agregar información"

- Ver qué códigos aparecen: `SELECT DISTINCT datos_faltantes FROM evaluaciones` en `backend/e3.db`.
- Ampliar `MISSING_CODE_FIELD` (`frontend/src/api/proposals/addInfo.ts`) con los
  nombres del motor: `semanas_gestacion`, `cobertura_incompatible`, `tramo_rsh`,
  `parto_red_publica`, `control_prenatal_red_publica`, `residencia_*`,
  `antecedente_edad_vigente`.
- Agregar los campos que falten al schema de la propuesta (front y
  `backend/app/api/models_antecedentes.py`). Embarazo: "¿Hay alguien
  embarazada?" y "¿Tiene N semanas o más?", con N leído del parámetro P006-02,
  nunca escrito fijo.
- Lo que no tiene pregunta cerrada queda como guía, sin repetir textos.
- **Test (1):** `semanas_gestacion` produce una pregunta Sí/No y no hay duplicados.

### Tarea 2 (A) · El motor recalcula con lo declarado (DEC-081, DEC-082)

- `engine/`: un embarazo declarado crea el candidato GESTANTE (adulta de
  referencia); "No" deja el beneficio en NO. Sumar a `CAMPOS_DECLARABLES` lo que haga falta.
- `api/antecedentes_motor.py`: traducir los campos de la pantalla al motor.
- `access/`: recalcular el acceso de esa familia con los resultados en memoria
  (SI sin gestión → ELEGIBLE_SIN_ASIGNACION). `reconstruir_familia_declarada` lo usa.
  No se modifica `e3.db` ni el snapshot.
- **Test (1):** familia con BEN-003 en INDETERMINADO + "Sí, ≥N semanas, sin
  cobertura" → SI PRELIMINAR / ELEGIBLE_SIN_ASIGNACION.

### Tarea 3 (A) · Ficha más directa

- Una tarjeta "Datos del hogar": quiénes viven, tramo RSH y "Datos por
  confirmar", con el botón "Agregar información" ahí mismo.
- "Preguntar a la familia" sin repetidos.
- Quitar los botones "Ver guion" y "Mensaje y tarjeta" de `FamilyPage.tsx`.
- **Tests:** solo ajustar los existentes que se rompan (`FamilyPage.test.tsx`,
  `localName.privacy.test.tsx`). Sin tests nuevos.

### Tarea 4 (B) · Chat de situaciones (DEC-085, DEC-086)

- Backend (`genai/template_provider.py`):
  - Tabla cerrada situación → beneficios (embarazo → BEN-003/009; sin trabajo →
    BEN-016/017; discapacidad → BEN-006; adulto mayor, agua, alimentos, vivienda).
    El Rol 4 revisa el texto después.
  - `es_pregunta_individual` deja de reaccionar a "mi hijo" / "mi familia"; solo
    desvía "¿califica?", "¿le corresponde?".
  - Filtro de datos personales (RUT, teléfono, correo) → 422 sin repetir el texto.
  - Respuesta con plantilla: "relacionados con lo que cuenta… revise la ficha",
    con aviso y citas. Bedrock entra cuando el Rol 2 AWS cierre A3.
- Frontend (`features/assistant/`): historial en memoria, ejemplos de
  situaciones en vez de preguntas generales, texto de introducción nuevo.
- **Test (1, backend):** "está embarazada y sin trabajo" → `CATALOG_INFO` con BEN-003.

### Tarea 5 (B) · Elegir las familias de la demo

- Consultas SQL de solo lectura sobre `backend/e3.db` (tablas `evaluaciones` y
  `accesos`) para elegir 2 o 3 jardines que juntos tengan: SI CONFIRMADO, SI
  PRELIMINAR, INDETERMINADO por embarazo, SIN_CUPO (BEN-018), ASIGNADO,
  discapacidad (BEN-006, p. ej. familias 00361–00365) y brecha (familias 91–230).
- Escribir la semilla rotulada `SYNTHETIC_DEMO_NOT_A_REAL_PERSON` en
  `frontend/src/offline/localNamesSeed.json`: tía ficticia, nombres de jardines y
  de niños. Solo nombres inventados.
- Anotar en este documento (sección 5) qué familia muestra cada caso.
- **Sin tests nuevos.**

### Tarea 6 (B) · Sesión de la tía, búsqueda y quitar vistas (DEC-087, DEC-088)

- Pantalla "Entrar como Tía X (demo)", solo en perfil demo, nunca en `escala`.
  Al entrar se cargan los nombres de la semilla (hoy se cargan en `main.tsx`).
- Encabezado con "Tía X · Jardín Y"; el selector de jardín muestra solo los de la demo.
- Salir borra nombres y estado de sesión.
- Búsqueda en Inicio por nombre o ID corto, sin enviar nada a la red.
- Quitar rutas, páginas y tests de guion, mensaje y "Familia nueva", y su
  pestaña del menú. `questions.tsx` se mantiene (lo usa A).
- **Test (1):** buscar un nombre deja una sola fila.

### Tarea 7 (A y B) · Integración

- Se fusiona primero A, luego B rebasado sobre `main`.
- B ajusta `e2e/smoke.spec.ts` al recorrido nuevo solo si se rompe.
- A escribe DEC-081 a DEC-088 en el registro, incluidas las desviaciones del
  spec del frontend: FE-001 (sin "Familia nueva"; asistente pasa a chat de
  situaciones) y FE-008/FE-009 (sin guion ni mensaje). Actualizar
  `DIVISION_TAREAS_APOYO_ROL2.md`: la regla de no tocar `engine/`/`access/`
  queda superada por DEC-081.
- **Verificación, una sola vez:** `npm run check` y `npm run test:e2e` en
  `frontend/`; `py -3.11 -m pytest -q` en `backend/`.
- Ensayo del recorrido con `E3_MOCK=0`: entrar → buscar niño → ficha → responder
  embarazo → "aplica" → "Ya le informé" → chat de situaciones.

Después de la tarea 7: orden visual de beneficios (A).

## 5. Casos de la demo

Lo completa B en la tarea 5.

| Caso | Jardín | Familia | Nombre ficticio |
|---|---|---|---|
| SI CONFIRMADO | | | |
| SI PRELIMINAR | | | |
| Falta embarazo → se responde y aplica | | | |
| SIN_CUPO | | | |
| ASIGNADO | | | |
| Discapacidad | | | |
| Brecha | | | |

## 6. Riesgos

- El texto libre del chat puede traer salud o nombres: los filtros reducen el
  riesgo, no lo eliminan. El aviso "no escriba datos personales" queda visible.
- Las respuestas Sí/No se pierden al reiniciar el backend. Guardarlas queda como tarea aparte.
- Embarazo y discapacidad son sensibles: las preguntas quedan opcionales ("si desea responder").
