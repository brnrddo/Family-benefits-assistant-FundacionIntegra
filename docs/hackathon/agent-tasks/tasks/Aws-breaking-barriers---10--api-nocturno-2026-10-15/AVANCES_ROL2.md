# Avances del Rol 2 (noche del 2026-10-15)

Este documento está escrito para leerse rápido, incluso en voz alta (sirve para
generar un resumen tipo podcast). Explica, en lenguaje simple, qué construimos
anoche en nuestro rol, cómo verlo mañana, qué dejamos fuera a propósito y qué
preguntas conviene llevar a la Fundación. No usa jerga innecesaria.

> Nota de alcance: todo lo que viene son avances de software reales y probados
> en el computador (tests verdes). **Nada de esto corre todavía en AWS.** Lo que
> toca a la nube sigue marcado como "no verificado" y lo explicamos al final.

---

## 1. ¿Qué es el "Rol 2" y qué hicimos anoche?

El proyecto está dividido en roles. Para ubicarnos:

- **Rol 1** construye el "motor": las reglas que, con los datos de una familia,
  dicen si le corresponde o no un beneficio. Eso ya estaba hecho antes de anoche.
- **Rol 2 (nosotros)** construye la **API**: la pieza del medio que conecta ese
  motor con la pantalla. Es como el mesón de una cocina: recibe el pedido de la
  pantalla, va a buscar lo que calculó el motor, lo ordena por prioridad, le pone
  un texto explicativo seguro y lo devuelve listo para mostrar.
- **Rol 3** construye la **pantalla** (la app que usaría la "tía") y consume
  nuestra API.
- **Rol 4** aporta el **contenido**: los textos, los beneficios del catálogo y
  los números con los que se calcula la prioridad.

Lo importante: **anoche avanzamos nuestra parte sin depender de la reunión de
mañana ni de que los otros roles terminen**. Dejamos la API funcionando con datos
de demostración (sintéticos, inventados, no de personas reales), de modo que el
Rol 3 ya puede empezar a conectar su pantalla aunque todavía falten acuerdos.

---

## 2. ¿Qué quedó construido? (en concreto)

Tres bloques, todos con pruebas automáticas en verde:

### a) La API completa con los 12 "flujos" (FEAT-003)
Levantamos una API real (con FastAPI) que publica las 12 operaciones que el
contrato del proyecto define: listar jardines, listar familias de un jardín, ver
la ficha de una familia, ver su contexto, ver sus oportunidades, generar un
guion, generar un mensaje, registrar una conversación, hacer una preevaluación,
ver indicadores (KPI), preguntarle al asistente del catálogo, e ingresar un
afiche sintético.

Cada operación responde con datos de demostración coherentes entre sí (las
familias apuntan a jardines que existen, las oportunidades respetan las reglas,
etc.). Trae su documentación navegable (`/docs`), un chequeo de salud
(`/healthz`) y manejo de errores ordenado y cerrado (nunca "filtra" datos de la
persona en los mensajes de error).

### b) La priorización U/B/V determinista (FEAT-001)
Cuando una familia tiene varias oportunidades, hay que decidir **cuál mostrar
primero**. Lo hacemos con tres ejes:

- **U = Urgencia** (qué tan apremiante es),
- **B = Beneficio/impacto** (cuánto le sirve en plata o en servicios),
- **V = Vulnerabilidad** (qué tan prioritaria es la situación de la familia).

La clave: **ningún número está "a mano" en el código**. Todos los pesos,
umbrales y medianas salen de la configuración de contenido (el "bundle C4").
Hoy usamos un bundle **provisional** marcado como tal, porque la versión final la
entrega el Rol 4. Es "determinista": con los mismos datos siempre da el mismo
orden, y se puede explicar paso a paso. Esto no es inteligencia artificial, son
reglas claras y auditables.

### c) El filtro de privacidad + plantilla sin IA (FEAT-002)
Antes de que cualquier texto se genere, pasamos los datos por un **filtro de
privacidad por "lista blanca"**: solo dejamos pasar lo que está explícitamente
permitido (roles y edades, tramos, idioma como código, los beneficios resueltos)
y bloqueamos de raíz cualquier dato sensible (nombre, RUT, folio, teléfono,
dirección, nacionalidad, diagnósticos de salud, códigos QR). Si algo prohibido
intentara colarse, el sistema se detiene en vez de arriesgarse.

El texto (guion, mensaje, respuesta del asistente) lo arma por ahora un
**generador de plantillas determinista**, sin llamar a ningún modelo de IA en la
nube. Si alguien le pregunta al asistente si "le corresponde" un beneficio en
particular, el sistema **no inventa una respuesta**: contesta que eso lo decide
el motor determinista, no la IA. Y los mensajes imprimibles salen como texto
plano seguro, nunca como código que pudiera ejecutar algo en la pantalla.

Todo lleva un aviso fijo al pie: *"Orientación referencial; no determina
derechos. Confirmar en la institución."*

---

## 3. Cómo verlo mañana (paso a paso)

Desde la carpeta `backend/`, en una terminal, levantar el servidor:

```bash
py -3.11 -m uvicorn app.api.app:app --port 8080 --reload
```

> Importante: usar `py -3.11`, **no** `python` a secas (el `python` del equipo
> apunta a un entorno sin las librerías de prueba).

Luego, en el navegador:

- **`http://localhost:8080/healthz`** → debe responder `{"status": "ok"}`
  (confirma que el servidor está vivo).
- **`http://localhost:8080/docs`** → la documentación navegable de la API; desde
  ahí se pueden probar las 12 operaciones.
- **`http://localhost:8080/api/v1/jardines`** → la lista de jardines de demo.
- **`http://localhost:8080/api/v1/familias/FAM-SIM-0001`** → una familia de demo.

Qué significa **`E3_MOCK=1`** (viene activado por defecto): el servidor responde
con **datos sintéticos de demostración**, sin necesidad de base de datos ni de
AWS. Son datos inventados para mostrar el flujo, no corresponden a personas
reales. Es exactamente lo que necesita el Rol 3 para avanzar con la pantalla hoy.

---

## 4. Qué NO construimos (y por qué)

Lo dejamos fuera **a propósito**, porque depende de la reunión de mañana o de
otros roles. No es un olvido: es evitar construir sobre dudas que se resuelven
mañana.

- **La lógica de "ingreso mínimo" o el puntaje/umbral de la ficha.** No tocamos
  cómo se decide si una familia "entra" por puntaje. La preevaluación de la API
  hoy es solo un mock que responde con nivel "PRELIMINAR"; no decide
  elegibilidad. Esto espera la conversación con la Fundación.
- **Cambios a la ficha de Integra.** No modificamos ni "flexibilizamos" nada de
  la ficha; primero hay que entenderla con la Fundación (ver sección 5).
- **AWS real.** No hay nada corriendo en la nube: ni Cognito (login), ni Bedrock
  (IA), ni despliegue. Todo eso sigue en estado **NO_VERIFICADO** según nuestra
  documentación de arquitectura, porque todavía no hemos probado nada en una
  cuenta de AWS. El diseño está escrito, pero diseño no es lo mismo que "probado
  y funcionando". Mañana es nuestra primera vez con AWS, así que vamos a tratar
  cada servicio como "no verificado hasta que lo probemos de verdad".
- **El contenido final (bundle C4).** Los números de priorización que usamos son
  provisionales; la versión oficial la entrega el Rol 4.

---

## 5. Preguntas para la Fundación (en tono colaborativo)

El objetivo de estas preguntas es **entender bien la ficha para poder ayudar
mejor**, no cuestionar cómo trabaja la Fundación. Lo planteamos desde la
curiosidad y el respeto: queremos acompañar a las personas para que no pierdan un
beneficio por tener información incompleta o por un detalle que no supieron que
importaba.

1. **Cómo acompañan hoy a quien llena la ficha.** Nos interesa entender el
   instrumento: ¿qué pasa cuando a alguien le falta declarar algo que sí le
   corresponde? Por ejemplo, una condición de salud que a veces es invalidante y
   a veces no, y que la persona no siempre recuerda mencionar. ¿Hay espacio para
   que el acompañamiento ayude a declarar la información de forma correcta y
   completa?
2. **El puntaje y los umbrales.** ¿Cómo se maneja hoy el puntaje? ¿Qué tan cerca
   del límite queda la gente? La idea es entender dónde un dato bien declarado
   puede marcar la diferencia entre quedar dentro o fuera de un beneficio.
3. **El costo humano de completar el formulario.** Para una persona de bajos
   recursos, ¿cuánto cuesta (tiempo, traslado, dificultad) llenar la ficha?
   ¿Dónde se traba la gente más seguido? Saber esto nos ayuda a pensar la
   herramienta a su favor, no a sumarle una carga.
4. **Qué pasa cuando falta un dato.** ¿Se puede perder un beneficio por un
   detalle no declarado? ¿Hay forma de revisar o complementar la ficha después?

### Nota de encuadre para el equipo
Esto **complementa** la idea de que la ficha es un requisito mínimo; no la
contradice. Que la ficha sea un mínimo obligatorio y que el acompañamiento ayude
a declarar bien la información son dos cosas que conviven. Nuestro aporte apunta a
lo segundo: que una persona **no pierda un beneficio al que tiene derecho** por
información incompleta o por no saber que cierto dato importaba. No se trata de
"forzar" la ficha ni de inventar datos; se trata de ayudar a declarar, de forma
correcta y completa, lo que es verdad. En eso estamos todos de acuerdo.

---

## 6. Decisiones y preguntas abiertas registradas (contractuales)

Durante la implementación anotamos estos puntos para no cambiar los contratos del
proyecto por nuestra cuenta. Son dudas o decisiones que conviene cerrar con el
equipo y con los roles dueños de cada contrato.

- **DEC (oportunidades solo SI/INDETERMINADO):** una "oportunidad" solo puede
  tener resultado `SI` o `INDETERMINADO`. Los resultados `NO` / `NO_APLICA` no
  llegan a la pantalla como oportunidad. Lo respetamos tal como lo pide el
  contrato C3.
- **PREG (bundle C4 provisional):** los números de priorización que usamos hoy
  son un bundle **provisional**. La versión oficial y definitiva la entrega el
  Rol 4; hay que reemplazarla cuando esté lista.
- **PREG (datos ausentes en el dataset):** señales como la fecha del último
  control de salud o las condiciones de vivienda **no están** en los datos de la
  demo. En los mocks aparecen de forma sintética; en el camino real quedarían
  como "sin dato" (`null`) y no se inventan.
- **PREG (preevaluación sin gate de ingreso):** no implementamos la lógica de
  ingreso mínimo ni ningún "filtro" de la ficha; eso depende de la reunión.
- **NO_VERIFICADO (AWS):** Cognito, Bedrock y el despliegue siguen sin probar en
  cuenta. La autorización actual es un stub de demo (sin login real) y el almacén
  de conversaciones es en memoria del proceso, no una base de datos en la nube.

---

*Resumen de una línea: anoche dejamos la API del Rol 2 funcionando con datos de
demostración, priorización explicable y filtro de privacidad, lista para que la
pantalla se conecte, sin depender de la reunión ni de AWS.*
