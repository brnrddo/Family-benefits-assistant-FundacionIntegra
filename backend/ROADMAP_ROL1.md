# Roadmap del Rol 1 — ganchos y mejoras futuras

Lo que el MUST del Rol 1 **ya cumple** está en `README.md`. Este documento lista
lo que quedó **documentado como gancho** (no implementado) y por qué, para que
quien siga tenga el camino claro. Cada ítem indica: qué es, dónde está el dato,
qué falta, y si vale la pena.

> Criterio: solo se implementó lo que afecta la **elegibilidad** (mandato del
> Rol 1). Lo que afecta solo el **monto** o el **contenido** se dejó como gancho
> porque es frontera con el Rol 2 y no cambia quién califica.

---

## ✅ Implementado en esta ronda
- **REF_EQ / `binding_padre`** (BEN-016 Asignación Familiar): el `CAUSANTE_1`
  debe ser *carga acreditada* del `BENEFICIARIO_1`. El evaluador ahora ordena
  los bindings (padre antes que hijo) y resuelve la relación `CARGA_DE`
  acreditada y vigente. Ver `evaluator._carga_acreditada_de`.

---

## 🪝 Ganchos documentados (no implementados)

### G1 · Bindings `ACCESO_*` en el motor (BEN-004 Aporte Familiar) — media/alta
**Qué es:** BEN-004 califica por OR de 3 grupos, cada uno un binding `ACCESO_n`
que pregunta "¿la familia tuvo SUF / Asignación Familiar / Subsistema SSyO
activo al 31-12-2025?".
**Dato:** `accesos_previos_hogar` + gestiones (`postulaciones` + último estado).
**Hoy:** el motor marca los bindings `ACCESO_*` como INDETERMINADO ("sin
candidatos") → BEN-004 siempre INDETERMINADO en M2. (El cruce de accesos se hace
parcialmente en M3 para otros fines, no para BEN-004.)
**Falta:** un resolvedor de "candidatos ACCESO" que lea `accesos_previos_hogar`
y las gestiones, aplicando la **fecha de contexto** (ver G2).
**¿Vale la pena?** Sí, media/alta: es 1 de 20 beneficios pero es un arquetipo de
demo. Esfuerzo medio. Riesgo: tocar el evaluador; cubrir con tests.

### G2 · `id_parametro_fecha_contexto` en `ACTIVE_ON_DATE` — media (depende de G1)
**Qué es:** 6 reglas de BEN-004 traen `id_parametro_fecha_contexto` (apunta a un
parámetro con la fecha de corte 31-12-2025) para evaluar la vigencia a esa fecha
en vez de la fecha de evaluación.
**Hoy:** `op_active_on_date` usa la fecha de evaluación (la vigencia se filtró
con ella al resolver el hecho).
**Falta:** cuando una regla trae `id_parametro_fecha_contexto`, resolver la
vigencia del hecho a esa fecha.
**¿Vale la pena?** Solo tiene efecto junto con G1 (hoy BEN-004 ya es IND por los
bindings ACCESO). Implementar junto a G1.

### G3 · Monto por `FORMULA` — media (frontera con Rol 2)
**Qué es:** 4 parámetros definen el monto con fórmulas, p. ej.
`min(tope,(umbral-ingreso_pc)*factor)` (subsidio de agua, decrece con ingreso) y
`0.10*ingreso_minimo_sim*18`.
**Dato:** `parametros_version` con `tipo_valor='FORMULA'`, `valor_texto` = la
fórmula; las variables (`ingreso_pc`, `tope`, `umbral`, `factor`) son otros
parámetros de la misma versión o campos derivados.
**Hoy:** `monto_estimado` usa siempre `monto_referencial_sintetico` (fijo).
**Falta:** un evaluador de fórmulas seguro (no `eval()`) que sustituya variables
y calcule. Afecta solo el **monto**, no la elegibilidad.
**¿Vale la pena?** Media para el pitch (monto potencial más realista, eje
"Beneficio" §8). Es más de Rol 2. Dejar como mejora.

### G4 · Monto por `MAP` (tramo de edad) — baja/media (frontera con Rol 2)
**Qué es:** 2 parámetros tipo `{"1-6":22000,"7-12":17000,"13-18":12000,...}` —
monto por tramo de edad del causante (BEN-001 SUF).
**Dato:** `parametros_version` con `tipo_valor='MAP'`, `valor_texto` = JSON.
**Hoy:** monto fijo.
**Falta:** elegir el monto según la edad del causante ganador.
**¿Vale la pena?** Baja/media. Igual que G3, afina monto, no elegibilidad.

### G5 · Exponer `politica_perdida` y `advertencia` — baja (trivial)
**Qué es:** columnas de `beneficios_versiones` con la condición de pérdida del
beneficio y advertencias.
**Hoy:** no se exponen.
**Falta:** incluirlas en el checklist / `v_familia_beneficio` para que la tía
(Rol 3) y el contenido (Rol 4) las muestren ("ojo, lo pierde si…").
**¿Vale la pena?** Baja esfuerzo, útil para Rol 2/4. Es solo pasar dos columnas
más; cero lógica nueva.

---

## Resumen para decidir
| Gancho | Afecta | Esfuerzo | Prioridad |
|---|---|---|---|
| G1 bindings ACCESO (BEN-004) | elegibilidad | medio | media/alta |
| G2 fecha_contexto | elegibilidad (con G1) | bajo | media (con G1) |
| G3 monto FORMULA | monto | medio | media (Rol 2) |
| G4 monto MAP | monto | bajo | baja (Rol 2) |
| G5 politica_perdida/advertencia | contenido | trivial | baja |
