# Database

## Objetivo

Definir el esquema, las vistas y las migraciones de la base derivada que relaciona familias, integrantes, RSH, condiciones, beneficios, reglas y gestiones.

- **Dueño:** Ingeniería Mecánica.
- **Colaborador principal:** Ingeniería en Computación consume el contrato desde backend.

## Entradas y salidas

**Entradas:** los 23 CSV canónicos de `data/publico/` y parámetros de carga documentados.

**Salidas:** esquema tipado, migraciones reproducibles y vistas para características, motor, estado de acceso y prioridad.

## Dependencias y límites

Depende de [data](../../../data/README.md). Toda base debe poder reconstruirse desde los CSV; vacío, `false` y cero conservan significados distintos.

No colocar aquí CSV canónicos, archivos `.db`/`.sqlite`, dumps, credenciales, reglas en texto libre ni datos reales. Tampoco crear un motor de elegibilidad paralelo al backend.

Contexto: [especificación](../../especificacion/PROYECTO_3_ESPECIFICACION_v2.md), [roles](../equipo/ROLES_Y_RESPONSABILIDADES.md) y [estructura](../equipo/ESTRUCTURA_REPOSITORIO_INICIAL.md).
