# Ejemplos C4

DATOS SINTETICOS - NO CORRESPONDEN A UNA PERSONA REAL

Un manifiesto válido declara versión/hash y contiene al menos una referencia de cada clase obligatoria: `WEIGHTS`, `QUESTIONS`, `BENEFITS`, `PROMPT`, `ACCESSIBILITY` e `I18N`. `SYNTHETIC_ASSET_MANIFEST` es adicional cuando existe demo territorial. Las rutas son únicas, permanecen bajo `content/` y su SHA-256 coincide con el archivo.

## Ranking cerrado

`ranking` contiene seis bloques sin propiedades extra:

1. `axis_weights`: U/B/V finitos en `[0,1]`, suma 1 con tolerancia `1e-6`.
2. `urgency`: agregación `MAX`, score base, emergencia, recién nacido, documento de terapia, cupo, inseguridad, vivienda y ventanas; Demo inicial usa `use_window=false`.
3. `benefit_impact`: multiplicadores `MENSUAL/ANUAL/UNICA`, divisor de proporción, mediana default y por jardín, y equivalencias anuales por beneficio.
4. `vulnerability`: pesos de componentes; scores de todos los tramos RSH y bandas de ingreso; cobertura, CSE, jefatura y posible discapacidad; desconocidos fuera del denominador.
5. `opportunity_score`: pesos obligatorios de `ELEGIBLE_SIN_ASIGNACION`, `GESTION_RECHAZADA`, `PENDIENTE_ANTECEDENTES`, `INDETERMINADO`, `GESTION_EN_CURSO`, `SIN_CUPO` y `ASIGNADO`, más bonus y límite de pregunta resoluble.
6. `family_priority`: cantidad top, multiplicador V, bonus de no conversada/nueva y días de familia nueva.

## Accesibilidad

El bundle inicial usa `polly.enabled=false` y `translate.enabled=false`, con allowlists vacías y claves i18n de fallback. Una activación válida exige `evidence_state=VERIFICADO_EN_CUENTA`, ID sanitizado del smoke test, al menos una voz o idioma permitido, límite de caracteres y fallback español. Cambiar activación crea nueva versión/hash C4.

Casos adversariales: clase obligatoria ausente, ruta/ID repetido, hash o referencia divergente, suma de ejes distinta de 1, ventana/banda solapada, estado faltante, mediana inexistente sin default, Polly activo sin voz/evidencia, Translate activo sin idioma/evidencia, URL no HTTPS o prompt con variables no declaradas. El futuro `python -m backend.app.contracts.validate_content --manifest content/manifest.yaml` valida estas invariantes entre archivos y falla cerrado; no está implementado en esta fase documental. Ningún archivo C4 puede reemplazar parámetros normativos de elegibilidad.
