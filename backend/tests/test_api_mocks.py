"""Tests de los 12 flujos C3 como mocks (FEAT-003).

Cada ruta 2xx se valida contra el schema C3 correspondiente (cargado del YAML
del contrato, con los ``$ref`` a los esquemas externos resueltos). Se verifican
coherencia referencial, errores cerrados (shape ErrorResponse), disclaimer
exacto, snapshot/hashes constantes, idempotencia e invariantes oneOf.
"""
from __future__ import annotations

import json
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

from app.api.app import app  # noqa: E402
from app.api.deps import (  # noqa: E402
    CONTENT_BUNDLE_HASH,
    CONTENT_VERSION,
    DISCLAIMER,
    ELIGIBILITY_BUNDLE_HASH,
    SNAPSHOT_ID,
)

_REPO_DIR = BACKEND_DIR.parent
_CONTRACTS_DIR = _REPO_DIR / ".kiro" / "specs" / "_shared" / "contracts"
_C3_PATH = _CONTRACTS_DIR / "C3-api.openapi.yaml"


@pytest.fixture(scope="module")
def c3() -> dict:
    with _C3_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def _schema_validator(c3: dict, schema_name: str) -> Draft202012Validator:
    """Validador para un schema de ``components/schemas`` del contrato C3.

    Resuelve los ``$ref`` internos (``#/components/...``) contra el documento C3
    y los ``$ref`` a archivos externos (``./schemas/*.json``) contra el disco.
    """
    base_uri = _CONTRACTS_DIR.as_uri() + "/"

    def _handler(uri: str) -> dict:
        # file:// handler para los schemas externos referenciados por ruta relativa.
        path = Path(uri[len("file:///"):]) if uri.startswith("file:///") else Path(uri)
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    resolver = RefResolver(
        base_uri=base_uri,
        referrer=c3,
        handlers={"file": _handler},
    )
    schema = {"$ref": f"#/components/schemas/{schema_name}"}
    return Draft202012Validator(schema, resolver=resolver)


def _validar(c3: dict, schema_name: str, payload: dict) -> None:
    validator = _schema_validator(c3, schema_name)
    errores = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    assert not errores, f"{schema_name}: " + "; ".join(e.message for e in errores)


def _uuid() -> str:
    return str(uuid.uuid4())


# --- healthz + OpenAPI -------------------------------------------------------


def test_healthz(client: TestClient):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_openapi_contrato_servido(client: TestClient):
    r = client.get("/api/v1/openapi.yaml")
    assert r.status_code == 200
    doc = yaml.safe_load(r.text)
    assert doc["openapi"].startswith("3.1")
    assert "/jardines" in doc["paths"]
    r2 = client.get("/docs")
    assert r2.status_code == 200


# --- meta constante ----------------------------------------------------------


def _assert_meta(meta: dict):
    assert meta["snapshot_id"] == SNAPSHOT_ID
    assert meta["eligibility_bundle_hash"] == ELIGIBILITY_BUNDLE_HASH
    assert meta["content_bundle_hash"] == CONTENT_BUNDLE_HASH
    assert meta["content_version"] == CONTENT_VERSION
    assert meta["request_id"]


# --- 12 flujos: 2xx válidos contra C3 ---------------------------------------


def test_list_jardines(client: TestClient, c3: dict):
    r = client.get("/api/v1/jardines")
    assert r.status_code == 200
    body = r.json()
    _validar(c3, "JardinListEnvelope", body)
    _assert_meta(body["meta"])
    assert body["items"], "debe traer jardines sintéticos"


def test_list_familias_by_jardin(client: TestClient, c3: dict):
    r = client.get("/api/v1/jardines/JARDIN-001/familias")
    assert r.status_code == 200
    body = r.json()
    _validar(c3, "FamiliaListEnvelope", body)
    # Coherencia referencial: las familias listadas pertenecen a ese jardín.
    for fam in body["items"]:
        assert fam["family_id"].startswith("FAM-SIM-")


def test_list_familias_jardin_inexistente_404(client: TestClient, c3: dict):
    r = client.get("/api/v1/jardines/JARDIN-NOEXISTE/familias")
    assert r.status_code == 404
    _validar_error(c3, r.json())


def test_get_familia(client: TestClient, c3: dict):
    r = client.get("/api/v1/familias/FAM-SIM-0001")
    assert r.status_code == 200
    body = r.json()
    _validar(c3, "FamiliaDetailEnvelope", body)
    assert body["data"]["disclaimer"] == DISCLAIMER
    # Coherencia referencial: su garden_id existe en la lista de jardines.
    assert body["data"]["garden_id"] == "JARDIN-001"


def test_get_familia_404(client: TestClient, c3: dict):
    r = client.get("/api/v1/familias/FAM-NOEXISTE")
    assert r.status_code == 404
    _validar_error(c3, r.json())


def test_get_contexto(client: TestClient, c3: dict):
    r = client.get("/api/v1/familias/FAM-SIM-0001/contexto")
    assert r.status_code == 200
    _validar(c3, "FamiliaContextEnvelope", r.json())


def test_list_oportunidades(client: TestClient, c3: dict):
    r = client.get("/api/v1/familias/FAM-SIM-0001/oportunidades")
    assert r.status_code == 200
    body = r.json()
    _validar(c3, "OpportunityListEnvelope", body)
    posiciones = [o["position"] for o in body["items"]]
    assert posiciones == sorted(posiciones)


def test_oportunidades_orden_invalido_422(client: TestClient, c3: dict):
    r = client.get("/api/v1/familias/FAM-SIM-0001/oportunidades?orden=ZZZ")
    assert r.status_code == 422
    _validar_error(c3, r.json())


def test_create_guion(client: TestClient, c3: dict):
    r = client.post(
        "/api/v1/familias/FAM-SIM-0001/guion",
        json={"benefit_ids": ["BEN-001", "BEN-012"]},
    )
    assert r.status_code == 200
    body = r.json()
    _validar(c3, "ScriptGenerationEnvelope", body)
    assert body["provider"] == "PLANTILLA"
    assert body["disclaimer"] == DISCLAIMER
    assert DISCLAIMER in body["content"]["script"]


def test_create_mensaje(client: TestClient, c3: dict):
    r = client.post(
        "/api/v1/familias/FAM-SIM-0001/mensaje",
        json={"benefit_ids": ["BEN-001"]},
    )
    assert r.status_code == 200
    body = r.json()
    _validar(c3, "MessageGenerationEnvelope", body)
    card = body["content"]["printable_card"]
    assert card["format_version"] == "CARD_V1"
    # Sin markup activo en los strings de la tarjeta.
    blob = json.dumps(card)
    assert "<script" not in blob and "onerror=" not in blob


def test_create_conversacion_idempotente(client: TestClient, c3: dict):
    key = _uuid()
    cuerpo = {
        "benefit_ids": ["BEN-001"],
        "next_step": "GO_TO_INSTITUTION",
        "channel": "IN_PERSON",
        "occurred_at": "2026-10-13T12:00:00Z",
        "snapshot_id": SNAPSHOT_ID,
        "origin": "SIMULADO_DEMO",
    }
    r1 = client.post(
        "/api/v1/familias/FAM-SIM-0001/conversaciones",
        json=cuerpo, headers={"Idempotency-Key": key},
    )
    assert r1.status_code == 201
    body = r1.json()
    _validar(c3, "ConversationEnvelope", body)
    cid = body["data"]["conversation_id"]
    # Misma key + mismo body -> mismo registro.
    r2 = client.post(
        "/api/v1/familias/FAM-SIM-0001/conversaciones",
        json=cuerpo, headers={"Idempotency-Key": key},
    )
    assert r2.status_code == 201
    assert r2.json()["data"]["conversation_id"] == cid
    # Misma key + body distinto -> 409.
    cuerpo2 = dict(cuerpo, next_step="NONE")
    r3 = client.post(
        "/api/v1/familias/FAM-SIM-0001/conversaciones",
        json=cuerpo2, headers={"Idempotency-Key": key},
    )
    assert r3.status_code == 409
    _validar_error(c3, r3.json())


def test_create_preevaluacion_siempre_preliminar(client: TestClient, c3: dict):
    r = client.post(
        "/api/v1/familias/nueva/preevaluacion",
        json={
            "data_classification": "SYNTHETIC_DEMO_NOT_A_REAL_PERSON",
            "garden_id": "JARDIN-001",
            "commune_id": "COM-001",
            "demo_notice_accepted": True,
            "rsh_band": 40,
        },
        headers={"Idempotency-Key": _uuid()},
    )
    assert r.status_code == 200
    body = r.json()
    _validar(c3, "PreevaluationEnvelope", body)
    assert body["data"]["level"] == "PRELIMINAR"
    assert body["data"]["disclaimer"] == DISCLAIMER


def test_preevaluacion_sin_rotulado_422(client: TestClient, c3: dict):
    r = client.post(
        "/api/v1/familias/nueva/preevaluacion",
        json={
            "data_classification": "OTRO",
            "garden_id": "JARDIN-001",
            "commune_id": "COM-001",
            "demo_notice_accepted": True,
        },
        headers={"Idempotency-Key": _uuid()},
    )
    assert r.status_code == 422
    _validar_error(c3, r.json())


def test_get_kpi(client: TestClient, c3: dict):
    r = client.get("/api/v1/kpi?nivel=jardin&id=JARDIN-001")
    assert r.status_code == 200
    _validar(c3, "KpiEnvelope", r.json())


def test_kpi_nivel_invalido_422(client: TestClient, c3: dict):
    r = client.get("/api/v1/kpi?nivel=planeta")
    assert r.status_code == 422
    _validar_error(c3, r.json())


def test_asistente_catalog_info(client: TestClient, c3: dict):
    r = client.post("/api/v1/asistente", json={"question": "¿Qué beneficios existen?"})
    assert r.status_code == 200
    body = r.json()
    _validar(c3, "AssistantEnvelope", body)
    assert body["intent"] == "CATALOG_INFO"
    assert body["provider"] == "PLANTILLA"


def test_asistente_individual_sin_bedrock(client: TestClient, c3: dict):
    r = client.post("/api/v1/asistente", json={"question": "¿Yo califico para el subsidio?"})
    assert r.status_code == 200
    body = r.json()
    _validar(c3, "AssistantEnvelope", body)
    assert body["intent"] == "REQUIRES_DETERMINISTIC_EVALUATION"


def test_ingesta_afiche_pendiente_revision(client: TestClient, c3: dict):
    r = client.post(
        "/api/v1/catalogo/ingesta-afiche",
        json={
            "synthetic_asset_id": "ASSET-DEMO-0001",
            "media_type": "image/png",
            "sha256": "a" * 64,
        },
    )
    assert r.status_code == 200
    body = r.json()
    _validar(c3, "FlyerDraftEnvelope", body)
    assert body["data"]["status"] == "PENDIENTE_REVISION"


def test_ingesta_afiche_rechaza_campos_extra_422(client: TestClient, c3: dict):
    r = client.post(
        "/api/v1/catalogo/ingesta-afiche",
        json={
            "synthetic_asset_id": "ASSET-DEMO-0001",
            "media_type": "image/png",
            "sha256": "a" * 64,
            "bytes": "ZGF0YQ==",  # base64/bytes del cliente: PROHIBIDO
        },
    )
    assert r.status_code == 422
    _validar_error(c3, r.json())


# --- combinaciones adversariales de modelos ----------------------------------


def test_guion_benefit_ids_vacio_422(client: TestClient, c3: dict):
    r = client.post("/api/v1/familias/FAM-SIM-0001/guion", json={"benefit_ids": []})
    assert r.status_code == 422
    _validar_error(c3, r.json())


def test_guion_cuerpo_con_campo_extra_422(client: TestClient, c3: dict):
    r = client.post(
        "/api/v1/familias/FAM-SIM-0001/guion",
        json={"benefit_ids": ["BEN-001"], "context": {"nombre": "x"}},
    )
    assert r.status_code == 422
    _validar_error(c3, r.json())


def test_invariantes_oneof():
    """Las combinaciones incoherentes se rechazan por los validadores de modelos."""
    from app.api.models import InvarianteError, validar_opportunity

    # SI + level null -> rechazado
    with pytest.raises(InvarianteError):
        validar_opportunity("SI", None, "ELEGIBLE_SIN_ASIGNACION")
    # INDETERMINADO + acceso distinto -> rechazado
    with pytest.raises(InvarianteError):
        validar_opportunity("INDETERMINADO", None, "ASIGNADO")
    # NO en Opportunity -> rechazado (Opportunity solo SI/INDETERMINADO)
    with pytest.raises(InvarianteError):
        validar_opportunity("NO", None, "NO_APLICA")


def test_benefit_result_no_confirmado_asignado_rechazado():
    from app.api.models import InvarianteError, validar_benefit_result

    # NO + CONFIRMADO + ASIGNADO -> rechazado
    with pytest.raises(InvarianteError):
        validar_benefit_result("NO", "CONFIRMADO", "ASIGNADO")


# --- helper de validación de error -------------------------------------------


def _validar_error(c3: dict, payload: dict) -> None:
    schema_path = _CONTRACTS_DIR / "schemas" / "ErrorResponse.schema.json"
    with schema_path.open(encoding="utf-8") as fh:
        schema = json.load(fh)
    Draft202012Validator(schema).validate(payload)
    # Nunca ecoa PII: el mensaje es un texto fijo genérico.
    assert "nombre" not in json.dumps(payload).lower()
