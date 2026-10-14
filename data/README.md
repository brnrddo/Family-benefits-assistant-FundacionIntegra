# Dataset sintético E-3

Entrega aprobada de Fase 2. Contiene **500 hogares**, **20 beneficios** (17 estatales y 3 privados sintéticos), 1700 integrantes y 10.000 evaluaciones finales. Todo es sintético y no determina derechos ni reemplaza fuentes oficiales.

## Estructura
- `publico/`: CSV normalizados y `dataset_e3.json`; no contiene respuestas.
- `interno_no_distribuir/_meta/`: respuestas, trazabilidad de evaluaciones y reporte.
- `participantes_e3.zip`: paquete público reproducible.
- `NO_DISTRIBUIR_A_PARTICIPANTES_e3.zip`: paquete interno rotulado.
- `generador.py` y `validador.py`: biblioteca estándar, semilla fija `20261013`.

## Ejecutar
```bash
/usr/bin/python3 generador.py --output-root .
/usr/bin/python3 validador.py --output-root . --verificar-reproducibilidad
```
El generador solo reemplaza sus subdirectorios y artefactos conocidos. Los ZIP usan orden, fecha y permisos normalizados.
