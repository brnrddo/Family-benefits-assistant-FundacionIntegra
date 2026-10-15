# Ejemplos C2

DATOS SINTETICOS - NO CORRESPONDEN A UNA PERSONA REAL

```json
{"data_classification":"SYNTHETIC_DEMO_NOT_A_REAL_PERSON","id_familia":"FAM-SIM-0001","fuente":"FICHA_SINTETICA","hechos":[{"campo":"rsh.band","valor":40,"estado_dato":"DECLARADO","acreditada":false}],"procedencia":[{"campo":"rsh.band","fuente":"FICHA_SINTETICA"}],"inconsistencias":[],"no_informado":["child.last_health_control_date"],"senales_urgencia":{"vivienda_precaria":false},"senales_vulnerabilidad":{"rsh_score":1},"formato_preferido":"TEXTO","idioma_mensaje":"es"}
```

`campo`, `valor`, `no_informado`, inconsistencias y ambos grupos de señales usan vocabularios cerrados con tipos, enums, rangos y longitudes. No existen mapas EAV abiertos ni strings libres para hechos.

Caso adversarial: contacto, identificadores civiles, diagnósticos, nacionalidad, una clave desconocida o texto libre deben fallar contra el schema. Aun un C2 válido se transforma campo por campo a `LlmContextV1`; no se envía completo a IA.
