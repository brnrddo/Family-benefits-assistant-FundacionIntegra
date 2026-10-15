# Dockerfile — Backend Rol 1 (empaquetado AWS, P2)
#
# Construye una imagen con la base SQLite `e3.db` YA generada y precalculada
# embebida, lista para que el backend (Rol 2, App Runner / Lambda) la lea de
# SOLO LECTURA. Reproduce el pipeline `make data` dentro del build para que
# "la base y el precálculo corran igual en la nube del equipo" (PLAN_ROL1 §0/§6).
#
# IMPORTANTE: el contexto de build es la RAÍZ DEL REPO, no backend/, porque el
# loader lee los CSV desde ../data/publico (ver app/config.py). Construir así:
#
#   docker build -f backend/Dockerfile -t e3-backend .
#   docker run --rm e3-backend \
#       python -c "import sqlite3; print(sqlite3.connect('e3.db').execute('SELECT count(*) FROM evaluaciones').fetchone())"
#   # -> (10000,)
#
FROM python:3.11-slim

# No escribir .pyc y salida sin buffer (logs limpios en el contenedor).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1) Dependencias primero (capa cacheable). Solo requirements de runtime.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# 2) Código del backend y CSV públicos, respetando el layout del repo:
#    /app/backend  (código, e3.db se genera aquí)
#    /app/data/publico  (los 23 CSV que el loader lee)
COPY backend/ ./backend/
COPY data/publico/ ./data/publico/

# 3) Reproducir `make data` en el build: loader (M1) + precálculo/vistas.
#    Al terminar, backend/e3.db queda embebida en la imagen con las 10.000
#    evaluaciones y las vistas de cruce.
WORKDIR /app/backend
RUN python -m app.loader.load --force \
 && python -m app.db.build_views

# 4) Config por entorno (documentada). La DB se sirve de SOLO LECTURA.
#    Rol 2 puede sobrescribir estas variables al desplegar.
ENV E3_DB_PATH=/app/backend/e3.db \
    E3_FECHA_EVALUACION=2026-10-13

# Verificación en build-time: la base debe tener 10.000 evaluaciones.
RUN python -c "import sqlite3; n=sqlite3.connect('e3.db').execute('SELECT count(*) FROM evaluaciones').fetchone()[0]; assert n==10000, n; print('e3.db OK:', n, 'evaluaciones')"

# 5) Comando por defecto: placeholder hasta que Rol 2 defina el server FastAPI.
#    Imprime un resumen de la base embebida (sirve de smoke test del contenedor).
#    Rol 2 reemplazará esto por algo como:
#        CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["python", "-c", "import sqlite3; c=sqlite3.connect('e3.db'); print('evaluaciones:', c.execute('SELECT count(*) FROM evaluaciones').fetchone()[0]); print('accesos:', c.execute('SELECT count(*) FROM accesos').fetchone()[0]); print('vistas listas: v_familia_beneficio, v_oportunidades, v_brechas, v_ventanas')"]
