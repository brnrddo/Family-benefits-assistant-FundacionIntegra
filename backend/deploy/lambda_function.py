"""Punto de entrada de la Lambda: arranque en frío + adaptador ASGI (Mangum).

Lambda no corre un servidor, corre una función. El backend sí es un servidor
ASGI (FastAPI). ``Mangum`` es el traductor: recibe el evento JSON del API
Gateway (HTTP API), lo convierte en una petición que FastAPI entiende y
devuelve la respuesta en el formato que el gateway espera. Por eso el
``--handler`` de la función es ``lambda_function.handler``.

Este archivo se versiona en ``backend/deploy/`` y ``build_lambda.sh`` lo copia a
la RAÍZ del zip. En ejecución queda en ``/var/task/lambda_function.py``, con
``backend/``, ``content/`` y ``.kiro/`` como hermanos: el backend lee el
contrato C3 y el bundle C4 por rutas derivadas de ``__file__``, así que ese
layout es parte del contrato de despliegue.

Qué hace, en orden (todo en la fase INIT, antes del primer request):

1. deja ``/var/task/backend`` en ``sys.path`` para que ``import app...`` funcione;
2. sube a INFO solo los loggers propios (el runtime deja el root en WARNING y
   se perderían los logs ya saneados de la app);
3. baja la SQLite **sintética** desde S3 a ``/tmp`` si hay bucket configurado;
4. construye ``handler``.

Privacidad (``docs/PRIVACIDAD_DEMO.md``): los mensajes de log son códigos fijos.
Nunca se registra el nombre del bucket, la key, el valor de una variable
``E3_*`` ni ``str(exc)`` (el texto de botocore incluye bucket y key).
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("brujula.bootstrap")

# Raíz del paquete desplegado: /var/task en Lambda.
_RAIZ = Path(__file__).resolve().parent
_BACKEND = _RAIZ / "backend"

# Key fija del objeto en S3 (copia SINTÉTICA del snapshot del motor). No es
# configurable a propósito: coincide con la política IAM del rol de la función
# (<bucket>/snapshots/*) y no agrega una variable más que documentar.
_DB_S3_KEY = "snapshots/e3.db"

# /tmp es el único directorio escribible del runtime de Lambda.
_DB_DEFECTO = "/tmp/e3.db"

# Loggers propios que suben a INFO. No se toca el root ni los de terceros.
_LOGGERS_PROPIOS = ("brujula.bootstrap", "app.api")


def preparar_sys_path() -> None:
    """Hace importable el paquete ``app`` (vive en ``/var/task/backend/app``)."""
    ruta = str(_BACKEND)
    if ruta not in sys.path:
        sys.path.insert(0, ruta)


def subir_nivel_logs() -> None:
    """Deja en INFO los loggers propios para que CloudWatch los reciba.

    El runtime de Python deja el root logger en WARNING, así que el access log
    saneado de ``app.api`` (request_id, método, ruta normalizada, status,
    latencia: justo lo que PRIVACIDAD_DEMO permite) se descartaría. Esto cambia
    el NIVEL, no QUÉ se loguea: el saneo lo sigue haciendo la app.
    """
    for nombre in _LOGGERS_PROPIOS:
        logging.getLogger(nombre).setLevel(logging.INFO)


def preparar_db_sintetica() -> None:
    """Copia ``<bucket>/snapshots/e3.db`` a ``E3_DB_PATH`` si hace falta.

    - Sin ``E3_DB_S3_BUCKET`` no hace nada (modo mock o DB ya presente).
    - Si el archivo destino existe, no baja nada: el contenedor viene reciclado.
    - La descarga va a un ``.parcial`` y se renombra con ``os.replace``
      (atómico): un timeout a medio camino nunca deja una DB truncada.
    - Si falla, **no** propaga la excepción: lanzarla rompería el import y toda
      la API respondería 502, incluido ``/healthz``. El backend ya está diseñado
      para degradar a mocks (``runtime_degradado_a_mock``); el error queda en
      CloudWatch como ``e3_db_descarga_fallida`` para que se vea antes de
      presentar.
    """
    bucket = os.environ.get("E3_DB_S3_BUCKET")
    if not bucket:
        logger.info("e3_db_sin_bucket")
        return

    if not os.environ.get("E3_DB_PATH"):
        # app/config.py buscaría backend/e3.db (read-only e inexistente en
        # /var/task) y la API degradaría a mocks en silencio.
        logger.warning("e3_db_path_no_definida")

    destino = Path(os.environ.get("E3_DB_PATH") or _DB_DEFECTO)
    if destino.exists():
        logger.info("e3_db_presente")
        return

    parcial = destino.with_name(destino.name + ".parcial")
    try:
        import boto3  # import perezoso: solo si de verdad hay que bajar la DB

        destino.parent.mkdir(parents=True, exist_ok=True)
        boto3.client("s3").download_file(bucket, _DB_S3_KEY, str(parcial))
        os.replace(parcial, destino)
        logger.info("e3_db_descargada bytes=%d", destino.stat().st_size)
    except Exception as exc:  # noqa: BLE001 - el arranque no puede romperse
        try:
            parcial.unlink(missing_ok=True)
        except OSError:
            pass
        # Solo la CLASE de la excepción: su texto incluye bucket y key.
        logger.error("e3_db_descarga_fallida error=%s", type(exc).__name__)


preparar_sys_path()
subir_nivel_logs()
preparar_db_sintetica()

# Imports después del bootstrap: `app` solo es importable con el sys.path de
# preparar_sys_path(), y app.api.app lee el contrato C3 al importarse.
from mangum import Mangum  # noqa: E402
from app.api.app import app  # noqa: E402

# lifespan="off": el lifespan de FastAPI no aplica en Lambda. Costo conocido: no
# corre el precalentamiento del snapshot del motor, así que el primer request de
# datos lo paga (~4-5 s medidos en local; cabe en --timeout 29).
handler = Mangum(app, lifespan="off")
