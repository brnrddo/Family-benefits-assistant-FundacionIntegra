"""Fixtures compartidas de los tests del backend."""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

# Asegura que `import app...` funcione al correr pytest desde backend/.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.loader.load import construir_db  # noqa: E402


@pytest.fixture(scope="session")
def db_path(tmp_path_factory) -> Path:
    """Construye una DB de prueba efímera desde los CSV reales del repo.

    Se crea en un directorio temporal (no toca backend/e3.db) y se reconstruye
    con force=True para garantizar un estado limpio.
    """
    destino = tmp_path_factory.mktemp("e3db") / "e3_test.db"
    construir_db(db_path=destino, force=True)
    return destino


@pytest.fixture(scope="session")
def db_motor_path(db_path: Path, tmp_path_factory) -> Path:
    """Copia de ``db_path`` con el precálculo del Rol 1 (``build_views``, ~20 s).

    Es la DB que sirve el motor real de la API (``E3_MOCK=0``). Se construye una
    sola vez por sesión sobre una copia: ``db_path`` queda solo con el loader.
    """
    from app.db.build_views import construir

    destino = tmp_path_factory.mktemp("e3db_motor") / "e3_motor.db"
    shutil.copyfile(db_path, destino)
    construir(destino)
    return destino


@pytest.fixture(autouse=True)
def _e3_mock_por_defecto(monkeypatch):
    """Cada test parte del default ``E3_MOCK=1``; los tests de modo real hacen setenv."""
    monkeypatch.delenv("E3_MOCK", raising=False)


@pytest.fixture(autouse=True)
def _runtime_sin_db_local(monkeypatch, tmp_path_factory):
    """Aísla los tests de un ``backend/e3.db`` local del desarrollador.

    Con ``E3_MOCK=0`` y sin una DB propia del test, la API degrada a mocks como
    en un entorno limpio. Los tests que necesitan DB apuntan
    ``runtime.DB_PATH`` a la suya.
    """
    from app.api import runtime

    monkeypatch.setattr(
        runtime, "DB_PATH", tmp_path_factory.getbasetemp() / "sin-db-local" / "e3.db"
    )


@pytest.fixture(autouse=True)
def _genai_sin_bandera_local(monkeypatch):
    """Aísla la suite de un ``E3_LLM_PROVIDER`` exportado en la terminal.

    Sin esto, un desarrollador con la bandera puesta vería la API intentando
    Bedrock en tests que esperan el camino de plantilla.
    """
    from app.genai import redaccion

    monkeypatch.delenv("E3_LLM_PROVIDER", raising=False)
    redaccion.reiniciar_proveedor()


@pytest.fixture()
def conn(db_path: Path):
    """Conexión SQLite de solo lectura a la DB de prueba."""
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.close()
