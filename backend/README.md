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
