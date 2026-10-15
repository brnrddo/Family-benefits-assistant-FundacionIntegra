# Handoff Rol 1 — estado al cierre de la sesión

> Para retomar mañana sin releer todo. Rol 1 = datos y motor de elegibilidad.
> Rama de trabajo: `rol1/datos-motor-contexto-genai` (sincronizada con origin).

## Estado en una línea
MUST del Rol 1 **completo y verde**: 91 tests passed, `ruff` limpio, precálculo
< 30 s, rama subida. Falta la ficha digital (S2) y pulidos documentados.

## Cómo levantar el entorno (desde `backend/`)
```bash
python -m app.loader.load          # genera e3.db desde los CSV
python -m app.db.build_views       # precálculo + 4 vistas de cruce (~20 s)
pip install -r requirements-dev.txt
python -m pytest -q                # 91 passed (~30 s)
python -m ruff check app tests     # limpio
```
Nota: `e3.db` es efímera (no se versiona). Comandos de shell en PowerShell:
usar `python -` con here-strings `@"..."@` para scripts largos (los `-c` con
comillas fallan por el escaping de PowerShell).

## Lo que se hizo (módulos clave)
- `app/db/` — `build_views.py` materializa `evaluaciones` + `accesos` (10.000
  filas) y crea vistas `v_familia_beneficio`, `v_oportunidades`, `v_brechas`,
  `v_ventanas`. Índices base antes del loop para cumplir < 30 s.
- `app/access/service.py` — estado de acceso (8 estados) + cupo BEN-018
  (`SIN_CUPO`, ranking inseguridad↓/ingreso↑/id).
- `app/context/` — `ficha_sintetica.py`, `contexto_familia.py` (contrato C2),
  `context_filter.py` (allowlist hacia el LLM), `sanitizer.py` (resiliencia a
  datos sucios → `inconsistencias` + `calidad_datos`).
- `app/engine/evaluator.py` — REF_EQ/`binding_padre` (BEN-016) y fix de traza
  en bindings EXISTS sin ganador.
- `app/genai/` — `LLMProvider` + `StubProvider` (sin AWS) + esqueleto
  `BedrockProvider` para Rol 2. `boto3` en requirements.

## Contratos que entrega Rol 1 (congelados)
- **C1** salida del motor → tabla `evaluaciones` / vista `v_familia_beneficio`.
- **C2** `contexto_familia` → filtrar SIEMPRE con
  `context_filter.filtrar_para_llm` antes del LLM.

## Verificación de robustez hecha (resultado)
Se pasó un dataset recién generado por `data/generador.py` por el backend:
- **0 excepciones** del motor sobre 10.000 evaluaciones.
- El generador es determinista (misma salida con cualquier semilla).
- 37,7 % de coincidencia con `elegibilidad_esperada.csv`; el resto son
  divergencias **legítimas** por arquetipo/campos ausentes (spec §12.3), NO bugs.
- Bug real hallado y corregido: traza vacía en binding EXISTS sin ganador.

## PENDIENTE para mañana (orden sugerido)
1. **Ficha digital → hechos DECLARADO → reevaluación** (único MUST pendiente;
   soporta S2 / KPI #2). Nuevo módulo tipo `app/context/ficha_digital.py`:
   recibe campos que llena la tía → inserta hechos `estado_dato=DECLARADO,
   acreditada=false` → reevalúa → resultados PRELIMINAR. Conecta con
   `genai/caracterizador.py` (texto libre → hechos declarados).
2. **Sembrar 3 familias demo** verificadas (brecha, discapacidad, sin RSH) en un
   `backend/demo/`. Las familias ~91–230 son arquetipo "brecha".
3. **KPIs SQL** sobre las vistas (cobertura, top brechas por comuna, monto
   potencial). Determinista, NO con LLM.
4. **Dockerfile** que hornee `e3.db` (loader + build_views) para App Runner/Lambda.

Ganchos de motor documentados en `ROADMAP_ROL1.md` (G1–G5): bindings ACCESO para
BEN-004, fecha_contexto, montos por FORMULA/MAP, exponer politica_perdida.

## Decisiones y temas abiertos con el equipo
- **SQLite** (no DuckDB): decisión documentada; `e3.db` viaja horneada en el
  contenedor AWS (solo lectura).
- **Ubicación de GenAI**: `main` dice que Bedrock va en `ia/`, no en `backend/`.
  Dejamos solo interfaz+stub+esqueleto en `backend/app/genai/`. Pendiente que el
  dueño de `ia/`/Rol 2 decida si se mueve. (Anotado en la descripción del PR.)
- **PR a main**: abrir desde
  https://github.com/brnrddo/Aws-breaking-barriers---10-/pull/new/rol1/datos-motor-contexto-genai
  (descripción ya redactada en la conversación; aún no se ha abierto el PR).

## Git / entorno
- Rama: `rol1/datos-motor-contexto-genai` (al día con origin).
- `main` avanzó esta sesión (specs y contratos oficiales en `.kiro/specs/`);
  ya se integró a la rama. Hay ramas de compañeros: `api`, `docs/specs-...`.
- `.gitattributes` agregado → finales de línea normalizados (resuelto el
  problema de diffs fantasma CRLF/LF). Si alguien ve archivos "modificados" sin
  tocarlos: `git add --renormalize . && git commit`.
- `PROYECTO_3_ESPECIFICACION.local.bak` es backup local; NO subir.
