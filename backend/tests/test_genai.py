"""Tests de la base de IA generativa (provider stub + caracterizador).

Verifican que la capa GenAI funciona SIN AWS (plan B §4) y que respeta el
límite de la spec: el LLM propone (DECLARADO/no acreditado), no decide.
No requieren red ni boto3.
"""
from __future__ import annotations

from app.genai import StubProvider, get_provider
from app.genai.caracterizador import SCHEMA_CARACTERIZACION, caracterizar_texto_libre


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


def test_bedrock_no_implementado_pero_seleccionable():
    """El BedrockProvider existe como esqueleto; aún no funcional (Rol 2)."""
    from app.genai.provider import BedrockProvider
    p = BedrockProvider()
    assert p.nombre == "bedrock"
    try:
        p.generar("x")
        assert False, "debería lanzar NotImplementedError"
    except NotImplementedError:
        pass
