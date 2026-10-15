"""Camino Bedrock de ``POST /familias/{id}/guion`` (FEAT-001).

Por HTTP (``TestClient``) y sin AWS: el cliente ``bedrock-runtime`` se inyecta,
el reloj del provider se sustituye (la suite no duerme), ``boto3`` no se
importa y ``E3_GUARDRAIL_ID`` es un valor SINTÉTICO.

Qué se fija aquí:

- Sin ``E3_LLM_PROVIDER`` (o con ``stub``) la respuesta es idéntica a hoy:
  ``provider='PLANTILLA'``, ``warnings=[]`` y el mismo script de plantilla.
- Con ``E3_LLM_PROVIDER=bedrock`` y el modelo respondiendo bien:
  ``provider='BEDROCK'``, el script es la prosa del modelo con el aviso exacto
  y el cuerpo valida contra ``ScriptGenerationEnvelope`` de C3.
- Ante CUALQUIER fallo (BedrockError, Guardrail que interviene, PiiLeakError,
  falta ``E3_GUARDRAIL_ID``, postvalidación, beneficio sin cita C4): HTTP 200,
  plantilla, ``warnings=['GENAI_DEGRADADO_A_PLANTILLA']`` y un log con solo el
  código del motivo. Nunca 500.
- Orden de barreras: el contexto se construye y valida ANTES de la primera
  llamada al cliente, y lo que viaja al modelo es solo la allowlist.
- Privacidad: ningún log lleva el prompt, la salida del modelo, títulos del
  catálogo ni el valor del Guardrail.
"""
from __future__ import annotations

import ast
import copy
import json
import logging
import sys
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import mock_data, runtime  # noqa: E402
from app.api.app import app  # noqa: E402
from app.genai import provider as prov  # noqa: E402
from app.genai import redaccion  # noqa: E402
from app.genai.content_catalog import cargar_catalogo_contenido  # noqa: E402
from app.genai.provider import BedrockProvider  # noqa: E402
from app.genai.template_provider import DISCLAIMER  # noqa: E402
from tests._bedrock_dobles import (  # noqa: E402
    ClienteFalso,
    _RelojFalso,
    respuesta_tooluse,
)
from tests._genai_c3 import validar  # noqa: E402

REPO_DIR = BACKEND_DIR.parent
_LLM_CONTEXT_SCHEMA = (
    REPO_DIR / ".kiro" / "specs" / "_shared" / "contracts"
    / "schemas" / "LlmContextV1.schema.json"
)

# Valores sintéticos: ningún id real de Guardrail, cuenta ni endpoint.
GUARDRAIL_SINTETICO = "GUARDRAIL-SINTETICO-TEST"
MODELO_SINTETICO = "modelo-sintetico-test"

FAM = "FAM-SIM-0001"          # mock con BEN-001, BEN-012 y BEN-018
FAM_SIMPLE = "FAM-SIM-0002"   # mock con solo BEN-001
IDS = ["BEN-001", "BEN-012"]
WARNING_DEGRADADO = "GENAI_DEGRADADO_A_PLANTILLA"

# Prosa admisible: texto plano, sin promesas, sin cifras y sin frases vetadas.
TEXTO_MODELO = (
    "Hola, buenos dias. Revisamos dos apoyos para conversar con su familia. "
    "Puede consultar en la institucion de cada apoyo y preguntar que documentos "
    "necesita llevar."
)

client = TestClient(app)


# --- fixtures ----------------------------------------------------------------

@pytest.fixture(autouse=True)
def entorno(monkeypatch) -> _RelojFalso:
    """Neutraliza el throttle y deja el entorno Bedrock en valores sintéticos."""
    reloj = _RelojFalso()
    monkeypatch.setattr(prov, "time", reloj)
    monkeypatch.setattr(BedrockProvider, "_ultima_llamada", 0.0)
    monkeypatch.setenv("E3_GUARDRAIL_ID", GUARDRAIL_SINTETICO)
    monkeypatch.setenv("E3_GUARDRAIL_VERSION", "1")
    monkeypatch.setenv("E3_BEDROCK_MODEL_ID", MODELO_SINTETICO)
    # El TemplateProvider y el proveedor LLM se reconstruyen por test.
    monkeypatch.setattr(runtime, "_provider", None)
    redaccion.reiniciar_proveedor()
    yield reloj
    redaccion.reiniciar_proveedor()


@pytest.fixture(scope="module")
def catalogo():
    """Catálogo C4 real de ``content/`` (solo lectura)."""
    return cargar_catalogo_contenido()


def _inyectar(monkeypatch, cliente: ClienteFalso) -> ClienteFalso:
    """Selecciona Bedrock y hace que el provider use el cliente falso."""
    monkeypatch.setenv("E3_LLM_PROVIDER", "bedrock")
    proveedor = BedrockProvider(cliente=cliente)
    monkeypatch.setattr(redaccion, "obtener_proveedor", lambda: proveedor)
    return cliente


def _cliente_ok(script: str = TEXTO_MODELO) -> ClienteFalso:
    return ClienteFalso(respuesta_converse=respuesta_tooluse({"script": script}))


def _post(ids: list[str], family_id: str = FAM):
    return client.post(
        f"/api/v1/familias/{family_id}/guion", json={"benefit_ids": ids}
    )


def _prompt_enviado(cliente: ClienteFalso) -> str:
    kwargs = dict(cliente.llamadas[1][1])
    return kwargs["messages"][0]["content"][0]["text"]


def _degradado(body: dict) -> None:
    """Afirma la forma exacta de una respuesta degradada a plantilla."""
    validar("ScriptGenerationEnvelope", body)
    assert body["provider"] == "PLANTILLA"
    assert body["warnings"] == [WARNING_DEGRADADO]
    assert body["content"]["script"].endswith(DISCLAIMER)


# --- (a) bandera ausente: nada cambia ---------------------------------------

def test_sin_bandera_responde_plantilla_y_no_toca_bedrock(monkeypatch):
    def _no_debe_llamarse(self):
        raise AssertionError("se intentó construir el cliente real de boto3")

    monkeypatch.setattr(BedrockProvider, "_crear_cliente", _no_debe_llamarse)
    r = _post(IDS)
    assert r.status_code == 200
    body = r.json()
    validar("ScriptGenerationEnvelope", body)
    assert body["provider"] == "PLANTILLA"
    assert body["warnings"] == []
    assert body["content"]["benefit_ids"] == IDS

    # Con ``stub`` el guion es exactamente el mismo (selector seguro).
    monkeypatch.setenv("E3_LLM_PROVIDER", "stub")
    assert _post(IDS).json()["content"] == body["content"]


# --- (b) camino feliz --------------------------------------------------------

def test_bedrock_ok_redacta_el_guion(monkeypatch):
    cliente = _inyectar(monkeypatch, _cliente_ok())
    r = _post(IDS)

    assert r.status_code == 200
    body = r.json()
    validar("ScriptGenerationEnvelope", body)
    assert body["provider"] == "BEDROCK"
    assert body["warnings"] == []
    assert body["content"]["benefit_ids"] == IDS
    # El aviso exacto lo agrega el servidor, no el modelo.
    assert body["content"]["script"] == f"{TEXTO_MODELO} {DISCLAIMER}"
    # Dos barreras Guardrail alrededor de una sola generación.
    assert cliente.operaciones == ["apply_guardrail", "converse", "apply_guardrail"]
    # El modelo solo escribe prosa: su salida estructurada es un único campo.
    tool = cliente.llamadas[1][1]["toolConfig"]["tools"][0]["toolSpec"]
    assert tool["inputSchema"]["json"] == redaccion.SCHEMA_GUION
    assert cliente.llamadas[1][1]["inferenceConfig"] == {
        "temperature": 0.2, "maxTokens": redaccion.MAX_TOKENS_GUION,
    }


def test_redactar_guion_normaliza_ids_duplicados(monkeypatch):
    """Misma normalización que el camino plantilla: sin repetidos y máximo tres.

    C3 ya rechaza duplicados en el cuerpo público (422), así que esta
    invariante se ejercita llamando a la capa de redacción directamente.
    """
    monkeypatch.setenv("E3_LLM_PROVIDER", "bedrock")
    cliente = _cliente_ok()
    content = redaccion.redactar_guion(
        ["BEN-001", "BEN-001", "BEN-012", "BEN-001"],
        mock_data.FAMILIAS[FAM],
        request_id="REQ-sintetico-0001",
        provider=BedrockProvider(cliente=cliente),
    )

    assert content["benefit_ids"] == IDS
    assert content["script"] == f"{TEXTO_MODELO} {DISCLAIMER}"
    # El beneficio repetido viaja una sola vez por sección del envelope.
    assert _prompt_enviado(cliente).count('"benefit_id": "BEN-001"') == 2


# --- (c) error de Bedrock ----------------------------------------------------

def test_error_de_converse_degrada_a_plantilla(monkeypatch, caplog):
    _inyectar(monkeypatch, ClienteFalso(
        error_converse=RuntimeError("fallo simulado de boto3")))
    with caplog.at_level(logging.DEBUG):
        r = _post(IDS)

    assert r.status_code == 200
    _degradado(r.json())
    assert "genai_degradado_a_plantilla: motivo=" in caplog.text
    assert f"motivo={redaccion.MOTIVO_BEDROCK_ERROR}" in caplog.text


# --- (d) Guardrails ----------------------------------------------------------

def test_guardrail_input_degrada_sin_llamar_converse(monkeypatch, caplog):
    cliente = _inyectar(monkeypatch, ClienteFalso(
        acciones_guardrail=["GUARDRAIL_INTERVENED"],
        respuesta_converse=respuesta_tooluse({"script": TEXTO_MODELO})))
    with caplog.at_level(logging.DEBUG):
        r = _post(IDS)

    assert r.status_code == 200
    _degradado(r.json())
    assert cliente.operaciones == ["apply_guardrail"]
    assert f"motivo={redaccion.MOTIVO_GUARDRAIL_INTERVINO}" in caplog.text


def test_guardrail_output_descarta_el_texto_del_modelo(monkeypatch):
    texto = "Texto bloqueado por la segunda barrera."
    cliente = _inyectar(monkeypatch, ClienteFalso(
        acciones_guardrail=["NONE", "GUARDRAIL_INTERVENED"],
        respuesta_converse=respuesta_tooluse({"script": texto})))
    r = _post(IDS)

    assert r.status_code == 200
    _degradado(r.json())
    assert cliente.operaciones == ["apply_guardrail", "converse", "apply_guardrail"]
    assert texto not in r.text


# --- (e) qué viaja al modelo -------------------------------------------------

def test_contexto_es_exactamente_la_allowlist(monkeypatch):
    cliente = _inyectar(monkeypatch, _cliente_ok())
    capturado: dict = {}
    original = redaccion.construir_llm_context

    def _recorder(c1, c2, benefits):
        salida = original(c1, c2, benefits)
        capturado["contexto"] = copy.deepcopy(salida)
        # (g) orden de barreras: nada se llamó todavía.
        capturado["operaciones_previas"] = list(cliente.operaciones)
        return salida

    monkeypatch.setattr(redaccion, "construir_llm_context", _recorder)
    assert _post(IDS).json()["provider"] == "BEDROCK"

    contexto = capturado["contexto"]
    with _LLM_CONTEXT_SCHEMA.open(encoding="utf-8") as fh:
        jsonschema.validate(contexto, json.load(fh))
    assert set(contexto) == {
        "composition", "rsh_band", "income_band",
        "preferred_format", "language", "benefits",
    }
    assert [b["benefit_id"] for b in contexto["benefits"]] == IDS
    # Minimización: ningún monto viaja al modelo (PREG-047).
    assert all(b["amount"] is None for b in contexto["benefits"])
    assert all(b["reason_codes"] == [] for b in contexto["benefits"])
    assert capturado["operaciones_previas"] == []

    enviado = json.dumps(cliente.llamadas, ensure_ascii=False, default=str)
    for prohibido in (FAM, "family_id", "urgency_signals", "vulnerability_signals",
                      "inconsistency_codes", "estimated_annual_amount", "priority_score"):
        assert prohibido not in enviado


def test_la_ficha_de_la_familia_no_se_muta(monkeypatch):
    _inyectar(monkeypatch, _cliente_ok())
    antes = copy.deepcopy(mock_data.FAMILIAS[FAM])
    assert _post(IDS).json()["provider"] == "BEDROCK"
    assert mock_data.FAMILIAS[FAM] == antes


# --- (f) logs sin contenido --------------------------------------------------

def test_logs_sin_prompt_ni_salida_ni_titulos(monkeypatch, caplog, catalogo):
    cliente = _inyectar(monkeypatch, _cliente_ok())
    with caplog.at_level(logging.DEBUG):
        assert _post(IDS).json()["provider"] == "BEDROCK"

    # Lo que registra la aplicación (``httpx`` del TestClient no es la app).
    propio = "\n".join(
        r.getMessage() for r in caplog.records if r.name.startswith("app")
    )
    assert TEXTO_MODELO not in caplog.text
    assert "Reglas del servidor" not in caplog.text
    assert _prompt_enviado(cliente) not in caplog.text
    assert GUARDRAIL_SINTETICO not in caplog.text
    # La app solo loguea la ruta normalizada: ningún identificador de familia.
    assert FAM not in propio
    for entrada in catalogo.entradas.values():
        assert entrada.title not in propio
        assert entrada.description not in propio
    # Sí se registra la métrica agregada permitida.
    assert "genai_redaccion: operacion=SCRIPT estado=OK" in propio


# --- (g) orden de barreras y vía única hacia el modelo -----------------------

def test_pii_leak_degrada_sin_tocar_el_cliente(monkeypatch, caplog):
    cliente = _inyectar(monkeypatch, _cliente_ok())

    def _fuga(*_args, **_kwargs):
        raise redaccion.PiiLeakError("fuga simulada")

    monkeypatch.setattr(redaccion, "construir_llm_context", _fuga)
    with caplog.at_level(logging.DEBUG):
        r = _post(IDS)

    assert r.status_code == 200
    _degradado(r.json())
    assert cliente.llamadas == []
    assert f"motivo={redaccion.MOTIVO_CONTEXTO_RECHAZADO}" in caplog.text


def test_solo_redaccion_y_caracterizador_invocan_al_proveedor():
    """Ningún módulo de ``app/api/`` llama a ``generar`` directamente."""
    modulos: set[str] = set()
    for ruta in (BACKEND_DIR / "app").rglob("*.py"):
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "generar"
            ):
                modulos.add(ruta.relative_to(BACKEND_DIR).as_posix())
    assert modulos == {"app/genai/redaccion.py", "app/genai/caracterizador.py"}


# --- (h, i) postvalidación de la salida del modelo ---------------------------

@pytest.mark.parametrize("script, motivo", [
    ("La familia tiene derecho a $250.000 este mes.", redaccion.MOTIVO_POSTVALIDACION),
    ("Vale la pena consultar en la institucion.", redaccion.MOTIVO_POSTVALIDACION),
    ("Su familia podria calificar al apoyo.", redaccion.MOTIVO_POSTVALIDACION),
    ("Revise <b>este apoyo</b> en la oficina.", redaccion.MOTIVO_POSTVALIDACION),
])
def test_salida_con_promesa_o_markup_degrada(monkeypatch, caplog, script, motivo):
    _inyectar(monkeypatch, _cliente_ok(script))
    with caplog.at_level(logging.DEBUG):
        r = _post(IDS)

    assert r.status_code == 200
    _degradado(r.json())
    assert f"motivo={motivo}" in caplog.text
    assert script not in r.text


def test_salida_estructurada_con_campo_extra_degrada(monkeypatch, caplog):
    cliente = _inyectar(monkeypatch, ClienteFalso(
        respuesta_converse=respuesta_tooluse(
            {"script": TEXTO_MODELO, "benefit_ids": ["BEN-999"]})))
    with caplog.at_level(logging.DEBUG):
        r = _post(IDS)

    assert r.status_code == 200
    _degradado(r.json())
    # La postvalidación del provider la rechaza antes de la barrera de salida.
    assert cliente.operaciones == ["apply_guardrail", "converse"]
    assert f"motivo={redaccion.MOTIVO_BEDROCK_ERROR}" in caplog.text


# --- (j, k) datos que no habilitan el camino Bedrock ------------------------

def test_benefit_id_que_no_es_oportunidad_degrada(monkeypatch, caplog):
    cliente = _inyectar(monkeypatch, _cliente_ok())
    with caplog.at_level(logging.DEBUG):
        r = _post(["BEN-005"], family_id=FAM_SIMPLE)

    assert r.status_code == 200
    _degradado(r.json())
    assert cliente.llamadas == []
    assert f"motivo={redaccion.MOTIVO_SIN_RESULTADO_MOTOR}" in caplog.text


def test_beneficio_sin_cita_c4_degrada(monkeypatch, caplog):
    cliente = _inyectar(monkeypatch, _cliente_ok())
    with caplog.at_level(logging.DEBUG):
        r = _post(["BEN-018"])

    assert r.status_code == 200
    _degradado(r.json())
    assert cliente.llamadas == []
    assert f"motivo={redaccion.MOTIVO_SIN_CITA_C4}" in caplog.text


# --- (l) la CONSTRUCCIÓN del proveedor también falla cerrada ----------------

def test_sin_guardrail_configurado_degrada(monkeypatch, caplog):
    """Sin ``E3_GUARDRAIL_ID`` (o sin boto3) no se llama a Bedrock: 200 y plantilla."""
    monkeypatch.delenv("E3_GUARDRAIL_ID", raising=False)
    monkeypatch.setenv("E3_LLM_PROVIDER", "bedrock")
    with caplog.at_level(logging.DEBUG):
        r = _post(IDS)

    assert r.status_code == 200
    _degradado(r.json())
    assert f"motivo={redaccion.MOTIVO_PROVEEDOR_NO_DISPONIBLE}" in caplog.text


def test_familia_inexistente_sigue_404(monkeypatch):
    _inyectar(monkeypatch, _cliente_ok())
    assert _post(IDS, family_id="FAM-NO-EXISTE").status_code == 404


def test_benefit_id_desconocido_sigue_422(monkeypatch):
    cliente = _inyectar(monkeypatch, _cliente_ok())
    r = _post(["BEN-999"])
    assert r.status_code == 422
    assert cliente.llamadas == []
    assert "BEN-999" not in r.text


# --- unitarios: envelope interno y render del prompt ------------------------

def _contexto_y_items(catalogo, ids: list[str], family_id: str = FAM):
    familia = mock_data.FAMILIAS[family_id]
    contexto = redaccion.construir_llm_context(
        [],
        redaccion.vista_c2_minima(familia["context"]),
        redaccion.benefits_autorizados(familia, ids),
    )
    return contexto, redaccion.catalog_items(catalogo.entradas, ids)


def test_envelope_familia_valido(catalogo):
    prompt = catalogo.prompts["PROMPT-GUION"]
    contexto, items = _contexto_y_items(catalogo, IDS)
    envelope = redaccion.construir_envelope_familia(
        redaccion.OPERACION_GUION, contexto, items, prompt)

    assert envelope["operation"] == "SCRIPT"
    assert envelope["prompt_template_id"] == "PROMPT-GUION"
    assert envelope["prompt_version"] == prompt.version
    assert envelope["output_schema_version"] == prompt.meta["output_schema_version"]
    assert [i["benefit_id"] for i in envelope["catalog_items"]] == IDS
    for item in envelope["catalog_items"]:
        assert item["official_url"].startswith("https://")
        assert item["actions"] and item["source_ids"]


def test_envelope_familia_manipulado_falla_cerrado(catalogo):
    prompt = catalogo.prompts["PROMPT-GUION"]
    contexto, items = _contexto_y_items(catalogo, IDS)
    contexto["rsh_band"] = 41  # fuera del enum cerrado de LlmContextV1

    with pytest.raises(redaccion.RedaccionError) as exc:
        redaccion.construir_envelope_familia(
            redaccion.OPERACION_GUION, contexto, items, prompt)
    assert exc.value.motivo == redaccion.MOTIVO_ENVELOPE_INVALIDO
    # El mensaje es solo el código: nunca el valor que falló.
    assert str(exc.value) == redaccion.MOTIVO_ENVELOPE_INVALIDO


def test_renderizar_prompt_resuelve_variables_y_anexa_reglas(catalogo):
    prompt = catalogo.prompts["PROMPT-GUION"]
    contexto, items = _contexto_y_items(catalogo, IDS)
    envelope = redaccion.construir_envelope_familia(
        redaccion.OPERACION_GUION, contexto, items, prompt)

    texto = redaccion.renderizar_prompt(prompt, envelope)

    assert "{{" not in texto
    assert "## Reglas del servidor" in texto
    assert "## Plantilla de respaldo" not in texto
    assert '"SCRIPT"' in texto
    assert '"benefit_id": "BEN-001"' in texto
    assert FAM not in texto
    # El bloque del servidor va al final para prevalecer.
    assert texto.index("## Reglas del servidor") > texto.index("## Variables")


def test_renderizar_prompt_sin_variable_falla_cerrado(catalogo):
    from app.genai.content_catalog import PromptC4

    prompt = catalogo.prompts["PROMPT-GUION"]
    roto = PromptC4(
        template_id=prompt.template_id,
        version=prompt.version,
        meta={**prompt.meta, "variables": ["no_existe_en_el_envelope"]},
        cuerpo=prompt.cuerpo,
    )
    contexto, items = _contexto_y_items(catalogo, IDS)
    envelope = redaccion.construir_envelope_familia(
        redaccion.OPERACION_GUION, contexto, items, prompt)

    with pytest.raises(redaccion.RedaccionError) as exc:
        redaccion.renderizar_prompt(roto, envelope)
    assert exc.value.motivo == redaccion.MOTIVO_PROMPT_C4_INVALIDO


def test_payload_con_patron_prohibido_falla_cerrado():
    with pytest.raises(redaccion.RedaccionError) as exc:
        redaccion._exigir_payload_limpio("contacto: 11.111.111-1", None)
    assert exc.value.motivo == redaccion.MOTIVO_EGRESO_SOSPECHOSO

    with pytest.raises(redaccion.RedaccionError):
        redaccion._exigir_payload_limpio(f"familia {FAM} revisada", FAM)


def test_bedrock_seleccionado_es_seguro_por_defecto(monkeypatch):
    monkeypatch.delenv("E3_LLM_PROVIDER", raising=False)
    assert redaccion.bedrock_seleccionado() is False
    monkeypatch.setenv("E3_LLM_PROVIDER", "stub")
    assert redaccion.bedrock_seleccionado() is False
    monkeypatch.setenv("E3_LLM_PROVIDER", " Bedrock ")
    assert redaccion.bedrock_seleccionado() is True
