# Cómo se ordenan las "3 cosas para conversar"

Este documento explica, en palabras simples, los números de `pesos_priorizacion.yaml` (y los de KPI y accesibilidad del manifiesto). Estos valores **solo ordenan** la lista: deciden qué beneficio se conversa primero y qué familia del jardín aparece arriba. **Quién califica a un beneficio lo decide el motor determinista (Rol 1), nunca estos números ni la IA.**

Lo que la especificación (§8) no fija se decidió en DEC-041 a DEC-044 o se calculó desde el dataset sintético E-3. Son valores sintéticos de demo, no normativos, y se revisan con Integra antes del perfil Escala. Los decimales se escriben con punto, igual que en el archivo; los montos van en pesos sintéticos.

DATOS SINTETICOS - NO CORRESPONDEN A UNA PERSONA REAL

## Los tres ejes

Cada beneficio de una familia recibe tres notas de 0 a 1:

- **Urgencia (U):** ¿se pierde algo si no se conversa esta semana? Se toma la señal más alta (por ejemplo, una emergencia reciente o inseguridad alimentaria). Si no hay ninguna, vale 0.2.
- **Beneficio para la familia (B):** ¿cuánto le cambia el año? Se compara lo que entrega el beneficio en un año con el ingreso anual del hogar. Si el beneficio equivale al 20 % del ingreso o más, B vale 1.
- **Vulnerabilidad del hogar (V):** ¿qué tan vulnerable es el hogar? Es la misma para todos los beneficios de la familia y sirve también para ordenar la lista del jardín.

Con esas notas se calcula el puntaje de cada beneficio:

```text
puntaje = peso del estado × (1 + bonus por acción) × (0.4·U + 0.4·B + 0.2·V)
```

Y la prioridad de la familia en la lista del jardín:

```text
prioridad = suma de los 3 mejores puntajes + 3 × V + bonus si no ha sido conversada + bonus si es familia nueva
```

## Valores y de dónde salen

"Fuente §8, línea L…" es una cita literal de `docs/especificacion/PROYECTO_3_ESPECIFICACION_v2.md`. "Calculado del dataset E-3" es un cálculo reproducible sobre `data/publico/`. "DEC-04x" es una decisión registrada en `.kiro/specs/_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md`.

### Pesos de los ejes y del puntaje

| Valor | Cuánto | Origen | Por qué |
|---|---|---|---|
| Peso de U, B y V | 0.4 / 0.4 / 0.2 | Fuente §8, línea L540 | La urgencia y el beneficio pesan igual; la vulnerabilidad desempata. |
| Peso por estado de acceso | 10 elegible sin asignación, 7 gestión rechazada, 6 pendiente de antecedentes, 5 indeterminado, 2 gestión en curso, 1 sin cupo, 0 asignado | Fuente §8, líneas L537 y L538 | Primero lo que la familia puede pedir ya; lo que ya tiene vale 0. |
| Indeterminado resoluble | con 1 pregunta | Fuente §8, línea L538 | Solo cuenta si basta una pregunta para aclararlo. |
| Bonus por acción | +1 (duplica el puntaje) | Fuente §8, línea L539 | Sube lo que la familia tiene que hacer; lo automático no necesita conversación. |

### Urgencia (U)

| Valor | Cuánto | Origen | Por qué |
|---|---|---|---|
| Cómo se combinan las señales | la más alta | Fuente §8, línea L503 | Basta una señal fuerte. |
| Emergencia familiar reciente (BEN-020) | 1.0 si ocurrió hace 60 días o menos | Fuente §8, línea L506 | Es lo más urgente. |
| Recién nacido (BEN-008) | crece a medida que pasan los 90 días | Fuente §8, línea L507 | Se pierde si no se pide a tiempo. |
| Documento de terapia por vencer (BEN-019) | crece a medida que pasan los 90 días | Fuente §8, línea L508 | Igual que el anterior. |
| Cupo limitado | 0.8 | Fuente §8, línea L509 | Puede agotarse. |
| Inseguridad alimentaria | 0.8 si el índice es 3 o más | Fuente §8, línea L510 | Necesidad básica. |
| Vivienda precaria (campamento o toma) | 0.7 | Fuente §8, línea L511 | Situación de riesgo. |
| Ventana de postulación | 1.0 si cierra en 7 días o menos; 0.6 si cierra en 30 | Fuente §8, línea L512 | Plazo por vencer. |
| Usar la ventana | no (apagado) | Fuente §8, línea L515 | En el dataset casi todas las ventanas cierran el mismo día. |
| Sin ninguna señal | 0.2 | Fuente §8, línea L513 | Valor base. |

### Beneficio para la familia (B)

| Valor | Cuánto | Origen | Por qué |
|---|---|---|---|
| Anualizar montos | mensual × 12, anual × 1, pago único × 1 | Fuente §8, línea L519 | Todo se compara en un año. |
| Nota máxima | si el beneficio es el 20 % del ingreso anual o más | Fuente §8, línea L521 | Sobre ese nivel ya cambia mucho el año. |
| Ingreso por defecto | $315.150 al mes | Calculado del dataset E-3 (DEC-041) | Mediana del ingreso del hogar de las 500 familias. Se usa si no hay ingreso ni mediana del jardín. |
| Ingreso mediano por jardín (50 jardines) | de $307.800 a $322.500 al mes | Calculado del dataset E-3 (DEC-041) | Si falta el ingreso de la familia se usa la mediana de su jardín y B se marca como estimado. Lista completa en `pesos_priorizacion.yaml`. |
| Programa de Alimentación Escolar (BEN-007) | $360.000 al año | DEC-041 | Cerca de $2.000 por ración por 180 días hábiles. |
| Apoyo Biopsicosocial (BEN-009) | $150.000 al año | DEC-041 | 6 controles al año (dato de las versiones V017 y V018) por $25.000. |
| Útiles Escolares (BEN-015) | $40.000 al año | DEC-041 | Un set al año. |
| Apoyo al Recién Nacido (BEN-008) | $250.000 | DEC-041 | Un kit único (cantidad 1, entrega única). |
| Subsidio de agua (BEN-005) | $168.000 al año | Calculado del dataset E-3 (DEC-041) | Descuento de 70 % de la versión vigente V010 × boleta mediana de $20.000 × 12, redondeado a miles. |

Reglas de cálculo, en palabras:

- La mediana es el valor del medio; si hay un número par de familias, es el promedio de los dos del medio. Se redondea al peso.
- Se usa el ingreso del hogar vigente al 13 de octubre de 2026 (una fila por familia). Se asume que es **mensual** (SUP-045): los datos no lo dicen de forma explícita, pero la especificación lo usa así.
- Para el agua se simplifica: no se considera el tope de consumo. Por eso es una equivalencia aproximada.
- BEN-016 no necesita equivalencia: su monto lo entrega el motor según el tramo de ingreso.
- **BEN-010 (Bono de Protección) no tiene monto ni equivalencia** (PREG-048). Su monto depende de los meses de permanencia. No se inventó un valor; queda pendiente.

El cálculo se puede repetir y el validador local lo vuelve a hacer. Usa estos archivos (sha256 con fin de línea LF, igual a `data/MANIFEST_PARTICIPANTES.sha256`):

| Archivo | sha256 |
|---|---|
| `data/publico/antecedentes_familia.csv` | `16e147a897daa858e67e51b7256b6f1c36867ea60a5d8e20e2a7b1500b9c1287` |
| `data/publico/familias.csv` | `fcded15d9eb91e2ba3fed342449be5e57897fff434d7b4821d20f2946a91a374` |
| `data/publico/jardines.csv` | `30ce0ff03b209eda963ad5944857fb19f00692bb49bf045383e130008502bef4` |
| `data/publico/beneficios_versiones.csv` | `f2b830d89b866c54f3a7c91192938135a911250c396c265f5e86d7047cb1b3f8` |
| `data/publico/parametros_version.csv` | `ab440cf9dd149c597e11871d0e96b26dae24e5ce00201ecab7f6f955d3346c1c` |

### Vulnerabilidad del hogar (V)

| Valor | Cuánto | Origen | Por qué |
|---|---|---|---|
| Tramo del Registro Social de Hogares | 40 → 1.0; 50 → 0.85; 60 → 0.7; 70 → 0.4; 80 → 0.2; 90 y 100 → 0; sin registro → 0.8 | Fuente §8, línea L528 | A menor tramo, más vulnerable. |
| Ingreso por persona: menos de $110.000 | 1.0 | Fuente §8, línea L529 | Extremo más vulnerable. |
| Ingreso por persona: de $110.000 a $250.000 | 0.67 | DEC-042 | Tercios entre los extremos de la fuente. |
| Ingreso por persona: de $250.000 a $400.000 | 0.33 | DEC-042 | Tercios entre los extremos de la fuente. |
| Ingreso por persona: más de $400.000 | 0 | Fuente §8, línea L529 | Extremo menos vulnerable. |
| Peso del tramo del registro | 0.3 | DEC-042 | Casi todas las familias lo tienen. |
| Peso del ingreso | 0.3 | DEC-042 | Casi todas las familias lo tienen. |
| Peso de la previsión de salud | 0.1 | DEC-042 | Señal de la ficha; puede faltar. |
| Peso del puntaje final de la ficha (CSE, de 0 a 34) | 0.1 | DEC-042 | Señal de la ficha; puede faltar. |
| Peso de jefa de hogar en programa SernamEG | 0.1 | DEC-042 | Señal de la ficha; puede faltar. |
| Peso de niño o niña con posible discapacidad | 0.1 | DEC-042 | Señal de la ficha; puede faltar. |
| Fondo Nacional de Salud (FONASA) tramo A o sin previsión | 1.0 | DEC-042 | La fuente nombra ambos juntos como señal (L530). |
| Puntaje CSE "alto" | 20 o más → 1.0 | Fuente §8, línea L530 ("alto" = mayor o igual) y DEC-042 (umbral 20) | Umbral sintético de demo. |
| Jefa de hogar en SernamEG | 1.0 si está | DEC-042 | Señal presente = máxima. |
| Posible discapacidad | 1.0 si está | DEC-042 | Señal presente = máxima. |
| Señales desconocidas | no cuentan | Fuente §8, línea L532 | No se castiga a quien tiene menos datos. |

Los seis pesos suman 1.0.

### Prioridad de la familia

| Valor | Cuánto | Origen | Por qué |
|---|---|---|---|
| Puntajes que se suman | los 3 mejores | Fuente §8, línea L546 | Coincide con las "3 cosas para conversar". |
| Multiplicador de V | 3 | Fuente §8, línea L547 | Sube a los hogares más vulnerables. |
| Bonus si la familia no ha sido conversada | 5 | DEC-043 | Reordena familias parecidas sin pasar por encima de una oportunidad fuerte (que vale hasta 20). |
| Bonus si es familia nueva | 3 | DEC-043 | Menor que el anterior. |
| Familia nueva | 30 días o menos | Fuente §8, línea L549 | Definición de la fuente. |

### KPI y accesibilidad (manifiesto)

| Valor | Cuánto | Origen | Por qué |
|---|---|---|---|
| Mínimo de familias por celda de un reporte | 5 | DEC-044 | Si una celda tiene menos de 5 familias no se muestra, para no identificar a nadie. |
| Máximo de días por consulta de KPI | 90 | DEC-044 | Un trimestre basta para la demo. |
| Largo máximo de texto para audio (Polly) | 1500 caracteres | DEC-044 | Mensajes cortos. El servicio sigue apagado y sin evidencia. |
| Largo máximo de texto para traducir (Translate) | 1500 caracteres | DEC-044 | Igual que el anterior. Sigue apagado y sin idiomas aprobados. |

Además, `content/.gitattributes` (DEC-045) deja los archivos de `content/` con fin de línea LF para que sus sha256 no cambien en Windows.

## Señales que no se conocen

Una señal que no se conoce no suma ni resta: V se calcula solo con las señales conocidas, repartiendo el peso entre ellas.

- **Previsión de salud:** FONASA A o sin previsión = 1. Otra categoría conocida (FONASA B, C o D, o ISAPRE) = 0. Si no se sabe, queda fuera. (Nota para Rol 2: esto no cambia contratos; solo indica cómo leer la señal).
- **Puntaje CSE de la ficha (0 a 34):** 20 o más = 1; menos de 20 = 0; sin dato, fuera.
- **SernamEG y posible discapacidad:** presente = 1; se sabe que no = 0; sin dato, fuera.

En el dataset E-3 estas cuatro señales no existen, así que hoy V usa solo el tramo del registro y el ingreso por persona.

## Ejemplo con una familia sintética

Familia `FAM-SIM-E3-00091`, del jardín `JAR-SIM-E3-00041`. Los estados de acceso son **hipotéticos**, solo para mostrar la cuenta; no son un resultado del motor.

1. **Vulnerabilidad.** Ingreso del hogar $267.300 al mes, 4 integrantes: $66.825 por persona (menos de $110.000) → 1.0. Tramo 50 → 0.85. Sin señales de ficha. V = (0.3 × 0.85 + 0.3 × 1.0) / 0.6 = **0.925**.
2. **Urgencia.** Índice de inseguridad alimentaria 3 → U = **0.8**.
3. **Beneficio.** Ingreso anual $3.207.600.
   - Subsidio Familiar (BEN-001): $22.000 al mes → $264.000 al año → B = (264.000 / 3.207.600) / 0.20 = **0.41**.
   - Bono Base Familiar (BEN-011): $55.000 al mes → $660.000 al año, más del 20 % del ingreso → B = **1** (tope).
   - Si faltara el ingreso se usaría la mediana del jardín ($319.800): B estimado de 0.34 para BEN-001 y 0.86 para BEN-011.
4. **Puntajes** (perfil hipotético):
   - BEN-001, elegible sin asignación y requiere acción: 10 × 2 × (0.4 × 0.8 + 0.4 × 0.41 + 0.2 × 0.925) ≈ **13.39**.
   - BEN-011, elegible sin asignación y automático: 10 × 1 × (0.32 + 0.4 + 0.185) = **9.05**.
   - Alimentación Escolar (BEN-007), ya asignado: **0**.
5. **Prioridad.** 13.39 + 9.05 + 0 + 3 × 0.925 ≈ **25.22**. Si no ha sido conversada: ≈ **30.22**. Si además es familia nueva: ≈ **33.22**.

## Qué dice el chequeo de sensatez

Se aplicaron los valores a las 500 familias sintéticas con el mismo perfil hipotético. No apareció ningún resultado degenerado:

- **V** no es igual para todos: va de 0.335 a 1.0 (cuartiles 0.685, 0.85 y 0.925) con 10 valores distintos. Si una familia tuviera las cuatro señales de ficha, su V subiría (por ejemplo de 0.85 a 0.91); si se supiera que no las tiene, bajaría (a 0.51).
- **B** distingue beneficios: con el ingreso por defecto va de 0.05 (Útiles) a 1 (solo 2 de 18 llegan al tope). Las equivalencias valen entre 0.13 y 1.14 meses de ingreso mediano.
- **Bonus:** la prioridad sin bonus va de 10.5 a 25.6. Los dos bonus juntos (8) son menores que ese rango y que el puntaje de una oportunidad fuerte (11.7 en la familia mediana). Dentro de un jardín, el bonus de familia no conversada sube en promedio 2.3 puestos de 10. Con un perfil idéntico para todas las familias, ese bonus lleva al primer lugar a 206 de 500 familias. Con estados de acceso reales, que varían entre familias, el efecto debería ser menor.

## Qué revisar con Integra

- SUP-045: que el ingreso del hogar del dataset sea mensual (es una inferencia).
- Las equivalencias de BEN-007, BEN-008, BEN-009 y BEN-015, y la simplificación del subsidio de agua BEN-005 (sin tope de consumo).
- Los pesos de V y el umbral CSE de 20.
- Los bonus 5 y 3. El chequeo muestra que reordenan bastante dentro de un jardín cuando las familias se parecen.
- El mínimo de 5 familias por celda y los 90 días (PREG-007 en el perfil Escala).
- El límite de 1500 caracteres para audio y traducción.
- BEN-010 sin monto ni equivalencia (PREG-048).
- En el dataset los ingresos son muy parecidos entre jardines (de $307.800 a $322.500), así que usar la mediana del jardín casi no cambia B.
- En el ejemplo la inseguridad alimentaria se aplica a todos los beneficios de la familia. Rol 2 decide cómo implementarlo.
- `content/.gitattributes` (DEC-045).
