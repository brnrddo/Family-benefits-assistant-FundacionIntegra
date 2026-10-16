"""Chat de situaciones del asistente (Tarea 4 del plan de arreglos de la demo).

Una situación descrita por la tía ("está embarazada y sin trabajo") se responde
con apoyos de la tabla cerrada del catálogo C4, intención ``CATALOG_INFO``, sin
promesas de elegibilidad. Una pregunta con RUT se rechaza con 422 sin eco.
"""
from __future__ import annotations

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
