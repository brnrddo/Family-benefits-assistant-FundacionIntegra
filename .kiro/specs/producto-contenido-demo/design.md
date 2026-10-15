# Diseño — Rol 4 Producto, contenido y demo

**Owner futuro:** `content/`, slides, guion y video; rama `contenido`. Produce [C0](../_shared/contracts/C0-mapeo-ficha.schema.json) y [C4](../_shared/contracts/C4-contenido-manifest.schema.json); entrega a Roles 1–3. Trabaja solo con CSV/JSON/YAML/Markdown y revisión en celular, sin Python/TypeScript.

C0 contiene metadatos, nunca valores. Las cuatro clases siguen [privacidad](../../../docs/PRIVACIDAD_DEMO.md). Cambiar la allowlist LLM requiere nueva versión de `LlmContextV1`, no una bandera C0.

C4 referencia archivos de clases obligatorias `WEIGHTS`, `QUESTIONS`, `BENEFITS`, `PROMPT`, `ACCESSIBILITY` e `I18N`, además del inventario sintético opcional. Su ranking cerrado cubre: pesos de ejes; todas las señales, umbrales, ventanas y score base de U; anualización, divisor, equivalencias y medianas de B; ponderaciones y mapeos RSH/ingreso/señales de V; los siete pesos de estado, bonus y pregunta resoluble; top, multiplicador, bonus y ventana de prioridad familiar. Pesos U/B/V suman 1; bandas/ventanas se ordenan y no se solapan; `use_window=false` inicial; C4 no reemplaza parámetros E-3.

La futura tarea `API-T14` implementará `python -m backend.app.contracts.validate_content --manifest content/manifest.yaml` para schema, rutas, hashes, clases obligatorias, referencias entre archivos, suma, rangos, estados y condiciones de accesibilidad. Rol 4 corrige el bundle; no escribe el validador.

Prompts declaran variables, no aceptan texto de cliente y exigen salida estructurada/aviso. Para mensajes solicitan únicamente `PrintableCard`: título, introducción y secciones de texto/citas. Nunca solicitan HTML, CSS, atributos, handlers ni URLs libres. Citas deben corresponder a fuentes HTTPS inventariadas; Rol 3 decide tags, estilos e iconos mediante plantilla propia.

Polly/Translate empiezan deshabilitados y con listas vacías. Solo una nueva versión/hash C4 puede habilitarlos, con `VERIFICADO_EN_CUENTA`, ID sanitizado de smoke test, al menos una voz/idioma autorizado, límites y claves de fallback español. Sin esas condiciones el bundle falla cerrado.

Revisión humana: frases ≤20 palabras, trato de usted, siglas explicadas, fuentes oficiales HTTPS, “podría/vale la pena consultar”, contraste y comprensión. Demo identifica datos/siembras sintéticas, muestra fallback, estado AWS y no confunde vista previa WhatsApp con envío. Afiche opcional queda `PENDIENTE_REVISION`. Estado actual: diseño documental; contenido runtime/pitch aún pendientes.
