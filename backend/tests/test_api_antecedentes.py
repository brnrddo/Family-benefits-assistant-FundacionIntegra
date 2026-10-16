"""Tests de la propuesta ``addFamiliaAntecedentes`` (DEC-039/PREG-039).

``POST /api/v1/familias/{id}/antecedentes`` NO está en C3 v1.0.2 (hay un test
que lo verifica), pero su respuesta 200 se valida contra el
``FamiliaDetailEnvelope`` del contrato, cargado del YAML sin editarlo.

Todo el material es sintético (``SYNTHETIC_DEMO_NOT_A_REAL_PERSON``): ningún
nombre, identificador civil, contacto ni texto libre.
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from jsonschema.validators import RefResolver

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import antecedentes_store as store  # noqa: E402
from app.api.antecedentes_service import hechos_declarados  # noqa: E402
from app.api.app import app  # noqa: E402
from app.api.deps import DISCLAIMER  # noqa: E402
from app.api.models import PreevaluationRequest  # noqa: E402
from app.api.models_antecedentes import (  # noqa: E402
    CAMPO_A_MISSING_CODE,
    CAMPOS_DECLARABLES,
    CAMPOS_MOTOR,
    AddFamilyInfoRequestV1,
)

_REPO_DIR = BACKEND_DIR.parent
_CONTRACTS_DIR = _REPO_DIR / ".kiro" / "specs" / "_shared" / "contracts"
_C3_PATH = _CONTRACTS_DIR / "C3-api.openapi.yaml"

_RUTA = "/api/v1/familias/FAM-SIM-0001/antecedentes"
_ROTULO = "SYNTHETIC_DEMO_NOT_A_REAL_PERSON"


@pytest.fixture(scope="module")
def c3() -> dict:
    with _C3_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _store_limpio():
    """El store es por proceso: se vacía antes y después de cada test."""
    store.reset()
    yield
    store.reset()


def _schema_validator(c3: dict, schema_name: str) -> Draft202012Validator:
    """Validador de un schema de ``components/schemas`` del contrato C3."""
    base_uri = _CONTRACTS_DIR.as_uri() + "/"

    def _handler(uri: str) -> dict:
        path = Path(uri[len("file:///"):]) if uri.startswith("file:///") else Path(uri)
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    resolver = RefResolver(base_uri=base_uri, referrer=c3, handlers={"file": _handler})
    return Draft202012Validator({"$ref": f"#/components/schemas/{schema_name}"}, resolver=resolver)


def _validar(c3: dict, schema_name: str, payload: dict) -> None:
    validator = _schema_validator(c3, schema_name)
    errores = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    assert not errores, f"{schema_name}: " + "; ".join(e.message for e in errores)


def _validar_error(c3: dict, payload: dict) -> None:
    schema_path = _CONTRACTS_DIR / "schemas" / "ErrorResponse.schema.json"
    with schema_path.open(encoding="utf-8") as fh:
        schema = json.load(fh)
    Draft202012Validator(schema).validate(payload)


def _uuid() -> str:
    return str(uuid.uuid4())


def _post(client: TestClient, cuerpo: dict, key: str | None = None, ruta: str = _RUTA):
    headers = {"Idempotency-Key": key or _uuid()}
    return client.post(ruta, json=cuerpo, headers=headers)


def _por_id(items: list[dict], benefit_id: str) -> dict:
    return next(i for i in items if i["benefit_id"] == benefit_id)


# --- éxito y forma de respuesta ---------------------------------------------


def test_200_y_envelope_valido(client: TestClient, c3: dict):
    r = _post(client, {"data_classification": _ROTULO, "has_rsh": True})
    assert r.status_code == 200  # NUNCA 201: no crea un recurso visible
    body = r.json()
    _validar(c3, "FamiliaDetailEnvelope", body)
    assert body["data"]["disclaimer"] == DISCLAIMER
    assert body["data"]["family_id"] == "FAM-SIM-0001"


def test_misma_forma_que_get_familia(client: TestClient):
    """Reutiliza el serializador de GET /familias/{id}: mismas claves."""
    get = client.get("/api/v1/familias/FAM-SIM-0001").json()["data"]
    post = _post(client, {"data_classification": _ROTULO, "has_rsh": True}).json()["data"]
    assert set(post) == set(get)


def test_paridad_de_campos_con_preevaluation_request():
    """18 campos idénticos a PreevaluationRequest + las 6 preguntas Sí/No del motor."""
    assert set(AddFamilyInfoRequestV1.model_fields) == (
        {"data_classification"} | CAMPOS_DECLARABLES | set(CAMPOS_MOTOR))
    assert len(CAMPOS_DECLARABLES) == 18
    for nombre in CAMPOS_DECLARABLES:
        propio = AddFamilyInfoRequestV1.model_fields[nombre]
        c3_field = PreevaluationRequest.model_fields[nombre]
        assert propio.annotation == c3_field.annotation, nombre
        assert propio.metadata == c3_field.metadata, nombre
    for nombre in CAMPOS_MOTOR:
        assert AddFamilyInfoRequestV1.model_fields[nombre].annotation == (bool | None), nombre
    # Nada de jardín, comuna, nombres, identificadores ni texto libre.
    for prohibido in ("garden_id", "commune_id", "nombre", "rut", "telefono"):
        assert prohibido not in AddFamilyInfoRequestV1.model_fields


# --- semántica ausente / null / UNKNOWN -------------------------------------


def test_clave_ausente_no_cambia_nada(client: TestClient):
    antes = client.get("/api/v1/familias/FAM-SIM-0001").json()["data"]
    r = _post(client, {"data_classification": _ROTULO, "has_rsh": True})
    despues = r.json()["data"]
    # has_rsh (rsh_status) no sustenta ningún resultado sintético de esta familia:
    # lo declarado no toca los demás campos y nada más se modifica.
    assert despues["composition"] == antes["composition"]
    assert despues["informed"] == antes["informed"]
    assert despues["rsh_band"] == antes["rsh_band"]
    for br in despues["benefit_results"]:
        previo = _por_id(antes["benefit_results"], br["benefit_id"])
        assert br == previo


def test_null_es_desconocido_y_no_se_degrada(client: TestClient, c3: dict):
    """``null`` = "No sé": DESCONOCIDO, el código sigue faltando, nunca false/0."""
    r = _post(client, {"data_classification": _ROTULO, "housing_type": None})
    assert r.status_code == 200
    data = r.json()["data"]
    _validar(c3, "FamiliaDetailEnvelope", r.json())
    ben = _por_id(data["benefit_results"], "BEN-018")
    assert "housing_type" in ben["missing_codes"]

    hechos = hechos_declarados(
        AddFamilyInfoRequestV1(data_classification=_ROTULO, housing_type=None)
    )
    assert len(hechos) == 1
    hecho = hechos[0]
    assert hecho["desconocido"] is True
    assert hecho["valor"] is None
    assert hecho["valor"] is not False and hecho["valor"] != 0
    assert hecho["estado_dato"] == "DECLARADO"
    assert hecho["acreditada"] is False

    # Y a nivel de familia queda como "no informado" en el contexto C3.
    ctx = client.get("/api/v1/familias/FAM-SIM-0001/contexto").json()
    _validar(c3, "FamiliaContextEnvelope", ctx)
    assert "housing_type" in ctx["data"]["missing_codes"]


def test_booleano_null_no_se_vuelve_false(client: TestClient, c3: dict):
    r = _post(client, {"data_classification": _ROTULO, "has_rsh": None})
    assert r.status_code == 200
    ctx = client.get("/api/v1/familias/FAM-SIM-0001/contexto").json()
    _validar(c3, "FamiliaContextEnvelope", ctx)
    assert "rsh_status" in ctx["data"]["missing_codes"]
    hechos = store.declarados_get("FAM-SIM-0001")
    assert hechos[0]["valor"] is None and hechos[0]["desconocido"] is True


def test_housing_type_unknown_equivale_a_no_se():
    hechos = hechos_declarados(
        AddFamilyInfoRequestV1(data_classification=_ROTULO, housing_type="UNKNOWN")
    )
    assert hechos[0]["desconocido"] is True
    assert hechos[0]["missing_code"] == "housing_type"


def test_no_se_no_borra_la_banda_del_motor(client: TestClient, c3: dict):
    """Declarar ignorancia NO destruye un dato de C1/C2: solo suma el código."""
    antes = client.get("/api/v1/familias/FAM-SIM-0001").json()["data"]
    ctx_antes = client.get("/api/v1/familias/FAM-SIM-0001/contexto").json()["data"]
    assert antes["rsh_band"] == 40

    r = _post(client, {"data_classification": _ROTULO, "rsh_band": None})
    assert r.status_code == 200
    _validar(c3, "FamiliaDetailEnvelope", r.json())
    assert r.json()["data"]["rsh_band"] == antes["rsh_band"]

    ctx = client.get("/api/v1/familias/FAM-SIM-0001/contexto").json()
    _validar(c3, "FamiliaContextEnvelope", ctx)
    # El contexto no se contradice consigo mismo: la banda y su score siguen.
    assert ctx["data"]["rsh_band"] == ctx_antes["rsh_band"]
    assert ctx["data"]["vulnerability_signals"] == ctx_antes["vulnerability_signals"]
    # El "No sé" se expresa como no informado, que es el campo de C3 para eso.
    assert "rsh_band" in ctx["data"]["missing_codes"]


def test_no_se_no_borra_la_banda_de_ingreso(client: TestClient, c3: dict):
    ctx_antes = client.get("/api/v1/familias/FAM-SIM-0001/contexto").json()["data"]
    assert ctx_antes["income_band"] == "UNDER_110K"

    r = _post(client, {"data_classification": _ROTULO, "household_income_band": None})
    assert r.status_code == 200
    ctx = client.get("/api/v1/familias/FAM-SIM-0001/contexto").json()
    _validar(c3, "FamiliaContextEnvelope", ctx)
    assert ctx["data"]["income_band"] == ctx_antes["income_band"]
    assert ctx["data"]["vulnerability_signals"] == ctx_antes["vulnerability_signals"]
    assert "income_band" in ctx["data"]["missing_codes"]


def test_no_se_llega_a_la_oportunidad_del_mismo_beneficio(client: TestClient, c3: dict):
    """La UI arma las preguntas desde la oportunidad: el código debe estar ahí."""
    r = _post(client, {"data_classification": _ROTULO, "rsh_band": None})
    assert r.status_code == 200
    data = r.json()["data"]
    _validar(c3, "FamiliaDetailEnvelope", r.json())

    ben = _por_id(data["benefit_results"], "BEN-001")
    opp = _por_id(data["top_opportunities"], "BEN-001")
    assert "rsh_band" in ben["missing_codes"]
    # Mismo beneficio, misma respuesta: no puede faltar y no faltar a la vez.
    assert "rsh_band" in opp["missing_codes"]
    assert opp["level"] == "PRELIMINAR"

    # Y la lista de oportunidades dice lo mismo que la ficha.
    items = client.get("/api/v1/familias/FAM-SIM-0001/oportunidades").json()["items"]
    assert "rsh_band" in _por_id(items, "BEN-001")["missing_codes"]


def test_declaracion_posterior_corrige_la_anterior(client: TestClient, c3: dict):
    """El último hecho declarado de un campo gana (la tía puede corregirse)."""
    r1 = _post(client, {"data_classification": _ROTULO, "rsh_band": None})
    assert r1.status_code == 200
    assert "rsh_band" in _por_id(r1.json()["data"]["benefit_results"], "BEN-001")["missing_codes"]

    r2 = _post(client, {"data_classification": _ROTULO, "rsh_band": 50})
    assert r2.status_code == 200
    data = r2.json()["data"]
    _validar(c3, "FamiliaDetailEnvelope", r2.json())
    assert "rsh_band" not in _por_id(data["benefit_results"], "BEN-001")["missing_codes"]
    assert "rsh_band" not in _por_id(data["top_opportunities"], "BEN-001")["missing_codes"]
    assert data["rsh_band"] == 50
    assert _por_id(data["benefit_results"], "BEN-001")["level"] == "PRELIMINAR"


def test_valor_conocido_resuelve_su_missing_code(client: TestClient, c3: dict):
    r = _post(
        client,
        {"data_classification": _ROTULO, "last_child_health_control_date": "2026-09-17"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    _validar(c3, "FamiliaDetailEnvelope", r.json())
    ben = _por_id(data["benefit_results"], "BEN-012")
    assert "last_health_control_date" not in ben["missing_codes"]
    ctx = client.get("/api/v1/familias/FAM-SIM-0001/contexto").json()["data"]
    assert "last_health_control_date" not in ctx["missing_codes"]


# --- nivel PRELIMINAR y elegibilidad intacta --------------------------------


def test_resultado_declarado_queda_preliminar(client: TestClient, c3: dict):
    antes = client.get("/api/v1/familias/FAM-SIM-0001").json()["data"]
    assert _por_id(antes["benefit_results"], "BEN-001")["level"] == "CONFIRMADO"

    r = _post(client, {"data_classification": _ROTULO, "rsh_band": 50})
    assert r.status_code == 200
    data = r.json()["data"]
    _validar(c3, "FamiliaDetailEnvelope", r.json())

    # BEN-001 se sustenta en rsh_band (su traza): deja de estar CONFIRMADO.
    ben = _por_id(data["benefit_results"], "BEN-001")
    assert ben["level"] == "PRELIMINAR"
    # Ningún result cambió: la elegibilidad es del motor determinista.
    for br in data["benefit_results"]:
        assert br["result"] == _por_id(antes["benefit_results"], br["benefit_id"])["result"]
    # Ninguna oportunidad tocada por el hecho declarado quedó CONFIRMADO.
    opp = _por_id(data["top_opportunities"], "BEN-001")
    assert opp["level"] == "PRELIMINAR"
    assert opp["score"] == _por_id(antes["top_opportunities"], "BEN-001")["score"]
    assert opp["position"] == _por_id(antes["top_opportunities"], "BEN-001")["position"]
    # El campo declarado se refleja tal cual (mismo campo y enum de C3).
    assert data["rsh_band"] == 50


def test_indeterminado_no_se_promueve(client: TestClient):
    r = _post(client, {"data_classification": _ROTULO, "housing_type": "ADEQUATE"})
    ben = _por_id(r.json()["data"]["benefit_results"], "BEN-018")
    assert ben["result"] == "INDETERMINADO"
    assert ben["level"] is None
    assert ben["access_state"] == "INDETERMINADO"


# --- cuerpos inválidos -------------------------------------------------------


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"data_classification": _ROTULO},                              # minProperties: 2
        {"has_rsh": True},                                             # sin rotulado
        {"data_classification": "OTRO", "has_rsh": True},              # const distinto
        {"data_classification": _ROTULO, "garden_id": "JARDIN-001"},   # propiedad extra
        {"data_classification": _ROTULO, "nombre": "x"},               # propiedad extra
        {"data_classification": _ROTULO, "commune_id": "COM-001"},     # propiedad extra
        {"data_classification": _ROTULO, "rsh_band": 45},              # fuera del enum
        {"data_classification": _ROTULO, "housing_type": "CASA"},      # fuera del enum
        {"data_classification": _ROTULO, "child_age": 121},            # fuera de rango
        {"data_classification": _ROTULO,
         "last_child_health_control_date": "xxxxxxxxxx"},              # no es fecha
        {"data_classification": _ROTULO,
         "last_child_health_control_date": "2026-13-01"},              # fecha inexistente
    ],
)
def test_cuerpo_invalido_422(client: TestClient, c3: dict, cuerpo: dict):
    r = _post(client, cuerpo)
    assert r.status_code == 422
    _validar_error(c3, r.json())


def test_sin_header_idempotency_key_error(client: TestClient, c3: dict):
    r = client.post(_RUTA, json={"data_classification": _ROTULO, "has_rsh": True})
    assert r.status_code == 422
    _validar_error(c3, r.json())


def test_idempotency_key_no_uuid_422(client: TestClient, c3: dict):
    r = _post(client, {"data_classification": _ROTULO, "has_rsh": True}, key="no-es-uuid")
    assert r.status_code == 422
    _validar_error(c3, r.json())


def test_familia_inexistente_404(client: TestClient, c3: dict):
    r = _post(
        client,
        {"data_classification": _ROTULO, "has_rsh": True},
        ruta="/api/v1/familias/FAM-NOEXISTE/antecedentes",
    )
    assert r.status_code == 404
    _validar_error(c3, r.json())


# --- idempotencia ------------------------------------------------------------


def test_idempotencia_misma_clave_mismo_cuerpo(client: TestClient):
    key = _uuid()
    cuerpo = {"data_classification": _ROTULO, "last_child_health_control_date": "2026-09-17"}
    r1 = _post(client, cuerpo, key=key)
    assert r1.status_code == 200
    r2 = _post(client, cuerpo, key=key)
    assert r2.status_code == 200
    assert r2.json()["data"] == r1.json()["data"]
    # Sin efectos nuevos: un solo hecho registrado.
    assert len(store.declarados_get("FAM-SIM-0001")) == 1


def test_idempotencia_cuerpo_distinto_409(client: TestClient, c3: dict):
    key = _uuid()
    r1 = _post(client, {"data_classification": _ROTULO, "has_rsh": True}, key=key)
    assert r1.status_code == 200
    r2 = _post(client, {"data_classification": _ROTULO, "has_rsh": False}, key=key)
    assert r2.status_code == 409
    _validar_error(c3, r2.json())


def test_null_y_ausente_no_colisionan_en_la_clave(client: TestClient):
    """``{"has_rsh": null}`` y un cuerpo sin ``has_rsh`` son cuerpos distintos."""
    key = _uuid()
    r1 = _post(client, {"data_classification": _ROTULO, "has_rsh": None}, key=key)
    assert r1.status_code == 200
    r2 = _post(client, {"data_classification": _ROTULO, "child_age": 4}, key=key)
    assert r2.status_code == 409


def test_misma_clave_otra_familia_409(client: TestClient, c3: dict):
    """La clave está acotada al recurso: nunca devuelve la ficha de otra familia."""
    key = _uuid()
    cuerpo = {"data_classification": _ROTULO, "has_rsh": True}
    r1 = _post(client, cuerpo, key=key)
    assert r1.status_code == 200
    assert r1.json()["data"]["family_id"] == "FAM-SIM-0001"

    r2 = _post(
        client, cuerpo, key=key, ruta="/api/v1/familias/FAM-SIM-0002/antecedentes"
    )
    assert r2.status_code == 409
    _validar_error(c3, r2.json())
    # Y no se sirvió la ficha equivocada ni se perdieron hechos en silencio.
    assert store.declarados_get("FAM-SIM-0002") == []

    # Con su propia clave, la segunda familia se procesa normalmente.
    r3 = _post(
        client, cuerpo, key=_uuid(), ruta="/api/v1/familias/FAM-SIM-0002/antecedentes"
    )
    assert r3.status_code == 200
    assert r3.json()["data"]["family_id"] == "FAM-SIM-0002"
    assert len(store.declarados_get("FAM-SIM-0002")) == 1


# --- scopes y motor ----------------------------------------------------------


@pytest.mark.parametrize(
    "scopes,esperado",
    [("familias:write", 200), ("familias:read", 404), ("", 401)],
)
def test_scopes(client: TestClient, scopes: str, esperado: int):
    r = client.post(
        _RUTA,
        json={"data_classification": _ROTULO, "has_rsh": True},
        headers={"Idempotency-Key": _uuid(), "X-Demo-Scopes": scopes},
    )
    assert r.status_code == esperado


def test_motor_no_disponible_503(client: TestClient, c3: dict, monkeypatch):
    monkeypatch.setenv("E3_MOCK", "0")
    r = _post(client, {"data_classification": _ROTULO, "has_rsh": True})
    assert r.status_code == 503
    body = r.json()
    _validar_error(c3, body)
    assert body["error"]["retryable"] is True
    assert store.declarados_get("FAM-SIM-0001") == []


# --- privacidad en logs ------------------------------------------------------


def test_logs_sin_cuerpo_ni_valores(client: TestClient, caplog):
    fecha = "2026-09-17"
    with caplog.at_level(logging.DEBUG):
        r = _post(
            client,
            {"data_classification": _ROTULO, "last_child_health_control_date": fecha},
        )
    assert r.status_code == 200
    texto = caplog.text
    assert "route=/familias/{id}/antecedentes" in texto
    assert "status=200" in texto
    # Nunca el cuerpo, el valor declarado, el rotulado ni el nombre del campo.
    for prohibido in (fecha, _ROTULO, "last_child_health_control_date", "data_classification"):
        assert prohibido not in texto


# --- el contrato C3 queda intacto -------------------------------------------


def test_c3_sigue_en_1_0_2_sin_la_ruta(c3: dict):
    assert c3["info"]["version"] == "1.0.2"
    assert "/familias/{id}/antecedentes" not in c3["paths"]


def test_codigos_son_el_enum_de_c3(c3: dict):
    """Los ``missing_code`` usados son el enum cerrado de FamilyContextView."""
    enum = set(
        c3["components"]["schemas"]["FamilyContextView"]["properties"]["missing_codes"]["items"][
            "enum"
        ]
    )
    assert set(CAMPO_A_MISSING_CODE.values()) <= enum
