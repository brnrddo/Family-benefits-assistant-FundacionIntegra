"""Tests de la base de IA generativa (provider stub + caracterizador).

Verifican que la capa GenAI funciona SIN AWS (plan B §4) y que respeta el
límite de la spec: el LLM propone (DECLARADO/no acreditado), no decide.
No requieren red ni boto3.
"""
from __future__ import annotations

import pytest

from app.genai import LLMProvider, LLMResponse, PiiLeakError, StubProvider, get_provider
from app.genai.caracterizador import SCHEMA_CARACTERIZACION, caracterizar_texto_libre

# Valor sintético: ningún id real de Guardrail, cuenta ni endpoint.
GUARDRAIL_SINTETICO = "GUARDRAIL-SINTETICO-TEST"


def test_get_provider_default_es_stub():
    p = get_provider()
    assert isinstance(p, StubProvider)
    assert p.nombre == "stub"


def test_stub_prosa_no_vacia():
    r = StubProvider().generar("hola")
    assert r.texto and r.proveedor == "stub"
    assert r.datos is None


def test_stub_respeta_json_schema():
    r = StubProvider().generar("x", json_schema=SCHEMA_CARACTERIZACION)
    assert r.datos is not None
    # el esqueleto trae las claves del schema
    assert "integrantes_detectados" in r.datos
    assert isinstance(r.datos["integrantes_detectados"], list)


def test_caracterizar_marca_declarado_no_acreditado():
    """La propuesta del LLM nunca es verdad confirmada (no decide elegibilidad)."""
    out = caracterizar_texto_libre(
        "vive con la abuela y dos niños",
        contexto_filtrado={"composicion": [], "rsh": {"tramo": 40}},
    )
    assert out["origen"] == "LLM"
    assert out["estado_dato"] == "DECLARADO"
    assert out["acreditada"] is False
    assert out["proveedor"] == "stub"


def test_bedrock_sin_guardrail_falla_cerrado(monkeypatch):
    """Seleccionar Bedrock sin Guardrail configurado no llega a AWS.

    El comportamiento completo del proveedor se prueba en
    ``test_genai_bedrock.py`` (con un cliente falso, sin red ni boto3).
    """
    from app.genai.provider import BedrockProvider, GuardrailNoConfigurado

    monkeypatch.delenv("E3_GUARDRAIL_ID", raising=False)
    assert BedrockProvider.nombre == "bedrock"
    with pytest.raises(GuardrailNoConfigurado):
        BedrockProvider()


class _ProveedorRemotoFalso(LLMProvider):
    """Proveedor no local: si se lo llama, el texto libre habría salido."""

    nombre = "bedrock"

    def __init__(self):
        self.llamadas = 0

    def generar(self, prompt, *, system=None, json_schema=None,
                temperatura: float = 0.2, max_tokens: int = 1024,
                request_id=None) -> LLMResponse:
        self.llamadas += 1
        raise AssertionError("el texto libre no debe viajar a un proveedor remoto")


def test_caracterizar_rechaza_proveedor_no_local():
    """El patrón de texto libre no puede egresar: falla cerrado antes del prompt."""
    remoto = _ProveedorRemotoFalso()

    with pytest.raises(PiiLeakError) as exc:
        caracterizar_texto_libre(
            "vive con la abuela postrada", contexto_filtrado={}, provider=remoto)

    assert remoto.llamadas == 0
    # El mensaje nombra el proveedor, nunca el texto de la tía.
    assert "abuela" not in str(exc.value)


def test_caracterizar_con_bedrock_por_entorno_no_llama_a_bedrock(monkeypatch):
    """Cambiar ``E3_LLM_PROVIDER`` no habilita esa vía de egreso."""
    from app.genai.provider import BedrockProvider

    llamadas: list[str] = []

    class _ClienteQueNoDebeUsarse:
        def apply_guardrail(self, **kwargs):
            llamadas.append("apply_guardrail")
            raise AssertionError("no debe llamarse")

        def converse(self, **kwargs):
            llamadas.append("converse")
            raise AssertionError("no debe llamarse")

    monkeypatch.setenv("E3_LLM_PROVIDER", "bedrock")
    monkeypatch.setenv("E3_GUARDRAIL_ID", GUARDRAIL_SINTETICO)
    monkeypatch.setattr(BedrockProvider, "_crear_cliente",
                        lambda self: _ClienteQueNoDebeUsarse())

    with pytest.raises(PiiLeakError):
        caracterizar_texto_libre(
            "vive con la abuela postrada", contexto_filtrado={"composicion": []})

    assert llamadas == []
