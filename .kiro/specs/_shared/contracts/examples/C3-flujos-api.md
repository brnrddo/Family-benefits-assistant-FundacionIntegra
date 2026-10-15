# Flujos C3

DATOS SINTETICOS - NO CORRESPONDEN A UNA PERSONA REAL

1. Rol 3 lista `/api/v1/jardines?limit=25`, conserva `snapshot_id` y usa `next_cursor` sin interpretarlo.
2. Lee oportunidades de `FAM-SIM-0001`; si hashes o snapshot cambian, recibe `409` y refresca.
3. Registra una conversación sintética con `Idempotency-Key` UUID. Misma clave y body devuelve el mismo registro; otro body devuelve `409`.
4. Solicita guion o mensaje enviando solo `benefit_ids` autorizados. El servidor obtiene C1/C2/C4, selecciona catálogo y prompt, y recién entonces construye el `FamilyGenerationRequestV1` interno.
5. La respuesta de mensaje contiene `whatsapp_preview` y `PrintableCard` (`CARD_V1`) con texto/citas tipados; nunca transporta HTML, CSS, atributos, handlers ni URLs libres. Rol 3 escapa los strings y decide todo el markup con una plantilla propia.
6. `/asistente` acepta solo `question`; catálogo, recuperación y prompt son internos. Una consulta individual responde `intent=REQUIRES_DETERMINISTIC_EVALUATION` sin Bedrock.
7. Cada ruta responde un schema funcional cerrado: jardines, familias, ficha, contexto, oportunidades, guion, mensaje, conversación, preevaluación, KPI, asistente o borrador de afiche.
8. La preevaluación acepta propiedades tipadas y enumeradas de la ficha; no acepta un mapa `facts` ni claves arbitrarias.
9. El afiche acepta solo `TextractFlyerRequestV1`; bytes, base64, URL, asset no inventariado o claves extra producen rechazo antes de Textract.

Casos adversariales del mensaje: strings con `<script>`, atributos `on*`, CSS/URLs embebidas o markup malformado no se interpretan como markup. Citas ajenas a C4 o no HTTPS se rechazan y se usa fallback seguro. Guardrails no sustituye estos controles.

Auth adversarial: sin token o con token de identidad se rechaza; un access token requiere emisor, vigencia, `client_id` y scope exactos. Fuera de scope se responde `404` para no revelar existencia.
