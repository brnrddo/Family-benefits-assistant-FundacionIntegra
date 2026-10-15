"""KPI real con ``E3_MOCK=0`` (B3, DEC-080): sube con una conversación y no duplica.

Material 100 % sintético (``SYNTHETIC_DEMO_NOT_A_REAL_PERSON``).
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import motor_real, runtime
from app.api.app import app
from app.api.deps import SNAPSHOT_ID
from app.api.routers import tracking
from tests.c3_schema import validar

client = TestClient(app)
_FAMILIA = "FAM-SIM-E3-00001"


@pytest.fixture(autouse=True)
def _modo_real(monkeypatch, db_motor_path: Path):
    monkeypatch.setenv("E3_MOCK", "0")
    monkeypatch.setattr(runtime, "DB_PATH", db_motor_path)
    monkeypatch.setattr(tracking, "_IDEMPOTENCIA", {})
    motor_real.limpiar_cache()
    yield
    motor_real.limpiar_cache()


def _kpi(**params) -> dict:
    r = client.get("/api/v1/kpi", params=params)
    assert r.status_code == 200, r.status_code
    body = r.json()
    validar("KpiEnvelope", body)
    return body["data"]


def _conversar(benefit_ids: list[str]) -> None:
    r = client.post(
        f"/api/v1/familias/{_FAMILIA}/conversaciones",
        json={
            "benefit_ids": benefit_ids,
            "next_step": "NONE",
            "channel": "IN_PERSON",
            "occurred_at": "2026-10-15T12:00:00Z",
            "snapshot_id": SNAPSHOT_ID,
            "origin": "REAL_DEMO",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 201, r.status_code


def test_kpi_real_sube_y_no_duplica():
    snap = motor_real.obtener_snapshot()
    assert snap is not None
    jardin = motor_real.garden_de(snap, _FAMILIA)
    top = [o["benefit_id"] for o in snap.familias[_FAMILIA]["opportunities"][:3]]

    nac0, jar0 = _kpi(nivel="nacional"), _kpi(nivel="jardin", id=jardin)
    assert nac0["total_families"] == len(snap.familias)
    assert jar0["total_families"] == len(snap.familias_por_jardin[jardin])
    assert nac0["informed_families"] == jar0["informed_families"] == 0
    assert jar0["informed_percentage"] == 0.0
    assert jar0["opportunity_coverage_percentage"] is None  # divisor cero
    assert jar0["informed_new_percentage"] is None

    _conversar(top)
    _conversar(top[:1])  # segunda conversación de la misma familia
    nac, jar = _kpi(nivel="nacional"), _kpi(nivel="jardin", id=jardin)
    assert nac["informed_families"] == jar["informed_families"] == 1
    assert jar["informed_percentage"] == round(100 / jar["total_families"], 1)
    assert jar["opportunity_coverage_percentage"] == round(
        100 * len(top) / len(snap.familias[_FAMILIA]["opportunities"]), 1
    )
    # Coherente con la barra de avance del jardín.
    garden = next(
        j for j in client.get("/api/v1/jardines").json()["items"] if j["garden_id"] == jardin
    )
    assert garden["families_informed"] == 1
