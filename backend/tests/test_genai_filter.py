"""Tests del filtro de privacidad GenAI y del TemplateProvider (FEAT-002).

- ``construir_llm_context`` rechaza PII incrustada en C1/C2 (allowlist positiva)
  y produce un ``LlmContextV1`` válido contra el schema cerrado.
- ``TemplateProvider`` produce ScriptContent/MessageContent/AssistantEnvelope
  válidos contra los schemas de respuesta de C3, con disclaimer exacto, sin
  HTML/CSS/handlers y con citas del catálogo C4.
- Una consulta individual devuelve REQUIRES_DETERMINISTIC_EVALUATION sin Bedrock.
- Ningún log del módulo transporta cuerpos/prompts/respuestas.

No requieren red ni boto3.
"""
from __future__ import annotations

import copy
import json
import logging
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

REPO_DIR = BACKEND_DIR.parent
_C3_PATH = REPO_DIR / ".kiro" / "specs" / "_shared" / "contracts" / "C3-api.openapi.yaml"

from app.genai import (  # noqa: E402
    DISCLAIMER,
    CatalogEntry,
    PiiLeakError,
    TemplateProvider,
    construir_llm_context,
)


# --- Carga de los schemas C3 para validación --------------------------------

def _c3_components() -> dict:
    with _C3_PATH.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    return doc["components"]["schemas"]


def _validar_c3(instancia: dict, schema_name: str) -> None:
    """Valida ``instancia`` contra ``#/components/schemas/<schema_name>``."""
    schemas = _c3_components()
    root = {
        "$id": "urn:c3-local",
        "components": {"schemas": schemas},
        "$ref": f"#/components/schemas/{schema_name}",
    }
    jsonschema.validate(instancia, root)


# --- Fixtures sintéticos -----------------------------------------------------

def _c2_limpio() -> dict:
    return {
        "composition": [
            {"role": "ADULT_REFERENCE", "age": 34},
            {"role": "CHILD", "age": 4},
        ],
        "rsh_band": 40,
        "income_band": "UNDER_110K",
        "preferred_format": "TEXT",
        "language": "es",
    }


def _benefits_limpios() -> list[dict]:
    return [
        {
            "benefit_id": "BEN-001",
            "result": "SI",
            "level": "PRELIMINAR",
            "access_state": "ELEGIBLE_SIN_ASIGNACION",
            "reason_codes": ["CRITERIOS_CUMPLEN"],
            "missing_codes": ["rsh_status"],
            "amount": 50000,
            "source_ids": ["SRC-OFICIAL"],
        },
    ]


def _catalogo() -> dict:
    return {
        "BEN-001": CatalogEntry(
            benefit_id="BEN-001",
            title="Subsidio Único Familiar",
            reason="Según su ficha, podría corresponderle este apoyo.",
            action="Vale la pena consultar los requisitos en la institución.",
            where_to_go="ChileAtiende de su comuna",
            source_id="SRC-OFICIAL",
            source_url="https://www.chileatiende.gob.cl/",
        ),
        "BEN-012": CatalogEntry(
            benefit_id="BEN-012",
            title="Aporte Familiar Permanente",
            reason="Podría corresponderle según su situación.",
            action="Consulte en la institución para confirmar.",
            where_to_go=None,
            source_id="SRC-OFICIAL",
            source_url="https://www.chileatiende.gob.cl/",
        ),
    }


# --- (a) rechazo de PII adversarial -----------------------------------------

@pytest.mark.parametrize(
    "clave_pii",
    ["nombre", "rut", "folio", "telefono", "direccion", "nacionalidad", "diagnostico"],
)
def test_construir_llm_context_rechaza_pii_en_c2(clave_pii):
    c2 = _c2_limpio()
    c2[clave_pii] = "valor sensible"
    with pytest.raises(PiiLeakError):
        construir_llm_context([], c2, _benefits_limpios())


def test_construir_llm_context_rechaza_pii_en_composicion():
    c2 = _c2_limpio()
    c2["composition"][0]["nombre"] = "Juan"
    with pytest.raises(PiiLeakError):
        construir_llm_context([], c2, _benefits_limpios())


def test_construir_llm_context_rechaza_pii_en_beneficio():
    benefits = _benefits_limpios()
    benefits[0]["telefono"] = "+56 9 1234 5678"
    with pytest.raises(PiiLeakError):
        construir_llm_context([], _c2_limpio(), benefits)


def test_construir_llm_context_rechaza_qr_y_codigo():
    benefits = _benefits_limpios()
    benefits[0]["qr"] = "https://qr/abc"
    with pytest.raises(PiiLeakError):
        construir_llm_context([], _c2_limpio(), benefits)


def test_construir_llm_context_rechaza_pii_en_c1():
    c1 = [{"id_familia": "FAM", "rut": "11.111.111-1"}]
    with pytest.raises(PiiLeakError):
        construir_llm_context(c1, _c2_limpio(), _benefits_limpios())


def test_construir_llm_context_rechaza_valor_fuera_de_allowlist():
    c2 = _c2_limpio()
    c2["income_band"] = "SECRETO"  # no está en el enum cerrado
    with pytest.raises(PiiLeakError):
        construir_llm_context([], c2, _benefits_limpios())


# --- (b) contexto limpio produce LlmContextV1 válido ------------------------

def test_construir_llm_context_valido_contra_schema():
    schema_path = (
        REPO_DIR / ".kiro" / "specs" / "_shared" / "contracts"
        / "schemas" / "LlmContextV1.schema.json"
    )
    with schema_path.open(encoding="utf-8") as fh:
        schema = json.load(fh)

    out = construir_llm_context([], _c2_limpio(), _benefits_limpios())
    jsonschema.validate(out, schema)
    assert out["composition"] == [
        {"role": "ADULT_REFERENCE", "age": 34},
        {"role": "CHILD", "age": 4},
    ]
    assert out["benefits"][0]["benefit_id"] == "BEN-001"
    # Ninguna clave inesperada se arrastró.
    assert set(out) == {
        "composition", "rsh_band", "income_band",
        "preferred_format", "language", "benefits",
    }


# --- (c) TemplateProvider válido contra C3 ----------------------------------

def test_guion_valido_contra_c3():
    tp = TemplateProvider(_catalogo())
    content = tp.generar_guion(["BEN-001", "BEN-012"])
    _validar_c3(content, "ScriptContent")
    assert DISCLAIMER in content["script"]
    assert len(content["script"]) <= 1200


def test_mensaje_valido_contra_c3_y_disclaimer():
    tp = TemplateProvider(_catalogo())
    content = tp.generar_mensaje(["BEN-001"])
    _validar_c3(content, "MessageContent")
    assert content["printable_card"]["format_version"] == "CARD_V1"
    assert DISCLAIMER in content["whatsapp_preview"]
    # Citas provienen del catálogo autorizado (HTTPS).
    for sec in content["printable_card"]["sections"]:
        for src in sec["sources"]:
            assert src["url"].startswith("https://")


def test_asistente_catalogo_valido_contra_c3():
    tp = TemplateProvider(_catalogo())
    env = tp.responder_asistente("req-1", "¿Qué beneficios existen para familias?")
    _validar_c3(env, "AssistantEnvelope")
    assert env["intent"] == "CATALOG_INFO"
    assert env["provider"] == "PLANTILLA"
    assert env["disclaimer"] == DISCLAIMER


# --- (d) PrintableCard no transporta markup ---------------------------------

def test_printable_card_neutraliza_markup():
    cat = _catalogo()
    cat["BEN-001"] = CatalogEntry(
        benefit_id="BEN-001",
        title="<script>alert(1)</script>Subsidio",
        reason="onclick=hack() texto .class{color:red} normal",
        action="visite https://malicioso.example/pay ahora",
        where_to_go="<b>oficina</b>",
        source_id="SRC-OFICIAL",
        source_url="https://www.chileatiende.gob.cl/",
    )
    tp = TemplateProvider(cat)
    content = tp.generar_mensaje(["BEN-001"])
    _validar_c3(content, "MessageContent")

    blob = json.dumps(content, ensure_ascii=False)
    assert "<script>" not in blob
    assert "</b>" not in blob
    assert "onclick=" not in blob
    # La única URL permitida es la cita HTTPS inventariada del catálogo.
    assert "malicioso.example" not in blob
    assert "{color" not in blob


# --- (e) consulta individual sin Bedrock ------------------------------------

def test_asistente_pregunta_individual_sin_bedrock():
    tp = TemplateProvider(_catalogo())
    env = tp.responder_asistente("req-2", "¿Yo califico para el subsidio?")
    _validar_c3(env, "AssistantEnvelope")
    assert env["intent"] == "REQUIRES_DETERMINISTIC_EVALUATION"
    assert env["provider"] == "PLANTILLA"


# --- (f) logs sin cuerpos/prompts/respuestas --------------------------------

def test_sin_logs_con_contenido_sensible(caplog):
    with caplog.at_level(logging.DEBUG):
        c2 = _c2_limpio()
        construir_llm_context([], c2, _benefits_limpios())
        tp = TemplateProvider(_catalogo())
        tp.generar_mensaje(["BEN-001"])
        tp.responder_asistente("req-3", "¿Yo califico para el subsidio?")

    texto_logs = "\n".join(r.getMessage() for r in caplog.records)
    # No se emite prompt, pregunta ni respuesta en los logs.
    assert "califico" not in texto_logs
    assert DISCLAIMER not in texto_logs
    assert "whatsapp_preview" not in texto_logs
