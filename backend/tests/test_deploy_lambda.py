"""Tests del entrypoint de la Lambda (``backend/deploy/lambda_function.py``).

Cubre los dos riesgos reales del archivo:

- **romper el arranque en frío**: si la descarga de la SQLite sintética lanza,
  el import del módulo falla y toda la API responde 502 (incluido ``/healthz``);
- **filtrar el nombre del bucket o la key** en un log (PRIVACIDAD_DEMO).

El módulo no es importable como paquete (``backend/deploy`` no lo es) y en local
no está instalado ``mangum`` (es dependencia solo-nube,
``requirements-lambda.txt``). Por eso se carga con ``importlib`` desde su ruta,
inyectando antes un ``mangum`` falso en ``sys.modules``. No toca red ni AWS.
"""
from __future__ import annotations

import ast
import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

LAMBDA_FUNCTION = BACKEND_DIR / "deploy" / "lambda_function.py"

BUCKET_FALSO = "bucket-sintetico-de-prueba"

# Únicas expresiones (aparte del mensaje fijo) que un log del entrypoint puede
# pasar como argumento: la clase de la excepción y el tamaño del archivo.
ARGUMENTOS_PERMITIDOS_EN_LOGS = frozenset({"type(exc).__name__", "destino.stat().st_size"})


class _MangumFalso:
    """Registra con qué se construyó el handler, sin ejecutar nada ASGI."""

    def __init__(self, app, **kwargs):
        self.app = app
        self.kwargs = kwargs


def _modulo_mangum_falso() -> ModuleType:
    modulo = ModuleType("mangum")
    modulo.Mangum = _MangumFalso  # type: ignore[attr-defined]
    return modulo


class _S3Falso:
    """Cliente S3 mínimo: anota la llamada y escribe bytes sintéticos."""

    def __init__(self, registro: list, error: Exception | None = None):
        self._registro = registro
        self._error = error

    def download_file(self, bucket: str, key: str, destino: str) -> None:
        self._registro.append((bucket, key, destino))
        if self._error is not None:
            raise self._error
        Path(destino).write_bytes(b"sqlite sintetica de prueba")


def _modulo_boto3_falso(registro: list, error: Exception | None = None) -> ModuleType:
    modulo = ModuleType("boto3")
    modulo.client = lambda servicio: _S3Falso(registro, error)  # type: ignore[attr-defined]
    return modulo


@pytest.fixture()
def lambda_mod(monkeypatch):
    """Carga ``lambda_function`` aislado: sin bucket, con ``mangum`` falso.

    Restaura al salir los niveles de los loggers que el módulo sube a INFO,
    para no contaminar el resto de la suite.
    """
    monkeypatch.delenv("E3_DB_S3_BUCKET", raising=False)
    monkeypatch.setitem(sys.modules, "mangum", _modulo_mangum_falso())

    niveles = {n: logging.getLogger(n).level for n in ("brujula.bootstrap", "app.api")}
    spec = importlib.util.spec_from_file_location("lambda_function_test", LAMBDA_FUNCTION)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(modulo)
        yield modulo
    finally:
        for nombre, nivel in niveles.items():
            logging.getLogger(nombre).setLevel(nivel)


def test_sin_bucket_no_descarga_nada(lambda_mod, monkeypatch, caplog):
    """Sin ``E3_DB_S3_BUCKET`` no se importa boto3 ni se toca S3."""
    monkeypatch.delenv("E3_DB_S3_BUCKET", raising=False)
    # Un boto3 que explota si alguien lo usa: la prueba es que no se usa.
    explosivo = ModuleType("boto3")
    explosivo.client = lambda servicio: pytest.fail("no debe tocar S3 sin bucket")
    monkeypatch.setitem(sys.modules, "boto3", explosivo)

    with caplog.at_level(logging.INFO, logger="brujula.bootstrap"):
        lambda_mod.preparar_db_sintetica()

    assert "e3_db_sin_bucket" in caplog.text


def test_descarga_la_db_cuando_falta(lambda_mod, monkeypatch, tmp_path):
    """Con bucket y destino ausente: una descarga y el archivo final en su sitio."""
    destino = tmp_path / "e3.db"
    registro: list = []
    monkeypatch.setenv("E3_DB_S3_BUCKET", BUCKET_FALSO)
    monkeypatch.setenv("E3_DB_PATH", str(destino))
    monkeypatch.setitem(sys.modules, "boto3", _modulo_boto3_falso(registro))

    lambda_mod.preparar_db_sintetica()

    assert len(registro) == 1
    bucket, key, parcial = registro[0]
    assert bucket == BUCKET_FALSO
    assert key == "snapshots/e3.db"
    assert parcial.endswith(".parcial")  # se descarga aparte y se renombra
    assert destino.exists()
    assert not Path(parcial).exists()


def test_db_presente_no_vuelve_a_descargar(lambda_mod, monkeypatch, tmp_path):
    """Contenedor reciclado (arranque templado): la DB ya está, no se baja."""
    destino = tmp_path / "e3.db"
    destino.write_bytes(b"sqlite sintetica previa")
    registro: list = []
    monkeypatch.setenv("E3_DB_S3_BUCKET", BUCKET_FALSO)
    monkeypatch.setenv("E3_DB_PATH", str(destino))
    monkeypatch.setitem(sys.modules, "boto3", _modulo_boto3_falso(registro))

    lambda_mod.preparar_db_sintetica()

    assert registro == []
    assert destino.read_bytes() == b"sqlite sintetica previa"


def test_fallo_de_descarga_no_rompe_ni_filtra(lambda_mod, monkeypatch, tmp_path, caplog):
    """Si S3 falla: no propaga, no deja ``.parcial`` y no loguea bucket ni key."""
    destino = tmp_path / "e3.db"
    registro: list = []
    error = RuntimeError(f"falló bajando {BUCKET_FALSO}/snapshots/e3.db")
    monkeypatch.setenv("E3_DB_S3_BUCKET", BUCKET_FALSO)
    monkeypatch.setenv("E3_DB_PATH", str(destino))
    monkeypatch.setitem(sys.modules, "boto3", _modulo_boto3_falso(registro, error))

    with caplog.at_level(logging.ERROR, logger="brujula.bootstrap"):
        lambda_mod.preparar_db_sintetica()  # no debe lanzar

    assert "e3_db_descarga_fallida" in caplog.text
    assert BUCKET_FALSO not in caplog.text
    assert "snapshots/e3.db" not in caplog.text
    assert not destino.exists()
    assert not (tmp_path / "e3.db.parcial").exists()


def test_handler_usa_lifespan_off(lambda_mod):
    """El handler se construye con la app real y sin lifespan (no aplica en Lambda)."""
    assert isinstance(lambda_mod.handler, _MangumFalso)
    assert lambda_mod.handler.kwargs == {"lifespan": "off"}
    assert lambda_mod.handler.app is lambda_mod.app


def test_sys_path_incluye_backend_del_paquete(lambda_mod):
    """El bootstrap inserta ``<raíz del zip>/backend`` para que ``import app`` funcione."""
    esperado = str(lambda_mod._RAIZ / "backend")
    assert esperado in sys.path
    assert lambda_mod._DB_DEFECTO == "/tmp/e3.db"


def test_warning_si_falta_e3_db_path(lambda_mod, monkeypatch, tmp_path, caplog):
    """Sin ``E3_DB_PATH`` el destino es /tmp y queda avisado en el log."""
    monkeypatch.setenv("E3_DB_S3_BUCKET", BUCKET_FALSO)
    monkeypatch.delenv("E3_DB_PATH", raising=False)
    registro: list = []
    monkeypatch.setitem(sys.modules, "boto3", _modulo_boto3_falso(registro))
    # No se escribe en /tmp durante el test: el destino "existe" y se corta antes.
    monkeypatch.setattr(lambda_mod, "_DB_DEFECTO", str(tmp_path / "e3.db"))
    (tmp_path / "e3.db").write_bytes(b"sqlite sintetica previa")

    with caplog.at_level(logging.WARNING, logger="brujula.bootstrap"):
        lambda_mod.preparar_db_sintetica()

    assert "e3_db_path_no_definida" in caplog.text
    assert registro == []


def test_logs_solo_pasan_argumentos_permitidos():
    """Ningún log del entrypoint ecoa el bucket, la key ni ``str(exc)``.

    Se mira el AST (no el texto) para no confundir el código con los comentarios.
    Cada argumento que no sea el mensaje fijo tiene que estar en la allowlist:
    agregar uno es una decisión de privacidad explícita, no un descuido.
    """
    arbol = ast.parse(LAMBDA_FUNCTION.read_text(encoding="utf-8"))
    llamadas = [
        nodo
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Attribute)
        and isinstance(nodo.func.value, ast.Name)
        and nodo.func.value.id == "logger"
    ]
    assert llamadas, "el entrypoint debe dejar rastro en CloudWatch"
    for llamada in llamadas:
        for argumento in llamada.args:
            if isinstance(argumento, ast.Constant):
                continue  # el mensaje fijo (código de evento)
            assert ast.unparse(argumento) in ARGUMENTOS_PERMITIDOS_EN_LOGS
