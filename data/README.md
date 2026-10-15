# Dataset sintético E-3

Entrega aprobada de Fase 2. Contiene **500 hogares**, **20 beneficios** (17 estatales y 3 privados sintéticos), 1700 integrantes y 10.000 evaluaciones finales. Todo es sintético y no determina derechos ni reemplaza fuentes oficiales.

El contrato vigente del proyecto está en la [especificación](../docs/especificacion/PROYECTO_3_ESPECIFICACION_v2.md).

## Fuente canónica

Los **23 CSV de `publico/`** son la fuente canónica. Una ficha familiar se construye relacionando familias, integrantes, RSH, antecedentes, condiciones por integrante, relaciones, catálogo, reglas y gestiones; ninguna tabla aislada contiene toda la información.

`publico/dataset_e3.json` sirve para inspección y mocks, pero **no debe ser la fuente única**: omite `publico/condiciones_integrante.csv`. Una carga completa debe leer los CSV.

Un dato ausente o vacío significa que no está informado y puede producir `INDETERMINADO`; no debe transformarse en `false` ni en cero. `false`, cero y vacío son valores distintos.

## Estructura

- `publico/`: 23 CSV normalizados y `dataset_e3.json`; no contiene respuestas.
- `interno_no_distribuir/_meta/`: respuestas, trazabilidad de evaluaciones y reporte cuando ese paquete está disponible.
- `participantes_e3.zip`: paquete público reproducible cuando está disponible.
- `NO_DISTRIBUIR_A_PARTICIPANTES_e3.zip`: paquete interno rotulado cuando está disponible.
- `generador.py` y `validador.py`: herramientas de biblioteca estándar con semilla fija `20261013`.

Este checkout no necesariamente incluye los ZIP ni el área interna; su ausencia no autoriza a reconstruir o inventar respuestas.

## Ejecutar las herramientas

```bash
/usr/bin/python3 generador.py --output-root .
/usr/bin/python3 validador.py --output-root . --verificar-reproducibilidad
```

El generador solo reemplaza sus subdirectorios y artefactos conocidos. Los ZIP usan orden, fecha y permisos normalizados. Ejecútelo únicamente cuando una tarea de datos lo requiera; no es parte de la reorganización documental.
