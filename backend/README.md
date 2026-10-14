# Backend — Apoyo Inteligente para Familias (Desafío 3 Integra)

API y lógica del servidor. Aquí vive el motor de elegibilidad, el estado de
acceso, la capa de IA generativa y las pantallas HTML servidas por FastAPI.

Stack: **Python 3.11+** · **FastAPI** · **SQLite** (biblioteca estándar para el loader).
Frontend: **HTML + CSS + JavaScript** servidos por FastAPI (sin framework ni bundler).

---

## M1 — Loader del dataset E-3 a SQLite

El loader carga los **23 CSV públicos** de `../data/publico/` en una base SQLite
(`backend/e3.db`), una tabla por archivo (nombre de tabla = nombre de archivo sin `.csv`).

### Enfoque "SQL directo"
- Todas las columnas se cargan como **TEXT**. Las fechas ISO (`2026-10-13`) se
  comparan correctamente como texto, lo que evita problemas de parsing. Donde una
  consulta necesite un número se usa `CAST` puntual.
- Los valores vacíos del CSV se cargan como **NULL** (no como cadena vacía).
- Lectura explícita en **UTF-8** (en Windows el default puede no serlo), de modo
  que los acentos (p. ej. "Automático") quedan correctos.
- El consolidado `dataset_e3.json` **no** se carga a una tabla; queda como archivo
  para el frontend si se necesita.

### Base de datos efímera
`backend/e3.db` **no se versiona** (está en `.gitignore` como `*.db`). Se regenera
desde los CSV cuando haga falta. Nunca la subas a git.

### Fecha de evaluación
Configurable en `app/config.py` (`FECHA_EVALUACION`, default `2026-10-13`; corte
exclusivo `2026-10-14`). Se puede sobrescribir con la variable de entorno
`E3_FECHA_EVALUACION`. También `E3_DB_PATH` para cambiar la ruta de la DB.

---

## Cómo generar la DB

Desde la carpeta `backend/`:

```bash
# (opcional) crear entorno virtual
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/mac: source .venv/bin/activate

# El loader M1 solo usa la stdlib; no requiere instalar nada.
python -m app.loader.load          # crea e3.db si no existe
python -m app.loader.load --force  # reconstruye desde cero
```

Imprime un resumen con los conteos por tabla. Conteos esperados: 500 familias,
1700 integrantes, 20 beneficios, 41 versiones, 151 reglas, etc.

## Cómo correr los tests

```bash
pip install -r requirements-dev.txt   # instala pytest
pytest                                # desde backend/
```

Los tests construyen una DB de prueba en un directorio temporal (no tocan
`e3.db`) y verifican: creación de las 23 tablas, conteos de filas, join
familia↔integrantes, encoding UTF-8, versión vigente de BEN-001 (= V002),
BEN-016 con 3 versiones, y que los vacíos quedan como NULL.

---

## M2 — Motor de elegibilidad (determinista)

Responde **"¿esta familia califica a este beneficio?"** con lógica de tres
valores (`SI` / `NO` / `INDETERMINADO`), nivel de confianza
(`CONFIRMADO` / `PRELIMINAR`), traza regla-por-regla y entidad ganadora.
**No decide estado de acceso** (eso es M3) ni usa IA.

Módulos en `app/engine/`:
- `model.py` — tipos (`Tri`, `Nivel`, `Hecho`, `TrazaRegla`, `ResultadoBeneficio`).
- `operators.py` — operadores atómicos presentes en las reglas: `EQ, LT, LTE,
  GT, GTE, IN, BETWEEN, ACTIVE_ON_DATE, RANGE_LOOKUP, COUNT_REL_GTE,
  NOT_EXISTS_WITHIN` (+ `REF_EQ` parcial).
- `facts.py` / `resolver.py` — mapa `campo_dato → origen` (directo / EAV /
  derivado / faltante) y resolución de hechos por hogar/integrante con vigencia
  semiabierta.
- `evaluator.py` — agregación OR entre grupos, AND dentro, cuantificadores
  HOUSEHOLD/EXISTS/COUNT, bindings por rol (misma persona), nivel, monto, traza.
- `service.py` — API de alto nivel: `evaluar_familia(id)` (bajo demanda) y
  `precalcular_todo()` (envoltorio 500×20, ~26 s).

### Uso rápido
```python
from app.engine.service import evaluar_familia
for r in evaluar_familia("FAM-SIM-E3-00100"):
    print(r.id_beneficio, r.resultado.value, r.nivel)
```

### Supuestos sobre datos ausentes (IMPORTANTE)
El dataset no trae algunos datos que ciertas reglas piden. Política:
- **Sin evidencia** → `INDETERMINADO` (se convierte en pregunta para la tía):
  `semanas_gestacion`, `parto_red_publica`, `control_prenatal_red_publica`,
  `residencia_total_anios`, `residencia_ultimos20_anios`, `dias_desde_evento`,
  `documento_terapia_dias`.
- **Con evidencia indirecta** → se asume como `DECLARADO` (no acreditado) y el
  beneficio puede dar `SI` con nivel **PRELIMINAR** (nunca CONFIRMADO). Banderas
  en `config.py`, reversibles por variable de entorno:
  - `SUPONER_ANTECEDENTE_EDAD` (default True): `antecedente_edad_vigente = true`
    si el causante es menor de 18. Habilita **SUF (BEN-001)** y SUF Automático.
  - `SUPONER_CONTROL_VIGENTE` (default True): `dias_desde_control` dentro de
    ventana si el niño tiene control de salud infantil vigente. Habilita el
    Bono Control Niño Sano (BEN-012).

El nivel `PRELIMINAR` es la señal visible de que hubo un supuesto. La traza
muestra siempre el detalle regla-por-regla para auditar la decisión.

### Alcance de M2
Resuelve elegibilidad. Los beneficios que dependen del cruce con accesos
previos / gestiones (BEN-004 Aporte Familiar, BEN-016 Asignación Familiar) o de
datos genuinamente ausentes (BEN-008, 019, 020) quedan `INDETERMINADO` aquí; se
completan en M3 (estado de acceso).
