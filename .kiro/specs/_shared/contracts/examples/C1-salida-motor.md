# Ejemplos C1

DATOS SINTETICOS - NO CORRESPONDEN A UNA PERSONA REAL

Caso válido resumido (los hashes se abrevian solo en esta explicación; un fixture ejecutable deberá usar 64 hexadecimales): familia `FAM-SIM-0001`, beneficio `BEN-001`, resultado `SI`, nivel `PRELIMINAR`, estado `PENDIENTE_ANTECEDENTES`, motivo `EVIDENCIA_DECLARADA` y fuente `F004`.

Invariantes: `NO`/`INDETERMINADO`/`NO_APLICA` llevan `nivel=null`; una traza conserva operador y resultado; C1 completo nunca se envía a Bedrock.

Caso adversarial: dos condiciones satisfechas por entidades distintas no forman un binding ganador y no pueden producir `SI`. Un hash distinto de `CONTROL/ACTIVE` debe cerrar la lectura con conflicto.
