# Diseño — Rol 3 Frontend PWA

**Owner futuro:** `frontend/`; rama `front`. Consume exclusivamente [C3](../_shared/contracts/C3-api.openapi.yaml) y [C4](../_shared/contracts/C4-contenido-manifest.schema.json). `content/i18n/es.json` será fuente canónica importada directamente. No interpreta trazas para recrear reglas ni calcula U/B/V.

Las seis rutas corresponden a: jardín/progreso/lista; familia/top tres/detalle; confirmación en tres toques; ficha nueva con “No sé”; KPI agregado/suprimido; asistente de catálogo. Componentes muestran chips, fuente, faltantes, edad/snapshot, aviso y estado de proveedor. Mocks se generan desde C3 antes del backend real.

La tarjeta imprimible conserva la experiencia del producto sin cruzar markup no confiable. C3 entrega `PrintableCard` con `format_version=CARD_V1`, título, introducción y 1–3 secciones de texto/citas. Un componente propio decide elementos, clases, iconos y layout de impresión; React aplica escape normal a cada string. Se prohíben `dangerouslySetInnerHTML`, parseadores HTML y uso de strings de la API como tag, atributo, estilo o URL. Solo `SourceCitation.url`, validada como HTTPS por C3, puede producir un enlace con atributos seguros definidos por la plantilla. Entradas que parezcan scripts, handlers, CSS/URLs o markup malformado se muestran como texto inerte o provocan estado de error contractual; nunca se ejecutan. La plantilla siempre añade el aviso canónico.

PWA: precache solo app shell/assets. Ficha abierta en memoria. Demo permite IndexedDB solo para datos rotulados sintéticos con snapshot/fecha/TTL y una cola mínima sin texto libre; 201 confirma, 409 refresca, 401 pausa, 503 conserva para reintento manual. KPI no sube en pendiente. Logout limpia. Escala desactiva persistencia/cola hasta aprobación.

Accesibilidad: 360 px, zoom, foco visible, teclado, targets grandes, contraste y semántica; no depender solo de color/emoji. Polly/Translate son mejora recuperable y solo se presentan activos cuando C4 lo declara con evidencia/allowlist válida; siempre queda texto español. Estado actual: diseño documentado; PWA, mocks y pruebas no implementados.
