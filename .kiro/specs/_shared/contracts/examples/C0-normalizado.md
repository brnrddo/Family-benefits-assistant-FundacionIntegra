# Ejemplos C0

DATOS SINTETICOS - NO CORRESPONDEN A UNA PERSONA REAL

Caso válido estructural:

```json
[{"campo_origen":"edad_en_anios","nivel_privacidad":"CONTEXTO_MINIMO_LLM","campo_motor":"edad","uso":"MOTOR","tipo":"INTEGER","permitido_llm":true,"justificacion":"Edad por rol, sin identificador, requerida por el motor.","responsable_revision":"ROL_4"}]
```

Caso adversarial: una fila con columnas extra, `campo_origen` duplicado o un campo excluido marcado como permitido debe fallar. `permitido_llm=true` nunca basta para incluir el valor: la única allowlist runtime es `LlmContextV1`.
