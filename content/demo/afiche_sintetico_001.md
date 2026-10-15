# Afiche sintético 001 (prueba futura de Textract)

DATOS SINTETICOS - NO CORRESPONDEN A UNA PERSONA REAL

Estado: PENDIENTE_REVISION

## Finalidad

- Activo inventado para una prueba futura de Amazon Textract sobre afiches sintéticos (PREG-008, CONT-011).
- Solo se envía como `TextractFlyerRequestV1` con el `synthetic_asset_id` registrado en `content/demo/inventario_activos.yaml`. Nunca como bytes, base64, URL ni clave S3 del cliente.
- El borrador que entregue Textract nunca se publica ni se convierte en regla de forma automática (DEC-013, CONT-011). Una persona del Rol 4 lo compara con el texto de abajo.
- No deriva de ningún afiche, documento ni persona real. No contiene teléfono, correo, URL, QR, personas ni direcciones.

## Imagen

- Archivo: `content/demo/afiche_sintetico_001.png` (PNG, 1240 × 1754 px, fondo blanco y texto negro en Arial).
- Generado con un script local del workflow, fuera del árbol versionado. El PNG no lleva metadatos de texto.
- Hash, tamaño y dimensiones: ver `content/demo/inventario_activos.yaml`.

## Texto esperado (verdad de referencia)

Una línea por renglón del afiche, de arriba hacia abajo. Los requisitos, fechas, institución y comuna son ficticios.

```text
AFICHE SINTÉTICO - DATOS DE DEMOSTRACIÓN
Programa local inventado
Talleres de Lectura en Familia
Institución: Red Comunitaria Sintética D
Comuna sintética COM-001
Requisitos ficticios:
- Tener un niño o una niña en el jardín
- Asistir con una persona adulta de la familia
- Inscribirse dentro de las fechas
Inscripciones: 2 de marzo al 30 de abril de 2026
Talleres: sábados de mayo a junio de 2026
Consulte en su jardín
AFICHE SINTÉTICO - DATOS DE DEMOSTRACIÓN
```
