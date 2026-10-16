"""Embarazo declarado en "Agregar información" con el motor real (Tarea 2).

Familia sintética ``FAM-SIM-E3-00002``: BEN-003 llega INDETERMINADO porque el
dataset no trae gestación. Al declarar embarazo, semanas >= N y sin cobertura
incompatible, BEN-003 pasa a SI PRELIMINAR / ELEGIBLE_SIN_ASIGNACION (nunca
CONFIRMADO, nunca 503). N sale del parámetro versionado ``P006-02``.

Todo el material es sintético (``SYNTHETIC_DEMO_NOT_A_REAL_PERSON``).
"""
from __future__ import annotations

import sqlite3
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import antecedentes_store as store  # noqa: E402
from app.api import motor_real, runtime  # noqa: E402
from app.api.app import app  # noqa: E402

client = TestClient(app)

_FAMILIA = "FAM-SIM-E3-00002"
_ROTULO = "SYNTHETIC_DEMO_NOT_A_REAL_PERSON"


@pytest.fixture(scope="module", autouse=True)
def _cache_limpio():
    motor_real.limpiar_cache()
    yield
    motor_real.limpiar_cache()


@pytest.fixture(autouse=True)
def _modo_real(monkeypatch, db_motor_path: Path):
    monkeypatch.setenv("E3_MOCK", "0")
    monkeypatch.setattr(runtime, "DB_PATH", db_motor_path)
    store.reset()
    yield
    store.reset()


def _ben(items: list[dict], bid: str) -> dict:
    return next(i for i in items if i["benefit_id"] == bid)


def test_embarazo_declarado_aplica():
    antes = client.get(f"/api/v1/familias/{_FAMILIA}")
    assert antes.status_code == 200
    assert _ben(antes.json()["data"]["benefit_results"], "BEN-003")["result"] == "INDETERMINADO"

    r = client.post(
        f"/api/v1/familias/{_FAMILIA}/antecedentes",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "data_classification": _ROTULO,
            "household_pregnancy": True,
            "pregnancy_weeks_at_least_threshold": True,
            "has_incompatible_coverage": False,
        },
    )
    assert r.status_code != 503
    assert r.status_code == 200, r.status_code
    ben = _ben(r.json()["data"]["benefit_results"], "BEN-003")
    assert ben["result"] == "SI"
    assert ben["level"] == "PRELIMINAR"  # dato declarado: nunca CONFIRMADO
    assert ben["access_state"] == "ELEGIBLE_SIN_ASIGNACION"
    assert ben["missing_codes"] == []


def test_embarazo_declarado_persiste_en_lecturas():
    """Tras el POST, las rutas GET (motor real) devuelven la ficha reevaluada.

    Memoria del proceso (``antecedentes_store``): el autouse ``_modo_real`` la
    vacía antes y después de cada test.
    """
    r = client.post(
        f"/api/v1/familias/{_FAMILIA}/antecedentes",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "data_classification": _ROTULO,
            "household_pregnancy": True,
            "pregnancy_weeks_at_least_threshold": True,
            "has_incompatible_coverage": False,
        },
    )
    assert r.status_code == 200, r.status_code

    ficha = client.get(f"/api/v1/familias/{_FAMILIA}")
    assert ficha.status_code == 200
    ben = _ben(ficha.json()["data"]["benefit_results"], "BEN-003")
    assert (ben["result"], ben["level"], ben["access_state"]) == (
        "SI", "PRELIMINAR", "ELEGIBLE_SIN_ASIGNACION")

    ctx = client.get(f"/api/v1/familias/{_FAMILIA}/contexto")
    assert ctx.status_code == 200
    assert "pregnancy" not in ctx.json()["data"]["missing_codes"]

    # Lo ya declarado se expone como nombres de campo (sin valores) para no volver a preguntarlo.
    ant = client.get(f"/api/v1/familias/{_FAMILIA}/antecedentes")
    assert ant.status_code == 200
    assert ant.json()["data"]["declared_fields"] == [
        "has_incompatible_coverage", "household_pregnancy", "pregnancy_weeks_at_least_threshold"]


def test_umbral_semanas_expuesto(db_motor_path: Path):
    conn = sqlite3.connect(db_motor_path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        esperado = int(conn.execute(
            "SELECT valor_int FROM parametros_version WHERE id_parametro = 'P006-02'"
        ).fetchone()[0])
    finally:
        conn.close()

    r = client.get(f"/api/v1/familias/{_FAMILIA}/antecedentes")
    assert r.status_code == 200, r.status_code
    data = r.json()["data"]
    assert data["family_id"] == _FAMILIA
    assert data["pregnancy_weeks_threshold"] == esperado
    assert isinstance(data["pregnancy_weeks_threshold"], int)
    assert data["declared_fields"] == []
