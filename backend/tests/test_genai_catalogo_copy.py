"""Invariantes de copy y longitud sobre TODO el contenido real de ``content/``.

Con el provider real (sin HTTP, para que sea rápido):

- Las 1140 combinaciones de 3 de los 20 beneficios para el guion y las 680 de
  los 17 citables para el mensaje caben en los límites de C3 sin truncar.
- Toda URL sale de ``official_url`` de ``beneficios.yaml``.
- Ninguna salida (incluidos asistente y textos sin catálogo) promete
  elegibilidad ni menciona montos (DEC-054), ni trae markup o URLs en texto.
"""
from __future__ import annotations

import itertools
import re
import sys
from pathlib import Path

import pytest
import yaml

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import runtime  # noqa: E402
from app.genai.template_provider import (  # noqa: E402
    ASISTENTE_SIN_CATALOGO,
    DISCLAIMER,
    GUION_SIN_CATALOGO,
    asistente_sin_catalogo,
    contiene_promesa,
    es_texto_plano,
)
from tests._genai_c3 import validar  # noqa: E402

CONTENT_DIR = BACKEND_DIR.parent / "content"
with (CONTENT_DIR / "beneficios.yaml").open(encoding="utf-8") as _fh:
    BEN = {b["benefit_id"]: b for b in yaml.safe_load(_fh)["beneficios"]}
IDS = list(BEN)
CITABLES = [b for b in IDS if BEN[b]["official_url"]]
URLS = {BEN[b]["official_url"] for b in CITABLES}
PREGUNTAS = [
    "¿Qué es el Subsidio Familiar?",
    "¿Qué es el Subsidio Familiar automático?",
    "¿Qué es la canasta familiar?",
    "¿Qué beneficios existen?",
    "¿Dónde se actualiza el Registro Social de Hogares?",
    "¿Yo califico para el subsidio?",
    "Subsidio Familiar, Bono por Hijo y Asignación Familiar",
]


@pytest.fixture(scope="module")
def provider():
    original = runtime._provider
    runtime._provider = None
    p = runtime.get_provider()
    assert p is not None, "el catálogo de content/ debe cargar"
    yield p
    runtime._provider = original


def _assert_copy(texto: str) -> None:
    """Texto visible: sin promesas, sin montos, sin markup ni URLs."""
    sin_aviso = texto.replace(DISCLAIMER, "")
    assert not contiene_promesa(texto), texto
    assert es_texto_plano(sin_aviso), texto
    assert "corresponderle" not in texto.lower()
    assert "FALLBACK_TEMPLATE" not in texto


def _elegibles(combo) -> dict[str, str]:
    return {bid: "ELEGIBLE_SIN_ASIGNACION" for bid in combo}


def _frases(texto: str) -> list[str]:
    """Oraciones de una descripción de ``content/`` (separadas tras '.', '!' o '?')."""
    return re.split(r"(?<=[.!?])\s+", texto.strip())


def test_guion_todas_las_combinaciones(provider):
    for combo in itertools.combinations(IDS, 3):
        script = provider.generar_guion(list(combo), estados=_elegibles(combo))["script"]
        assert len(script) <= 1200
        assert script.endswith(DISCLAIMER)
        for bid in combo:
            assert BEN[bid]["simple_title"] in script
            # DEC-061: el guion lleva solo la primera frase de la descripción.
            frases = _frases(BEN[bid]["description"])
            assert f"{BEN[bid]['simple_title']}: {frases[0]}" in script
            for resto in frases[1:]:
                assert resto not in script
        _assert_copy(script)


def test_guion_maximo_120_palabras(provider):
    """El guion más largo (141 palabras con la descripción completa) cabe en 120 (DEC-061)."""
    combo = ["BEN-006", "BEN-019", "BEN-020"]
    script = provider.generar_guion(combo, estados=_elegibles(combo))["script"]
    assert len(script.split()) <= 120


def test_mensaje_todas_las_combinaciones(provider):
    for combo in itertools.combinations(CITABLES, 3):
        content = provider.generar_mensaje(list(combo), estados=_elegibles(combo))
        preview = content["whatsapp_preview"]
        assert len(preview) <= 600 and preview.endswith(DISCLAIMER)
        _assert_copy(preview)
        card = content["printable_card"]
        _assert_copy(card["title"])
        _assert_copy(card["introduction"])
        for sec in card["sections"]:
            b = BEN[sec["benefit_id"]]
            assert len(sec["heading"]) <= 100
            assert len(sec["reason"]) <= 240 and sec["reason"].endswith(b["description"])
            assert len(sec["action"]) <= 240
            assert sec["where_to_go"] is None or len(sec["where_to_go"]) <= 160
            for campo in ("heading", "reason", "action"):
                _assert_copy(sec[campo])
            if sec["where_to_go"]:
                _assert_copy(sec["where_to_go"])
            assert all(s["url"] in URLS for s in sec["sources"])


def test_muestra_valida_contra_c3(provider):
    combos = list(itertools.combinations(CITABLES, 3))[::34][:20]
    assert len(combos) == 20
    for combo in combos:
        validar("ScriptContent", provider.generar_guion(list(combo), estados=_elegibles(combo)))
        validar("MessageContent",
                provider.generar_mensaje(list(combo), estados=_elegibles(combo)))


@pytest.mark.parametrize("pregunta", PREGUNTAS)
def test_asistente_sin_promesas(provider, pregunta):
    env = provider.responder_asistente("REQ-TEST", pregunta)
    validar("AssistantEnvelope", env)
    assert len(env["answer"]) <= 2000
    _assert_copy(env["answer"])
    assert all(c["url"] in URLS for c in env["citations"])


@pytest.mark.parametrize("pregunta", ["¿Qué beneficios existen?", "¿Yo califico?"])
def test_textos_sin_catalogo_sin_promesas(pregunta):
    for texto in (GUION_SIN_CATALOGO, ASISTENTE_SIN_CATALOGO):
        _assert_copy(texto)
    env = asistente_sin_catalogo("REQ-TEST", pregunta)
    validar("AssistantEnvelope", env)
    _assert_copy(env["answer"])
