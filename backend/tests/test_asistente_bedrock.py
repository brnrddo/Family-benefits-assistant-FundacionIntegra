"""Camino Bedrock de ``POST /asistente`` en modo demo y su fallback sin callejón.

Por HTTP (``TestClient``) y sin AWS: el cliente ``bedrock-runtime`` se inyecta
con un doble, el reloj del provider se sustituye, ``boto3`` no se importa y el
Guardrail es un valor SINTÉTICO. Todos los datos son ficticios.
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import runtime  # noqa: E402
from app.api.app import app  # noqa: E402
from app.genai import asistente_bedrock, redaccion  # noqa: E402
from app.genai import provider as prov  # noqa: E402
from app.genai.content_catalog import cargar_catalogo_contenido  # noqa: E402
from app.genai.provider import BedrockProvider  # noqa: E402
from app.genai.template_provider import (  # noqa: E402
    DISCLAIMER,
    _normalizar,
    asistente_sin_catalogo,
)
from tests._bedrock_dobles import (  # noqa: E402
    ClienteFalso,
    _RelojFalso,
    respuesta_tooluse,
)
from tests._genai_c3 import validar  # noqa: E402

# No activa SITUACIONES, títulos del catálogo ni ``es_pregunta_individual``.
PREGUNTA_SIN_MATCH = "¿Cómo apoyo a una familia que llegó hace poco al barrio?"
PREGUNTA_AGUA = "Les cortaron el agua"

# Prosa admisible del modelo: nombra un apoyo del catálogo (por error con su
# código interno, que el servidor cambia por el título) y uno ficticio.
TEXTO_MODELO = (
    "Hoy puede conversar con la familia y pedirle la ultima boleta de agua. "
    "Presentele el BEN-005 y tambien el Fondo Vecinal Agua Segura, un programa "
    "de esta demo. Luego acerquese a la oficina municipal."
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    """Throttle neutralizado y entorno Bedrock con valores sintéticos."""
    monkeypatch.setattr(prov, "time", _RelojFalso())
    monkeypatch.setattr(BedrockProvider, "_ultima_llamada", 0.0)
    monkeypatch.setenv("E3_GUARDRAIL_ID", "GUARDRAIL-SINTETICO-TEST")
    monkeypatch.setenv("E3_GUARDRAIL_VERSION", "1")
    monkeypatch.setenv("E3_BEDROCK_MODEL_ID", "modelo-sintetico-test")
    monkeypatch.delenv("E3_LLM_PROVIDER", raising=False)
    monkeypatch.setattr(runtime, "_provider", None)
    redaccion.reiniciar_proveedor()
    yield
    redaccion.reiniciar_proveedor()


def _inyectar(monkeypatch, cliente: ClienteFalso) -> ClienteFalso:
    monkeypatch.setenv("E3_LLM_PROVIDER", "bedrock")
    proveedor = BedrockProvider(cliente=cliente)
    monkeypatch.setattr(redaccion, "obtener_proveedor", lambda: proveedor)
    return cliente


def _preguntar(question: str) -> dict:
    r = client.post("/api/v1/asistente", json={"question": question})
    assert r.status_code == 200
    body = r.json()
    validar("AssistantEnvelope", body)
    return body


def _sin_callejon(answer: str) -> bool:
    texto = _normalizar(answer)
    return not any(f in texto for f in (
        "no encontr", "no hay nada", "no es posible responder", "nada que hacer",
    ))


def test_bedrock_ok_responde_catalog_info_con_aviso_y_solo_citas_permitidas(
    monkeypatch, caplog
):
    cliente = _inyectar(monkeypatch, ClienteFalso(respuesta_converse=respuesta_tooluse(
        {"answer": TEXTO_MODELO, "benefit_ids": ["BEN-005", "BEN-999"]}
    )))
    with caplog.at_level(logging.DEBUG):
        body = _preguntar(PREGUNTA_AGUA)

    assert body["provider"] == "BEDROCK"
    assert body["intent"] == "CATALOG_INFO"
    ben005 = cargar_catalogo_contenido().entradas["BEN-005"]
    # El código interno nunca queda en la prosa: se reemplaza por el título.
    esperado = TEXTO_MODELO.replace("BEN-005", ben005.title)
    assert body["answer"] == f"{esperado} {DISCLAIMER}"
    assert not re.search(r"\bBEN-\d+\b|\b(?:FAM|JAR)-[A-Z0-9-]+\b", body["answer"])
    assert body["warnings"] == []
    # Solo la cita del ID enviado; el ID desconocido se descarta.
    assert body["citations"] == [{"source_id": ben005.source_id, "url": ben005.source_url}]

    assert cliente.operaciones == ["apply_guardrail", "converse", "apply_guardrail"]
    converse = cliente.llamadas[1][1]
    tool = converse["toolConfig"]["tools"][0]["toolSpec"]
    assert tool["inputSchema"]["json"] == asistente_bedrock.SCHEMA_ASISTENTE
    prompt = converse["messages"][0]["content"][0]["text"]
    assert "BEN-005" in prompt
    assert not any(b in prompt for b in ("BEN-018", "BEN-019", "BEN-020"))
    # Logs sanitizados: ni la pregunta ni la respuesta.
    assert PREGUNTA_AGUA not in caplog.text
    assert TEXTO_MODELO not in caplog.text


def test_guardrail_input_evalua_solo_la_pregunta_no_el_prompt(monkeypatch):
    """INPUT recibe la pregunta exacta; el prompt completo solo va a Converse.

    Medido en la cuenta: las instrucciones del servidor evaluadas como entrada
    disparaban PROMPT_ATTACK/MISCONDUCT y el chat siempre degradaba.
    """
    cliente = _inyectar(monkeypatch, ClienteFalso(respuesta_converse=respuesta_tooluse(
        {"answer": TEXTO_MODELO, "benefit_ids": ["BEN-005"]}
    )))
    body = _preguntar(PREGUNTA_AGUA)

    assert body["provider"] == "BEDROCK"
    entradas = [kw for op, kw in cliente.llamadas
                if op == "apply_guardrail" and kw["source"] == "INPUT"]
    assert len(entradas) == 1
    assert entradas[0]["content"] == [{"text": {"text": PREGUNTA_AGUA}}]
    prompt = cliente.llamadas[1][1]["messages"][0]["content"][0]["text"]
    assert prompt != PREGUNTA_AGUA and PREGUNTA_AGUA in prompt


@pytest.mark.parametrize(("cliente", "motivo"), [
    (lambda: ClienteFalso(error_converse=RuntimeError("simulado")),
     redaccion.MOTIVO_BEDROCK_ERROR),
    (lambda: ClienteFalso(acciones_guardrail=["GUARDRAIL_INTERVENED"]),
     redaccion.MOTIVO_GUARDRAIL_INTERVINO),
], ids=["bedrock_error", "guardrail"])
def test_fallo_de_bedrock_degrada_a_plantilla_sin_callejon(
    monkeypatch, caplog, cliente, motivo
):
    _inyectar(monkeypatch, cliente())
    with caplog.at_level(logging.DEBUG):
        body = _preguntar(PREGUNTA_SIN_MATCH)

    assert body["provider"] == "PLANTILLA"
    assert body["intent"] == "CATALOG_INFO"
    assert body["answer"].endswith(DISCLAIMER)
    assert _sin_callejon(body["answer"])
    assert body["warnings"] == []  # degradación silenciosa
    assert f"genai_degradado_a_plantilla: motivo={motivo}" in caplog.text
    assert PREGUNTA_SIN_MATCH not in caplog.text


def test_pregunta_sin_coincidencias_en_plantilla_devuelve_acciones():
    body = _preguntar(PREGUNTA_SIN_MATCH)

    assert body["provider"] == "PLANTILLA"
    assert body["intent"] == "CATALOG_INFO"
    assert _sin_callejon(body["answer"])
    texto = _normalizar(body["answer"])
    for accion in ("ficha", "documentos", "oficina municipal"):
        assert accion in texto
    assert 1 <= len(body["citations"]) <= 8

    sin_catalogo = asistente_sin_catalogo("REQ-TEST", PREGUNTA_SIN_MATCH)["answer"]
    assert _sin_callejon(sin_catalogo)
    assert "ficha" in _normalizar(sin_catalogo)
