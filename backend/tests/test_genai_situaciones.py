"""Chat de situaciones del asistente (Tarea 4 del plan de arreglos de la demo).

Una situación descrita por la tía ("está embarazada y sin trabajo") se responde
con apoyos de la tabla cerrada del catálogo C4, intención ``CATALOG_INFO``, sin
promesas de elegibilidad. Una pregunta con RUT se rechaza con 422 sin eco.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.app import app  # noqa: E402
from app.genai.template_provider import DISCLAIMER, contiene_promesa  # noqa: E402
from tests._genai_c3 import validar, validar_error  # noqa: E402

client = TestClient(app)
_PROHIBIDAS = ("podria calificar", "podría calificar", "le corresponde", "vale la pena consultar")


def test_situacion_embarazo_sin_trabajo_y_rut_sin_eco():
    r = client.post("/api/v1/asistente",
                    json={"question": "Está embarazada y sin trabajo, ¿qué apoyos hay?"})
    assert r.status_code == 200
    body = r.json()
    validar("AssistantEnvelope", body)
    assert body["intent"] == "CATALOG_INFO"
    assert "Subsidio Maternal" in body["answer"]          # BEN-003
    assert "Asignación Familiar" in body["answer"]        # BEN-016
    assert body["answer"].endswith(DISCLAIMER)
    assert body["citations"]
    assert not contiene_promesa(body["answer"].replace(DISCLAIMER, ""))
    assert not any(p in body["answer"].lower() for p in _PROHIBIDAS)

    r = client.post("/api/v1/asistente", json={"question": "mi rut es 12.345.678-5"})
    assert r.status_code == 422
    validar_error(r.json())
    assert "12.345.678" not in r.text


def test_chat_de_familia_embarazo_con_contexto_sin_codigos():
    # El prefijo de contexto (lo arma el chat de la ficha) no dispara la
    # derivación individual y la situación de la tía manda sobre los
    # beneficios nombrados en el contexto.
    pregunta = (
        "Contexto de la familia: 1 adulto de referencia de 29 años, 1 niño o niña "
        "de 2 años, tramo RSH 40, beneficios en la ficha: Subsidio Familiar (aplica), "
        "Bono por Hijo (falta dato). Situación que cuenta la tía: la mamá está "
        "embarazada otra vez"
    )
    r = client.post("/api/v1/asistente", json={"question": pregunta})
    assert r.status_code == 200
    body = r.json()
    validar("AssistantEnvelope", body)
    assert body["intent"] == "CATALOG_INFO"
    answer = body["answer"]
    assert "Subsidio Maternal" in answer                  # BEN-003
    assert not re.search(r"\bBEN-\d+|FAM-|JAR-", answer)
    assert answer.endswith(DISCLAIMER)
    assert not contiene_promesa(answer.replace(DISCLAIMER, ""))
    assert not any(p in answer.lower() for p in _PROHIBIDAS)
