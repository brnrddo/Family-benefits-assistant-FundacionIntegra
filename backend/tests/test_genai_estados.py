"""GESTION_EN_CURSO, GESTION_RECHAZADA y SIN_CUPO con la frase del Rol 4 (DEC-060).

Con el provider real (``content/``, sin HTTP): el beneficio de seguimiento se
nombra con la frase por estado de la instrucción 5 de ``content/prompts`` y
nunca dentro del marco "podrían servirle". Las frases neutras de
``PLANTILLAS_NEUTRAS`` son otras, así que el literal esperado prueba que la
frase sale de ``content/``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import runtime  # noqa: E402
from tests._genai_c3 import validar  # noqa: E402

FRASES_ESTADO = {
    "GESTION_EN_CURSO": "El trámite ya está en curso. Vale la pena esperar la respuesta.",
    "GESTION_RECHAZADA": "Vale la pena consultar en la institución qué opciones hay.",
    "SIN_CUPO": "Vale la pena consultar en la institución qué opciones hay.",
}


@pytest.mark.parametrize("estado", list(FRASES_ESTADO))
def test_seguimiento_usa_la_frase_del_rol4(monkeypatch, estado):
    monkeypatch.setattr(runtime, "_provider", None)
    provider = runtime.get_provider()
    assert provider is not None, "el catálogo de content/ debe cargar"
    frase = FRASES_ESTADO[estado]

    guion = provider.generar_guion(["BEN-001"], estados={"BEN-001": estado})
    validar("ScriptContent", guion)
    assert f"Subsidio Familiar: {frase}" in guion["script"]
    assert "podrían servirle" not in guion["script"]

    mensaje = provider.generar_mensaje(["BEN-001"], estados={"BEN-001": estado})
    validar("MessageContent", mensaje)
    assert f"Subsidio Familiar: {frase}" in mensaje["whatsapp_preview"]
    assert "podrían servirle" not in mensaje["whatsapp_preview"]
    seccion = mensaje["printable_card"]["sections"][0]
    assert seccion["reason"].startswith(f"{frase} ")
