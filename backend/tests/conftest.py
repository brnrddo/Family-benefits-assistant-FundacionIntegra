"""Fixtures compartidas de los tests del backend."""
from __future__ import annotations

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


@pytest.fixture()
def conn(db_path: Path):
    """Conexión SQLite de solo lectura a la DB de prueba."""
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.close()
