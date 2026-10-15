# Política de anonimización, clasificación y uso de IA

**Alcance:** Demo E-3 y futuras pruebas sintéticas. Esta política precede a arquitectura, prompts y servicios. Un enmascaramiento parcial no anonimiza. Datos reales y documentos parcialmente ocultos permanecen fuera del repositorio y de la cuenta del evento.

## Clasificación obligatoria

| Clase | Ejemplos permitidos | Tratamiento |
|---|---|---|
| **Permitido al motor** | roles/edades, conteos, banda RSH sin folio, rangos de ingreso, hechos tipados, accesos y señales autorizadas | ID seudónimo, mínimo privilegio, cifrado; en evento solo sintético |
| **Contexto mínimo al LLM** | roles/edades, banda RSH/ingreso, formato, idioma enum y beneficios seguros derivados de C1 | solo [`LlmContextV1`](../.kiro/specs/_shared/contracts/schemas/LlmContextV1.schema.json), allowlist y filtro integral |
| **Local de la tía** | nombre de trato, domicilio/contacto operativo, autorizaciones de retiro, origen de preferencia de idioma | no sube a cloud Demo, logs, contratos ni prompts |
| **Totalmente excluido** | identificadores civiles, folios/QR/códigos vinculables, diagnósticos y salud detallada, judicial/Sename, biometría o datos sin finalidad | no capturar, persistir, mostrar, procesar ni enviar |

También se excluyen secretos, credenciales, tokens, claves, account IDs y endpoints privados. Nacionalidad no entra al motor ni al LLM; solo se transmite un idioma elegido como enum.

## Expediente de ingreso

La Demo recibe únicamente una atestación sintética de etapa y respuestas tipadas permitidas por C0/C2/C3. Nunca recibe el formulario real completado ni RSH personal. Páginas 1–2 y página 3 conservan las mismas fronteras: la habilitación temporal de una página no autoriza nuevos datos.

Los campos `TOTALMENTE_EXCLUIDO` pueden aparecer en C0 solo como metadatos de la plantilla vacía para demostrar revisión; no se capturan, persisten, muestran ni procesan. Datos `LOCAL_TIA` permanecen en el sistema/dispositivo autorizado y no cruzan contratos cloud. Formularios reales, aun parcialmente ocultos, permanecen fuera del repositorio y de la cuenta AWS del evento. La plantilla PDF no se incorpora mientras su redistribución no esté autorizada.

## Barrera previa y GenAI

1. Construir un DTO por allowlist positiva; nunca “limpiar” C1/C2 por exclusión.
2. Validar schema cerrado y serializar canónicamente uno de los dos envelopes de texto.
3. Inspeccionar **todo** el payload boto3 renderizado: claves, tipos, longitudes, URLs y patrones prohibidos. Los envelopes son internos: las rutas C3 de GenAI solo aceptan IDs de beneficios autorizados o una pregunta; las rutas de expediente aceptan únicamente uniones tipadas derivadas de C0. Contexto, catálogo y prompt se cargan en servidor desde C1/C2/C4.
4. Solo después aplicar Guardrails INPUT, Converse, schema/grounding, Guardrails OUTPUT y postvalidación.
5. Ante duda o fallo, cerrar la entrada o usar `TemplateProvider`; nunca relajar campos.

Guardrails es una segunda barrera, no anonimiza. C0 `permitido_llm` es metadato de revisión, no habilita runtime. Macie, si se prueba, solo detecta objetos sospechosos; tampoco anonimiza.

Textract solo puede recibir un asset sintético prepublicado e inventariado mediante `TextractFlyerRequestV1`. No se aceptan bytes, base64, URL ni clave S3 del cliente. Bedrock multimodal, Transcribe y AgentCore requieren decisión y contrato nuevos.

## Rotulado y fixtures

- Markdown de persona/hogar: línea exacta `DATOS SINTETICOS - NO CORRESPONDEN A UNA PERSONA REAL`.
- JSON/YAML de persona/hogar: `data_classification: SYNTHETIC_DEMO_NOT_A_REAL_PERSON`.
- IDs solo sintéticos y explícitos. No derivar fixtures de documentos reales ni usar nombres, identificadores, domicilio, contacto, folios o QR reales.
- Conversaciones Demo llevan `origen=SIMULADO_DEMO` cuando corresponda.

Tarea futura, no implementada en esta fase: `backend/app/contracts/validate_synthetic_examples.py` recorrerá ejemplos Markdown y fixtures JSON/YAML, exigirá los literales anteriores y se integrará a CI.

## Seudonimización, consentimiento y retención

Una futura integración real usaría HMAC-SHA-256 con secreto por ambiente, longitud suficiente y control de colisiones; un hash simple no basta. No habrá tabla de reversión en la nube Demo. El piloto real requiere consentimiento explícito, finalidad, residencia, retención, recuperación, controles de dispositivos y aprobación de Integra.

Los artefactos sintéticos tendrán lifecycle y retención mínima. Logout elimina datos/cola permitidos en dispositivo. En Escala no se persiste contexto familiar en navegador hasta aprobación. Borrado, exportación y recuperación deben definirse antes de material real.

## Logs y evidencia

Se permite: `request_id`, `job_id`, operación, ruta normalizada, código, estado, latencia, versión lógica y métricas agregadas. Se prohíbe: bodies, query libre, prompts, preguntas, respuestas, nombres, identificadores completos, contacto, fichas, tokens o endpoints privados. Errores no ecoan valores. Evidencia AWS registra fecha, región efectiva, operación y resultado sanitizado.

## Procedimiento futuro para material real

1. Trabajar solo en entorno autorizado, fuera de la cuenta del evento.
2. Inventariar finalidad, campos, responsables y retención.
3. Eliminar irreversiblemente identificadores, contacto, domicilio, folios, QR, metadata y páginas innecesarias.
4. Revisar por dos personas y ejecutar prueba de reidentificación.
5. Obtener aprobación del responsable de datos antes de cualquier carga.

El original nunca se incorpora al repositorio ni a la cuenta del evento.
