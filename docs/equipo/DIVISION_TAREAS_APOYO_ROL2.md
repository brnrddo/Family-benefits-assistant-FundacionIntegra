# División de tareas: apoyo al Rol 2

**Fecha:** 2026-10-15 · **Estado:** vigente

Cambio respecto del plan inicial (§15 y §18 de la especificación): la persona del
**Rol 3 (frontend)** terminó su parte y pasa a **apoyar al Rol 2**. El Rol 2
original se concentra en la **integración con AWS**.

Este documento existe para que nadie —ni persona ni agente— trabaje dos veces lo
mismo. Léalo completo antes de empezar.

---

## 1. Reparto en una frase

| Quién | Se queda con |
|---|---|
| **Rol 2 original** (y su agente de AWS) | Todo lo que toca AWS: identidad, IA en la nube, persistencia gestionada, despliegue e infraestructura |
| **Apoyo (ex Rol 3)** | Todo el backend que **no** toca AWS: datos reales, filtrado territorial, KPI y el cierre de alcance |

Regla simple para resolver dudas: **si requiere una cuenta de AWS, es del Rol 2
original. Si corre en el computador con `py -3.11`, es del apoyo.**

---

## 2. Lo que YA está hecho (no rehacer)

Antes de tomar una tarea, verifique que no esté aquí.

| Pieza | Estado | Dónde |
|---|---|---|
| API FastAPI con los 12 flujos de C3 bajo `/api/v1` | Listo | `backend/app/api/` |
| `/docs`, `/healthz`, errores cerrados por ruta | Listo | `backend/app/api/` |
| Priorización U/B/V determinista, sin números hardcodeados | Listo | `backend/app/priority/` |
| Filtro de privacidad por allowlist (`LlmContextV1`) | Listo | `backend/app/genai/llm_context.py` |
| Generador de textos sin IA (`TemplateProvider`) | Listo | `backend/app/genai/template_provider.py` |
| Motor de elegibilidad, acceso y contexto | Listo (Rol 1) | `backend/app/{engine,access,context}/` |
| **`POST /api/v1/familias/{id}/antecedentes`** | **Listo**, commit `29b58b7` | `backend/app/api/` |
| Frontend completo (PWA, mocks, e2e, i18n, offline) | Listo (ex Rol 3) | `frontend/` |
| C0 definitivo desde el mapeo de ficha | Listo (Rol 4, PR #9) | `content/` |

El endpoint de antecedentes quedó terminado con su idempotencia corregida y
**204 pruebas en verde**. No se reimplementa.

Base ya integrada en `main`: el PR #8 llevó la API, la priorización y el filtro
de privacidad; el PR #9 llevó el C0 definitivo del Rol 4. Para empezar cualquier
tarea, parta desde `main` actualizado.

---

## 3. Tareas del Rol 2 original (AWS)

Prioridad en este orden. Nada de esto está empezado.

### A1. Probar la cuenta antes de prometer nada
Smoke test mínimo y fechado por servicio, con datos sintéticos. Hasta tener
evidencia, todo servicio queda en `NO_VERIFICADO`.

Criterio de término: una tabla con servicio, región, operación probada, resultado
y fecha. Sin credenciales, sin identificadores de cuenta, sin endpoints privados.

### A2. Identidad (Cognito)
Reemplazar el stub de autorización por validación real de access token:
firma, `iss`, `exp`, `token_use=access`, `client_id` y scope.

Criterio de término: petición sin token devuelve 401; token válido con scope
correcto pasa; token de identidad se rechaza.

### A3. IA en la nube (Bedrock)
Completar `BedrockProvider` detrás de la interfaz que ya existe, con Converse y
Guardrails. **El filtro de privacidad local se aplica antes, siempre.** Si
Bedrock falla, cae a `TemplateProvider` y la respuesta sigue siendo 200.

Criterio de término: el guion y el mensaje se generan con Bedrock; cortando el
acceso, el flujo sigue funcionando con plantilla.

### A4. Persistencia gestionada
Hoy las conversaciones viven en memoria del proceso. Llevarlas a almacenamiento
real si el tiempo lo permite.

### A5. Despliegue
Publicar la PWA y la API. Dejar escrito el plan B local si el despliegue falla.

**Archivos del Rol 2 original (nadie más los toca):**
`backend/app/auth/`, `backend/app/genai/provider.py`, `infrastructure/`,
configuración de despliegue y el documento de evidencia AWS.

---

## 4. Tareas del apoyo (ex Rol 3)

Prioridad en este orden. Cada una es un PR propio.

**Estado al 2026-10-15:** B1, B2, B3 y B4 hechos (ver cada tarea). Las
decisiones quedaron en el registro compartido (DEC-064 a DEC-080, PREG-064 a
PREG-072). **Pendiente del Rol 1:** antecedentes en modo real. Con
`E3_MOCK=0`, `POST /familias/{id}/antecedentes` responde 503 hasta que el motor
acepte los campos declarados que envía la PWA (DEC-074, PREG-069).

### B1. Conectar el motor real (el de mayor valor para la demo) — HECHO (PR #15; catálogo PR #14; arreglos PR #21)
Hoy la API responde con datos sintéticos de demostración (`E3_MOCK=1`). La tarea
es que con `E3_MOCK=0` sirva datos reales de las 500 familias usando lo que ya
existe: `engine/service.py`, `access/`, `context/` y `priority/`.

- Si falta la base de datos, debe degradar a mocks con aviso, nunca romper.
- No modificar nada de `backend/app/{engine,access,context,loader,db}`: solo
  importarlo. Si encuentra un error ahí, repórtelo, no lo corrija. Superada para
  `engine/` y `access/` por DEC-081 (reevaluación con datos declarados, PR #31).

Criterio de término: `GET /familias/{id}` y `GET /familias/{id}/oportunidades`
devuelven resultados calculados por el motor, con su traza, y la suite sigue en
verde.

### B2. Filtrado territorial de beneficios — HECHO (PR #22, ejemplo solo demo)
Lo pidió explícitamente la contraparte de Integra: *"no todos los beneficios son
globales a nivel nacional; también hay beneficios particulares de ciertas zonas o
sectores. La idea es que sea lo más aterrizado posible al lugar donde está esa
familia y el jardín"*.

- Distinguir beneficios de alcance **nacional** y **local/zonal** usando lo que
  ya está en los datos: `data/publico/comunas.csv`, `jardines.csv` y los
  parámetros de cobertura por comuna que ya usan algunos beneficios.
- Sugerencia para no chocar con nadie: módulo nuevo, por ejemplo
  `backend/app/catalog/territorial.py`.
- No inventar beneficios locales. Si hace falta un ejemplo, debe ser sintético y
  estar rotulado como tal.
- Esta tarea tiene lado frontend: mostrar "disponible en su comuna" frente a
  "nacional". Como el apoyo es quien construyó la PWA, puede hacer ambos lados.

Criterio de término: para una comuna dada, la respuesta distingue ambos alcances
y el frontend lo muestra.

### B3. Marcar "familia informada" con un toque — HECHO (PR #23)
La contraparte confirmó que **sí** le sirve que la tía marque de un gesto que ya
informó a la familia, para medir el KPI, **sin perseguir el trámite después**.

- El registro de conversación hoy exige varios campos. Permitir valores por
  defecto razonables (los beneficios que se acaban de mostrar, siguiente paso
  "ninguno", canal "presencial") para que sea realmente un toque.
- Dejar documentados esos valores por defecto.

Criterio de término: un solo gesto en la PWA registra la conversación y el
indicador de familias informadas sube.

### B4. Cierre de alcance y registro de decisiones — HECHO (este PR)

Registrado en `.kiro/specs/_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md`: DEC-047
(front), DEC-064 a DEC-080, PREG-064 a PREG-072 y la tabla de equivalencias de
la numeración provisional. La reclasificación de los campos de puntaje en
`content/mapeo_ficha.csv` queda para el Rol 4 (PREG-072). La numeración
sugerida abajo quedó superada.

- Reclasificar los campos de **puntaje de la ficha** como no relevantes para
  beneficios, citando la respuesta de la contraparte.
- Registrar la decisión con las respuestas del 2026-10-15. Use **`DEC-046`** o
  siguiente: `main` ya usa hasta `DEC-045` y la integración en curso tomó
  `DEC-022`.
- Marcar explícitamente fuera de alcance: seguimiento del trámite, CRM, alertas
  de ventana y conversión de brechas.

---

## 5. Reglas que evitan choques

**No tocar, por ningún motivo:**

1. **`.kiro/specs/_shared/contracts/C3-api.openapi.yaml`.** Está congelado en
   **1.0.2**. El frontend genera sus tipos desde ese archivo y lo fija por hash:
   cualquier edición rompe su build y su test de snapshot. Si una funcionalidad
   necesita un campo nuevo, se implementa en el servidor como propuesta y se
   documenta, igual que se hizo con el endpoint de antecedentes.
2. **`backend/app/{engine,access,context,loader,db}`** (Rol 1): solo importar. Excepción: `engine/` y `access/` por DEC-081/DEC-082.
3. **`content/`** (Rol 4): es el productor único del contenido C4.
4. ~~Archivos bloqueados por la integración en curso.~~ **Ya se desbloquearon:**
   el PR #8 se fusionó a `main` el 2026-10-15. `backend/app/api/runtime.py`,
   `backend/requirements*.txt`, `backend/tests/test_priority.py` y
   `backend/fixtures/` quedan disponibles para el apoyo (son el punto de partida
   de la tarea B1).

**Convenciones:**

- Una rama y un PR por tarea, con nombre claro. No acumular varias cosas en una
  sola rama: el equipo pidió ver avance parcial.
- Pruebas siempre con `py -3.11 -m pytest -q` desde `backend/`. El `python` del
  shell apunta a un entorno sin pytest.
- Antes de empezar, `git fetch` y partir desde lo último. Nunca `--force`,
  `reset --hard`, `clean -fd` ni reescribir historia ajena.

---

## 6. Límites del producto que no se negocian

Aplican a todos, en cualquier tarea:

- La **elegibilidad la decide el motor determinista y trazable**. La IA solo
  redacta y explica; nunca decide si una familia califica.
- **Nunca prometer**: "podría calificar", "vale la pena consultar". El aviso de
  orientación referencial va en toda salida.
- **Nada de datos personales hacia la IA**: ni nombres, identificadores,
  domicilio, contacto, nacionalidad, diagnósticos ni códigos. El filtro por
  allowlist se aplica antes de cualquier servicio, y falla cerrado.
- **Datos de demo 100% sintéticos y rotulados.** Ningún dato real entra al
  repositorio ni a la cuenta del evento.
- Los **logs** registran identificador de petición, ruta, estado y latencia.
  Nunca cuerpos, preguntas, respuestas ni valores de campos.

---

## 7. Contexto de la contraparte (para entender el "por qué")

Respuestas de Fundación Integra del 2026-10-15 que definen el alcance actual:

- La herramienta es **para la tía**, para que ella informe al apoderado.
- Debe generar el resultado **rápido, con pocos datos clave**.
- El momento es la **matrícula presencial** en el jardín.
- El dolor real: *"la familia a veces no tiene idea de todos los beneficios a los
  que puede acceder dada su situación"*.
- Los beneficios deben ser **territorializados**.
- El puntaje de la ficha es solo para asignar cupos: *"no es un tema relevante
  para el desafío"*.
- **No hace seguimiento** del trámite.
