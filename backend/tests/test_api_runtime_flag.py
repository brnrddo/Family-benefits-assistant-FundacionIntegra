"""Tests de la bandera E3_MOCK y la degradación segura a mocks (FEAT-003).

- Por defecto (sin env) ``E3_MOCK`` está activo: todo responde mock sin DB.
- Con ``E3_MOCK=0`` y sin DB, las rutas degradan a mocks (200) con warning y
  NUNCA lanzan 500.
- Los logs no contienen cuerpos/prompts/respuestas (verificado con caplog).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=True)


def test_mock_por_defecto(monkeypatch):
    monkeypatch.delenv("E3_MOCK", raising=False)
    from app.api import deps

    assert deps.mock_habilitado() is True


def test_e3mock0_sin_db_degrada_sin_romper(monkeypatch, tmp_path):
    """E3_MOCK=0 con DB inexistente: runtime no disponible, pero las rutas no rompen."""
    monkeypatch.setenv("E3_MOCK", "0")
    # Apunta la ruta de DB a un archivo que no existe.
    from app.api import runtime

    monkeypatch.setattr(runtime, "DB_PATH", tmp_path / "no_existe.db")

    assert runtime.runtime_disponible() is False
    assert runtime.warnings_runtime() == ["RUNTIME_DEGRADADO_A_MOCK"]

    # Las rutas siguen respondiendo 200 (degradan a mock), sin 500.
    r = client.get("/api/v1/jardines")
    assert r.status_code == 200
    r2 = client.post(
        "/api/v1/familias/FAM-SIM-0001/guion", json={"benefit_ids": ["BEN-001"]}
    )
    assert r2.status_code == 200


def test_e3mock0_db_presente_runtime_disponible(monkeypatch, tmp_path):
    monkeypatch.setenv("E3_MOCK", "0")
    from app.api import runtime

    db = tmp_path / "e3.db"
    db.write_text("", encoding="utf-8")  # existe (contenido irrelevante aquí)
    monkeypatch.setattr(runtime, "DB_PATH", db)

    # El bundle C4 provisional carga correctamente -> runtime disponible.
    assert runtime.runtime_disponible() is True


def test_logs_no_contienen_cuerpos(monkeypatch, caplog):
    """Ningún log de la API contiene el prompt/pregunta/respuesta."""
    monkeypatch.delenv("E3_MOCK", raising=False)
    secreto = "SECRETO_UNICO_PARA_BUSCAR_EN_LOGS_12345"
    with caplog.at_level(logging.DEBUG):
        r = client.post("/api/v1/asistente", json={"question": secreto})
    assert r.status_code == 200
    # El texto enviado no debe aparecer en ningún registro de log.
    assert secreto not in caplog.text


def test_scope_fuera_de_alcance_404(monkeypatch):
    """Con header de scope declarado sin el scope requerido -> 404 (oculta existencia)."""
    monkeypatch.delenv("E3_MOCK", raising=False)
    r = client.get("/api/v1/jardines", headers={"X-Demo-Scopes": "kpi:read"})
    assert r.status_code == 404


def test_scope_vacio_401(monkeypatch):
    monkeypatch.delenv("E3_MOCK", raising=False)
    r = client.get("/api/v1/jardines", headers={"X-Demo-Scopes": ""})
    # Header presente pero sin scopes declarados -> 401.
    assert r.status_code == 401


def test_scope_correcto_200(monkeypatch):
    monkeypatch.delenv("E3_MOCK", raising=False)
    r = client.get("/api/v1/jardines", headers={"X-Demo-Scopes": "jardines:read"})
    assert r.status_code == 200
