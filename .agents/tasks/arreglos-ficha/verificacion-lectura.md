# Verificación · lo declarado persiste en las lecturas GET (Persona A)

Fecha: 2026-10-15. Worktree `.worktrees/ficha-orden`, rama `arreglos-ficha-orden`, sin commit (paso posterior). Datos 100 % sintéticos.

## Cambio

- `backend/app/api/motor_real.py` (de A, punto único):
  - `_reconstruir(family_id, campos)`: núcleo que ya usaba el POST, ahora devuelve (familia, prioridades, órdenes). `reconstruir_familia_declarada` (POST) delega en él, así que POST y GET usan la misma reevaluación (DEC-081/DEC-082: nivel máximo SI PRELIMINAR, acceso recalculado en memoria).
  - `_contexto_declarado`: C2 sale de la DB y no conoce lo declarado. Un campo declarado con valor conocido sale de `missing_codes` del contexto. Un "No sé" (null) no llega en `campos` y sigue faltando. `rsh_band`/`income_band` se reflejan igual que `aplicar_declarados` (mock).
  - `_vigente(snap, id)`: si `antecedentes_store` tiene hechos para la familia, devuelve la ficha reevaluada (caché por huella del snapshot + campos canónicos, máximo 256 entradas, se limpia con `limpiar_cache`). Sin hechos, o si la reevaluación no puede operar, devuelve el snapshot como antes.
  - `vista_familia`, `contexto` y `oportunidades` pasan por `_vigente`, lo que cubre GET familia, contexto y oportunidades. **No se tocó ningún router**: `familias.py` ya llamaba a estas funciones.
  - `resumen_familia` (lista del jardín) sigue saliendo del snapshot: el orden de la lista es la prioridad estática `familias_por_jardin`. Reordenar habría que hacerlo en `routers/jardines.py`, que no es de A, así que no es un cambio trivial. Tampoco cambian `estados_oportunidades` (allowlist de guion/mensaje) ni `runtime.py` (contexto GenAI); siguen con el snapshot.
- Nada se escribe en `e3.db` ni en el snapshot; lo declarado se pierde al reiniciar. El modo mock (`E3_MOCK=1`) no cambia. No se agregaron logs.
- Tests: `tests/test_antecedentes_gestacion.py::test_embarazo_declarado_persiste_en_lecturas` (nuevo). `tests/conftest.py` suma la fixture autouse `_antecedentes_store_limpio`, que vacía el store antes y después de cada test.
- Sin cambios en C3-api.openapi.yaml, genai/, auth/, infrastructure/ ni frontend. La forma de las respuestas es la misma; solo cambian valores.

## Test rojo → verde

- Rojo (antes de implementar): `py -3.11 -m pytest -q tests/test_antecedentes_gestacion.py` (cwd `backend`), EXIT 1:
  `FAILED tests/test_antecedentes_gestacion.py::test_embarazo_declarado_persiste_en_lecturas` con `AssertionError: assert ('INDETERMINA...NDETERMINADO') == ('SI', 'PRELI...N_ASIGNACION')`, `1 failed, 2 passed, 1 warning in 25.83s`. La causa es la esperada: GET devolvía el precálculo.
- Verde: `py -3.11 -m pytest -q tests/test_antecedentes_gestacion.py tests/test_api_motor_real.py tests/test_api_antecedentes.py`, EXIT 0: `129 passed, 3 warnings in 66.99s`.

## Suites (una vez, al final)

- `py -3.11 -m pytest -q` (cwd `.worktrees/ficha-orden/backend`), EXIT 0:
  `535 passed, 5 warnings in 233.51s (0:03:53)`. Los warnings son `jsonschema.RefResolver` deprecado, de tests.
- `npm run check` (cwd `.worktrees/ficha-orden/frontend`), EXIT 0:
  `Test Files  44 passed (44)`, `Tests  408 passed (408)`, `built in 1.14s`, `check:budget OK`.

## Ensayo con backend real (`E3_MOCK=0`, loopback)

uvicorn en `127.0.0.1:8000` con `E3_MOCK=0` y `backend/e3.db`, más `vite --mode api` con `VITE_PROPOSAL_ADD_INFO=true` en `127.0.0.1:5173`. Script Playwright temporal fuera del repo, ya borrado. Servidores cerrados al terminar. Viewport de 360 px, familia sintética FAM-SIM-E3-00364.

Pasos: entrar como tía demo → buscar "antonella" → ficha → "Datos del hogar" → "Agregar información" → embarazo Sí, ¿20 semanas o más? Sí, otra cobertura No → enviar → **recargar la página** → abrir "Datos del hogar".

Salida del script:

```
antes: Subsidio Maternal en apply = 0
antes: "Datos del hogar" menciona embarazada = true
tras POST: Subsidio Maternal en apply = 1
tras recarga: Subsidio Maternal en apply = 1
tras recarga: Subsidio Maternal en missing = 0
tras recarga: "Datos del hogar" menciona embarazada = false
GET /familias/{id}: BEN-003 = SI PRELIMINAR ELEGIBLE_SIN_ASIGNACION
GET /familias/{id}/contexto: pregnancy en missing_codes = false
GET /familias/{id}/oportunidades: BEN-003 = SI PRELIMINAR ELEGIBLE_SIN_ASIGNACION
scrollWidth = 360
captura guardada
errores de página = 0; respuestas API >= 400 = 0
```

Las tres líneas `GET` son `fetch` directos al backend, sin caché del front. Captura: `ensayo/cierre-05-recarga.png` (360 × 4895): Subsidio Maternal está en "Puede postular ahora" y "Datos por confirmar" no menciona embarazo.

## No verificado / pendiente

- La lista y el ranking del jardín (`GET /jardines/{id}/familias`) siguen con la prioridad del snapshot. Hacerlo coherente requiere tocar `routers/jardines.py`.
- Guion/mensaje (`estados_oportunidades`) y el contexto GenAI (`runtime.py`) no ven lo declarado.
- Con varios workers, cada uno tiene su propio store (limitación ya documentada en `antecedentes_store.py`).
