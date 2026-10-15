"""Guion, mensaje y asistente desde el catálogo C4 de ``content/`` (DEC-054..059).

Por HTTP (``TestClient``, ``E3_MOCK`` por defecto). Los valores esperados se
leen de ``content/`` en el test, no del loader:

- Guion y mensaje hablan de EXACTAMENTE los ``benefit_ids`` pedidos, con su
  nombre y descripción, y con el texto marco literal del Rol 4.
- ID desconocido → 422 ``ErrorResponse`` sin ecoar valores; nunca se sustituye.
- BEN-018/019/020 sin URL (PREG-045): sin sección en la tarjeta ni cita.
- Asistente por nombre de beneficio; la consulta individual no cambia.
- Catálogo inválido → fallback seguro sin 500 y sin cachear el fallo.
- Respuestas validadas contra el schema C3 de cada ruta; logs sin textos.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import sys
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import runtime  # noqa: E402
from app.api.app import app  # noqa: E402
from app.genai import content_catalog  # noqa: E402
from app.genai.template_provider import (  # noqa: E402
    DISCLAIMER,
    PH_INSTITUCION,
    PH_TITULOS,
)
from tests._genai_c3 import validar, validar_error  # noqa: E402

REPO_DIR = BACKEND_DIR.parent
CONTENT_DIR = REPO_DIR / "content"
FAM = "/api/v1/familias/FAM-SIM-0001"
IDS = [f"BEN-{n:03d}" for n in range(1, 21)]
SIN_CITA = ("BEN-018", "BEN-019", "BEN-020")
CITABLES = [b for b in IDS if b not in SIN_CITA]

client = TestClient(app)


# --- valores esperados leídos directo de content/ --------------------------------

with (CONTENT_DIR / "beneficios.yaml").open(encoding="utf-8") as _fh:
    BEN = {b["benefit_id"]: b for b in yaml.safe_load(_fh)["beneficios"]}
TITULOS = {bid: b["simple_title"] for bid, b in BEN.items()}


def _respaldo(archivo: str, clave: str, intent: str | None = None) -> str:
    """Valor literal de ``> clave: valor`` en la plantilla de respaldo del Rol 4."""
    texto = (CONTENT_DIR / "prompts" / archivo).read_text(encoding="utf-8")
    seccion = texto.split("## Plantilla de respaldo", 1)[1]
    for bloque in re.split(r"\n\s*\n", seccion):
        lineas = dict(
            linea[2:].split(": ", 1) for linea in bloque.splitlines() if linea.startswith("> ")
        )
        if clave in lineas and (intent is None or lineas.get("intent") == intent):
            return lineas[clave]
    raise AssertionError(f"{archivo}: sin {clave}")


def _sin_aviso(texto: str) -> str:
    assert texto.endswith(f" {DISCLAIMER}")
    return texto[: -len(DISCLAIMER) - 1]


GUION = _sin_aviso(_respaldo("guion.md", "script"))
WHATSAPP = _sin_aviso(_respaldo("mensaje_familia.md", "whatsapp_preview"))
CARD_TITLE = _respaldo("mensaje_familia.md", "printable_card.title")
CARD_INTRO = _respaldo("mensaje_familia.md", "printable_card.introduction")
REASON = _respaldo("mensaje_familia.md", "printable_card.sections[].reason")
ACTION = _respaldo("mensaje_familia.md", "printable_card.sections[].action")
INDIVIDUAL = _respaldo("asistente_catalogo.md", "answer", "REQUIRES_DETERMINISTIC_EVALUATION")
CATALOGO = _sin_aviso(_respaldo("asistente_catalogo.md", "answer", "CATALOG_INFO"))


def _otros_titulos(bids: list[str]) -> list[str]:
    """Títulos que NO deben aparecer: ni pedidos ni contenidos en lo pedido."""
    pedidos = " ".join(TITULOS[b] + " " + BEN[b]["description"] for b in bids)
    return [t for b, t in TITULOS.items() if b not in bids and t not in pedidos]


@pytest.fixture(autouse=True)
def _provider_limpio(monkeypatch):
    monkeypatch.setattr(runtime, "_provider", None)


def _post(ruta: str, ids: list[str]):
    return client.post(f"{FAM}/{ruta}", json={"benefit_ids": ids})


# --- guion -----------------------------------------------------------------------


@pytest.mark.parametrize("bid", IDS)
def test_guion_por_beneficio(bid):
    r = _post("guion", [bid])
    assert r.status_code == 200
    body = r.json()
    validar("ScriptGenerationEnvelope", body)
    script = body["content"]["script"]
    assert body["content"]["benefit_ids"] == [bid]
    assert body["warnings"] == []
    assert body["provider"] == "PLANTILLA"
    assert body["disclaimer"] == DISCLAIMER
    assert script.startswith(GUION.replace(PH_TITULOS, TITULOS[bid]))
    assert f"{TITULOS[bid]}: {BEN[bid]['description']}" in script
    assert script.endswith(DISCLAIMER)
    for otro in _otros_titulos([bid]):
        assert otro not in script


def test_guion_respeta_orden_pedido():
    ids = ["BEN-005", "BEN-001", "BEN-013"]
    body = _post("guion", ids).json()
    validar("ScriptGenerationEnvelope", body)
    assert body["content"]["benefit_ids"] == ids
    script = body["content"]["script"]
    titulos = ", ".join(TITULOS[b] for b in ids)
    assert script.startswith(GUION.replace(PH_TITULOS, titulos))
    posiciones = [script.index(f"{TITULOS[b]}: ") for b in ids]
    assert posiciones == sorted(posiciones)
    for otro in _otros_titulos(ids):
        assert otro not in script


# --- mensaje ---------------------------------------------------------------------


@pytest.mark.parametrize("bid", CITABLES)
def test_mensaje_por_beneficio(bid):
    r = _post("mensaje", [bid])
    assert r.status_code == 200
    body = r.json()
    validar("MessageGenerationEnvelope", body)
    content = body["content"]
    card = content["printable_card"]
    b = BEN[bid]
    assert content["benefit_ids"] == [bid]
    assert body["warnings"] == []
    assert content["whatsapp_preview"] == f"{WHATSAPP.replace(PH_TITULOS, TITULOS[bid])} {DISCLAIMER}"
    assert (card["format_version"], card["title"], card["introduction"]) == (
        "CARD_V1", CARD_TITLE, CARD_INTRO)
    assert len(card["sections"]) == 1
    sec = card["sections"][0]
    assert sec["benefit_id"] == bid
    assert sec["heading"] == TITULOS[bid]
    assert sec["reason"] == f"{REASON} {b['description']}"
    assert sec["action"] == ACTION.replace(PH_INSTITUCION, b["institution"])
    assert sec["where_to_go"] == b["where_to_go"]
    assert sec["sources"] == [{"source_id": b["official_source_id"], "url": b["official_url"]}]
    blob = json.dumps(content, ensure_ascii=False)
    for otro in _otros_titulos([bid]):
        assert otro not in blob


def test_mensaje_omite_seccion_sin_fuente():
    body = _post("mensaje", ["BEN-001", "BEN-018"]).json()
    validar("MessageGenerationEnvelope", body)
    content = body["content"]
    assert content["benefit_ids"] == ["BEN-001", "BEN-018"]
    assert [s["benefit_id"] for s in content["printable_card"]["sections"]] == ["BEN-001"]
    assert body["warnings"] == ["SECCION_SIN_FUENTE_OMITIDA"]
    titulos = f"{TITULOS['BEN-001']}, {TITULOS['BEN-018']}"
    assert content["whatsapp_preview"].startswith(WHATSAPP.replace(PH_TITULOS, titulos))


@pytest.mark.parametrize("ids", [["BEN-019"], ["BEN-018", "BEN-020"]])
def test_mensaje_sin_ninguna_fuente_422(ids):
    r = _post("mensaje", ids)
    assert r.status_code == 422
    payload = r.json()
    validar_error(payload)
    campos = [d["field"] for d in payload["error"]["details"]]
    assert campos == [f"body.benefit_ids.{i}" for i in range(len(ids))]
    assert "BEN-0" not in r.text


def test_guion_id_desconocido_422_sin_eco():
    r = _post("guion", ["BEN-999"])
    assert r.status_code == 422
    validar_error(r.json())
    assert r.json()["error"]["details"][0]["field"] == "body.benefit_ids.0"
    assert "BEN-999" not in r.text


def test_mensaje_id_desconocido_422_sin_sustituir():
    r = _post("mensaje", ["BEN-001", "BEN-999"])
    assert r.status_code == 422
    payload = r.json()
    validar_error(payload)
    assert [d["field"] for d in payload["error"]["details"]] == ["body.benefit_ids.1"]
    assert "BEN-999" not in r.text
    assert TITULOS["BEN-001"] not in r.text


# --- asistente -------------------------------------------------------------------


def _preguntar(question: str) -> dict:
    r = client.post("/api/v1/asistente", json={"question": question})
    assert r.status_code == 200
    body = r.json()
    validar("AssistantEnvelope", body)
    assert body["provider"] == "PLANTILLA"
    assert body["disclaimer"] == DISCLAIMER
    assert body["answer"].endswith(DISCLAIMER)
    return body


def _cita(bid: str) -> dict:
    return {"source_id": BEN[bid]["official_source_id"], "url": BEN[bid]["official_url"]}


def test_asistente_por_nombre():
    body = _preguntar("¿Qué es el Subsidio Familiar?")
    assert body["intent"] == "CATALOG_INFO"
    assert BEN["BEN-001"]["description"] in body["answer"]
    assert BEN["BEN-002"]["description"] not in body["answer"]
    assert body["citations"] == [_cita("BEN-001")]
    assert body["warnings"] == []


def test_asistente_gana_el_nombre_mas_especifico():
    body = _preguntar("¿Qué es el Subsidio Familiar automático?")
    assert BEN["BEN-002"]["description"] in body["answer"]
    assert BEN["BEN-001"]["description"] not in body["answer"]
    assert body["citations"] == [_cita("BEN-002")]


def test_asistente_beneficio_sin_url_sin_cita():
    body = _preguntar("¿Qué es la canasta familiar?")
    assert body["intent"] == "CATALOG_INFO"
    assert BEN["BEN-018"]["description"] in body["answer"]
    assert body["citations"] == []


def test_asistente_pregunta_general():
    body = _preguntar("¿Qué beneficios existen?")
    assert body["intent"] == "CATALOG_INFO"
    titulos = ", ".join(TITULOS[b] for b in CITABLES[:8])
    assert body["answer"] == f"{CATALOGO.replace(PH_TITULOS, titulos)} {DISCLAIMER}"
    urls = {b["official_url"] for b in BEN.values() if b["official_url"]}
    assert 1 <= len(body["citations"]) <= 8
    assert all(c["url"] in urls for c in body["citations"])
    assert len({c["url"] for c in body["citations"]}) == len(body["citations"])


def test_asistente_individual_sin_cambios():
    body = _preguntar("¿Yo califico para el subsidio?")
    assert body["intent"] == "REQUIRES_DETERMINISTIC_EVALUATION"
    assert body["answer"] == INDIVIDUAL
    assert body["citations"] == []
    assert body["warnings"] == []


# --- falla cerrada del catálogo (DEC-058) ----------------------------------------


def test_catalogo_invalido_fallback_sin_500(tmp_path, monkeypatch, caplog):
    shutil.copytree(CONTENT_DIR, tmp_path / "content")
    beneficios = tmp_path / "content" / "beneficios.yaml"
    beneficios.write_bytes(beneficios.read_bytes() + b"#")
    original = content_catalog.DEFAULT_MANIFEST
    monkeypatch.setattr(content_catalog, "DEFAULT_MANIFEST", tmp_path / "content" / "manifest.yaml")
    pregunta = "¿Qué es el Subsidio Familiar?"

    with caplog.at_level(logging.DEBUG):
        r = _post("guion", ["BEN-001", "BEN-005"])
        assert r.status_code == 200
        body = r.json()
        validar("ScriptGenerationEnvelope", body)
        assert body["warnings"] == ["CATALOGO_C4_NO_DISPONIBLE"]
        assert body["content"]["benefit_ids"] == ["BEN-001", "BEN-005"]
        assert body["content"]["script"].endswith(DISCLAIMER)
        for titulo in TITULOS.values():
            assert titulo not in body["content"]["script"]

        r = _post("mensaje", ["BEN-001"])
        assert r.status_code == 503
        validar_error(r.json())
        assert r.json()["error"]["retryable"] is True

        general = _preguntar(pregunta)
        assert general["intent"] == "CATALOG_INFO"
        assert general["citations"] == []
        assert general["warnings"] == ["CATALOGO_C4_NO_DISPONIBLE"]
        assert all(t not in general["answer"] for t in TITULOS.values())

        individual = _preguntar("¿Yo califico para el subsidio?")
        assert individual["intent"] == "REQUIRES_DETERMINISTIC_EVALUATION"
        assert individual["citations"] == []

    assert "C4_SHA256_DISTINTO" in caplog.text
    assert str(tmp_path) not in caplog.text
    assert pregunta not in caplog.text

    # El fallo no se cachea: con el manifest original vuelve a generar normal.
    monkeypatch.setattr(content_catalog, "DEFAULT_MANIFEST", original)
    body = _post("guion", ["BEN-001"]).json()
    assert body["warnings"] == []
    assert TITULOS["BEN-001"] in body["content"]["script"]


# --- flujo mock del frontend (E3_MOCK=1) -----------------------------------------


def _top_ids(family_id: str) -> list[str]:
    r = client.get(f"/api/v1/familias/{family_id}")
    assert r.status_code == 200
    return [o["benefit_id"] for o in r.json()["data"]["top_opportunities"]]


def test_flujo_mock_familia_con_programa_demo():
    ids = _top_ids("FAM-SIM-0001")
    assert ids == ["BEN-001", "BEN-012", "BEN-018"]
    guion = _post("guion", ids)
    assert guion.status_code == 200
    validar("ScriptGenerationEnvelope", guion.json())
    assert guion.json()["warnings"] == []
    mensaje = _post("mensaje", ids)
    assert mensaje.status_code == 200
    body = mensaje.json()
    validar("MessageGenerationEnvelope", body)
    assert len(body["content"]["printable_card"]["sections"]) == 2
    assert body["warnings"] == ["SECCION_SIN_FUENTE_OMITIDA"]


def test_flujo_mock_familia_simple():
    ids = _top_ids("FAM-SIM-0002")
    for ruta in ("guion", "mensaje"):
        r = client.post(f"/api/v1/familias/FAM-SIM-0002/{ruta}", json={"benefit_ids": ids})
        assert r.status_code == 200
        assert r.json()["warnings"] == []


# --- logs sin textos ---------------------------------------------------------------


def test_logs_sin_textos_ni_ids(caplog):
    pregunta = "¿Qué es el Bono por Hijo?"
    with caplog.at_level(logging.DEBUG):
        _post("guion", ["BEN-001", "BEN-005"])
        _post("mensaje", ["BEN-001", "BEN-018"])
        _post("mensaje", ["BEN-999"])
        _preguntar(pregunta)
    texto = caplog.text
    assert pregunta not in texto
    assert "BEN-0" not in texto and "BEN-999" not in texto
    for b in BEN.values():
        assert b["simple_title"] not in texto
        assert b["description"] not in texto
