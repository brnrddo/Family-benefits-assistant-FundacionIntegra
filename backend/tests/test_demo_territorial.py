"""B2: ficha solo relevante y beneficio territorial SOLO DEMO (propuestas DEC-070..072).

Todo el material es sintético (``SYNTHETIC_DEMO_NOT_A_REAL_PERSON``). El
ejemplo ``BEN-DEMO-LOCAL-01`` es inventado: solo existe en la DB local cuando
se carga con ``app.demo_territorial.cargar``; el motor del Rol 1 lo evalúa sin
cambios.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app.api import motor_real, runtime
from app.api.app import app
from tests.c3_schema import validar

client = TestClient(app)

_DEMO = "BEN-DEMO-LOCAL-01"
_DEMO_REGIONAL = "BEN-DEMO-REGIONAL-01"
_RELEVANTES = {"SI", "INDETERMINADO"}
_SCHEMA_ALCANCE = (
    Path(__file__).resolve().parents[2]
    / "frontend" / "src" / "api" / "proposals" / "CatalogScopeEnvelopeV1.schema.json"
)


@pytest.fixture(scope="module")
def db_demo(db_path: Path, tmp_path_factory) -> Path:
    """Copia del loader + ejemplo SOLO DEMO + precálculo del Rol 1."""
    from app.db.build_views import construir
    from app.demo_territorial.cargar import cargar

    destino = tmp_path_factory.mktemp("e3db_demo") / "e3_demo.db"
    shutil.copyfile(db_path, destino)
    cargar(destino)
    construir(destino)
    return destino


@pytest.fixture(autouse=True)
def _cache_limpio():
    motor_real.limpiar_cache()
    yield
    motor_real.limpiar_cache()


def _modo_real(monkeypatch, db: Path) -> None:
    monkeypatch.setenv("E3_MOCK", "0")
    monkeypatch.setattr(runtime, "DB_PATH", db)


def _get(path: str) -> dict:
    r = client.get(f"/api/v1{path}")
    assert r.status_code == 200, r.status_code
    return r.json()


def test_ficha_mock_y_real_sin_no_ni_no_aplica(monkeypatch, db_motor_path: Path):
    mock = _get("/familias/FAM-SIM-0001")
    validar("FamiliaDetailEnvelope", mock)
    assert {b["result"] for b in mock["data"]["benefit_results"]} <= _RELEVANTES

    _modo_real(monkeypatch, db_motor_path)
    family_id = "FAM-SIM-E3-00001"
    real = _get(f"/familias/{family_id}")
    validar("FamiliaDetailEnvelope", real)
    resultados = real["data"]["benefit_results"]
    assert {b["result"] for b in resultados} <= _RELEVANTES
    with sqlite3.connect(db_motor_path) as conn:
        esperado = conn.execute(
            "SELECT COUNT(*) FROM evaluaciones WHERE id_familia = ? "
            "AND resultado IN ('SI', 'INDETERMINADO')", (family_id,)
        ).fetchone()[0]
    assert len(resultados) == esperado > 0


def test_ejemplo_aparece_donde_vive_la_familia(monkeypatch, db_demo: Path):
    _modo_real(monkeypatch, db_demo)
    com_001 = _get("/familias/FAM-SIM-E3-00001")
    validar("FamiliaDetailEnvelope", com_001)
    demo = [b for b in com_001["data"]["benefit_results"] if b["benefit_id"] == _DEMO]
    assert len(demo) == 1
    assert (demo[0]["result"], demo[0]["level"], demo[0]["access_state"]) == (
        "SI", "CONFIRMADO", "ELEGIBLE_SIN_ASIGNACION"
    )
    # El beneficio regional también aplica: COM-001 pertenece a REG-SIM-01.
    demo_reg = [b for b in com_001["data"]["benefit_results"]
                if b["benefit_id"] == _DEMO_REGIONAL]
    assert len(demo_reg) == 1
    assert (demo_reg[0]["result"], demo_reg[0]["level"], demo_reg[0]["access_state"]) == (
        "SI", "CONFIRMADO", "ELEGIBLE_SIN_ASIGNACION"
    )
    # Sin fuente oficial no hay Opportunity (DEC-050).
    assert _DEMO not in {o["benefit_id"] for o in com_001["data"]["top_opportunities"]}
    assert _DEMO_REGIONAL not in {o["benefit_id"] for o in com_001["data"]["top_opportunities"]}
    opps = client.get("/api/v1/familias/FAM-SIM-E3-00001/oportunidades",
                      params={"limit": 100}).json()["items"]
    assert _DEMO not in {o["benefit_id"] for o in opps}
    assert _DEMO_REGIONAL not in {o["benefit_id"] for o in opps}

    # COM-011 pertenece a REG-SIM-03: no aplica ni el comunal ni el regional.
    com_011 = _get("/familias/FAM-SIM-E3-00051")
    validar("FamiliaDetailEnvelope", com_011)
    presentes = {b["benefit_id"] for b in com_011["data"]["benefit_results"]}
    assert _DEMO not in presentes
    assert _DEMO_REGIONAL not in presentes


def test_textos_demo_sin_promesas_ni_url():
    from app.catalog import territorial
    from app.genai.template_provider import contiene_promesa, es_texto_plano

    textos = (
        territorial.DEMO_TITULO, territorial.DEMO_DONDE_IR,
        territorial.DEMO_DESCRIPCION, territorial.DEMO_INSTITUCION,
        territorial.DEMO_TITULO_REGIONAL, territorial.DEMO_DONDE_IR_REGIONAL,
        territorial.DEMO_DESCRIPCION_REGIONAL, territorial.DEMO_INSTITUCION_REGIONAL,
    )
    for texto in textos:
        assert es_texto_plano(texto) and not contiene_promesa(texto)
        assert "solo demo" in texto.lower()


def _validar_alcance(body: dict) -> None:
    schema = json.loads(_SCHEMA_ALCANCE.read_text(encoding="utf-8"))
    errores = list(Draft202012Validator(schema).iter_errors(body))
    assert not errores, [e.validator for e in errores]
    validar("EnvelopeMetadata", body["meta"])


def test_alcance_marca_local_y_nacional(monkeypatch, db_demo: Path):
    _modo_real(monkeypatch, db_demo)
    r = client.get("/api/v1/catalogo/alcance")
    assert r.status_code == 200
    body = r.json()
    _validar_alcance(body)
    por_id = {i["benefit_id"]: i for i in body["items"]}
    assert (por_id[_DEMO]["scope"], por_id[_DEMO]["demo"]) == ("LOCAL", True)
    assert (por_id[_DEMO_REGIONAL]["scope"], por_id[_DEMO_REGIONAL]["demo"]) == ("LOCAL", True)
    for bid in ("BEN-001", "BEN-018"):
        assert (por_id[bid]["scope"], por_id[bid]["demo"]) == ("NACIONAL", False)
    assert "COM-" not in r.text and "Comuna" not in r.text
    assert "REG-" not in r.text


def test_sin_ejemplo_no_cambia_nada(monkeypatch, db_motor_path: Path, db_demo: Path):
    _modo_real(monkeypatch, db_motor_path)
    body = _get("/catalogo/alcance")
    _validar_alcance(body)
    ids = {i["benefit_id"] for i in body["items"]}
    assert _DEMO not in ids and _DEMO_REGIONAL not in ids
    assert {i["scope"] for i in body["items"]} == {"NACIONAL"}

    sql = (
        "SELECT id_familia, id_beneficio, resultado, nivel, monto_estimado, "
        "datos_faltantes, traza_json FROM evaluaciones "
        "WHERE id_beneficio NOT IN (?, ?) ORDER BY id_familia, id_beneficio"
    )
    with sqlite3.connect(db_motor_path) as a, sqlite3.connect(db_demo) as b:
        originales = a.execute(sql, (_DEMO, _DEMO_REGIONAL)).fetchall()
        con_demo = b.execute(sql, (_DEMO, _DEMO_REGIONAL)).fetchall()
    assert len(originales) == 10_000
    assert originales == con_demo
