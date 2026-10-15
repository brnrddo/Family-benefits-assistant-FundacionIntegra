"""Tests de ``BedrockProvider``: Converse + Guardrails INPUT/OUTPUT (API-007/008).

No requieren red, credenciales ni boto3 instalado:

- el cliente ``bedrock-runtime`` se **inyecta** (``BedrockProvider(cliente=...)``),
  así nunca se construye el real ni se importa boto3;
- el throttle (≥1.1 s entre llamadas) se neutraliza sustituyendo el módulo
  ``time`` que usa ``app.genai.provider`` por un reloj falso: la suite no
  duerme y la lógica del throttle se verifica aparte con ese mismo reloj.

Cubre las garantías de privacidad del cambio: sin Guardrail no se llama a
Bedrock, el Guardrail actúa como DOS barreras separadas, los errores de boto3 se
convierten en ``BedrockError`` capturable (para degradar a ``TemplateProvider``)
y ni los mensajes de error ni los logs transportan el prompt o la salida.
"""
from __future__ import annotations

import ast
import inspect
import json
import logging
import time
from pathlib import Path

import pytest

from app.genai import provider as prov
from app.genai.provider import (
    BedrockError,
    BedrockProvider,
    GuardrailIntervino,
    GuardrailNoConfigurado,
)

# Valores sintéticos: ningún id real de Guardrail, cuenta ni endpoint.
GUARDRAIL_SINTETICO = "GUARDRAIL-SINTETICO-TEST"
MODELO_SINTETICO = "modelo-sintetico-test"
REQUEST_ID_SINTETICO = "req-sintetico-0001"
PROMPT = "Explique el beneficio BEN-001 segun los hechos resueltos por el motor."


# --- dobles de prueba -------------------------------------------------------

class _RelojFalso:
    """Reemplaza al módulo ``time`` dentro del provider: no duerme de verdad."""

    def __init__(self, inicio: float = 0.0):
        self.t = inicio
        self.esperas: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, segundos: float) -> None:
        self.esperas.append(segundos)
        self.t += segundos


class _ClienteFalso:
    """Doble del cliente ``bedrock-runtime``; registra las llamadas recibidas.

    ``demora_s`` simula un Bedrock lento adelantando el reloj falso (no duerme).
    """

    def __init__(self, *, acciones_guardrail=None, respuesta_converse=None,
                 error_converse: Exception | None = None,
                 reloj: "_RelojFalso | None" = None, demora_s: float = 0.0):
        # Una acción por llamada a apply_guardrail, en orden (INPUT, OUTPUT).
        self.acciones_guardrail = list(acciones_guardrail or ["NONE", "NONE"])
        self.respuesta_converse = respuesta_converse
        self.error_converse = error_converse
        self.reloj = reloj
        self.demora_s = demora_s
        self.llamadas: list[tuple[str, dict]] = []

    @property
    def operaciones(self) -> list[str]:
        return [op for op, _ in self.llamadas]

    def _demorar(self) -> None:
        if self.reloj is not None and self.demora_s:
            self.reloj.t += self.demora_s

    def apply_guardrail(self, **kwargs) -> dict:
        self.llamadas.append(("apply_guardrail", kwargs))
        self._demorar()
        accion = self.acciones_guardrail.pop(0) if self.acciones_guardrail else "NONE"
        return {"action": accion, "outputs": [], "assessments": []}

    def converse(self, **kwargs) -> dict:
        self.llamadas.append(("converse", kwargs))
        self._demorar()
        if self.error_converse is not None:
            raise self.error_converse
        return self.respuesta_converse


class _ErrorBoto3Falso(Exception):
    """Simula un ClientError de boto3 cuyo mensaje podría ecoar la petición."""


def _respuesta_texto(texto: str = "Texto de orientacion referencial.",
                     stop_reason: str = "end_turn") -> dict:
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": texto}]}},
        "stopReason": stop_reason,
        "usage": {"inputTokens": 120, "outputTokens": 40, "totalTokens": 160},
    }


def _respuesta_tooluse(datos: dict, stop_reason: str = "tool_use") -> dict:
    return {
        "output": {"message": {"role": "assistant", "content": [
            {"toolUse": {"toolUseId": "tu-1", "name": "responder", "input": datos}},
        ]}},
        "stopReason": stop_reason,
        "usage": {"inputTokens": 150, "outputTokens": 60, "totalTokens": 210},
    }


SCHEMA_SINTETICO = {
    "type": "object",
    "properties": {"explicacion": {"type": "string"}},
    "required": ["explicacion"],
    "additionalProperties": False,
}


# --- fixtures ---------------------------------------------------------------

@pytest.fixture(autouse=True)
def reloj(monkeypatch) -> _RelojFalso:
    """Neutraliza la espera del throttle en TODOS los tests del módulo."""
    falso = _RelojFalso()
    monkeypatch.setattr(prov, "time", falso)
    monkeypatch.setattr(BedrockProvider, "_ultima_llamada", 0.0)
    return falso


@pytest.fixture(autouse=True)
def entorno_bedrock(monkeypatch) -> None:
    """Configuración mínima por entorno (solo nombres de variables, sin secretos)."""
    monkeypatch.setenv("E3_GUARDRAIL_ID", GUARDRAIL_SINTETICO)
    monkeypatch.setenv("E3_GUARDRAIL_VERSION", "1")
    monkeypatch.setenv("E3_BEDROCK_MODEL_ID", MODELO_SINTETICO)


# --- (a) salida de texto plano ---------------------------------------------

def test_texto_plano_sin_toolconfig():
    cliente = _ClienteFalso(respuesta_converse=_respuesta_texto())
    r = BedrockProvider(cliente=cliente).generar(PROMPT, system="Solo redacta.")

    assert r.texto == "Texto de orientacion referencial."
    assert r.datos is None
    assert r.proveedor == "bedrock"
    assert r.modelo == MODELO_SINTETICO
    assert r.uso == {"input_tokens": 120, "output_tokens": 40}

    # Dos barreras + una generación, en ese orden.
    assert cliente.operaciones == ["apply_guardrail", "converse", "apply_guardrail"]
    kwargs_converse = dict(cliente.llamadas[1][1])
    assert "toolConfig" not in kwargs_converse
    assert kwargs_converse["modelId"] == MODELO_SINTETICO
    assert kwargs_converse["system"] == [{"text": "Solo redacta."}]
    assert kwargs_converse["inferenceConfig"] == {"temperature": 0.2, "maxTokens": 1024}


# --- (b) salida estructurada via toolUse -----------------------------------

def test_salida_estructurada_via_tooluse():
    datos = {"explicacion": "El motor resolvio los hechos; esto solo los redacta."}
    cliente = _ClienteFalso(respuesta_converse=_respuesta_tooluse(datos))

    r = BedrockProvider(cliente=cliente).generar(PROMPT, json_schema=SCHEMA_SINTETICO)

    assert r.datos == datos
    assert json.loads(r.texto) == datos
    tool_config = cliente.llamadas[1][1]["toolConfig"]
    assert tool_config["tools"][0]["toolSpec"]["inputSchema"] == {"json": SCHEMA_SINTETICO}
    assert tool_config["toolChoice"] == {"tool": {"name": "responder"}}


def test_estructurada_sin_tooluse_falla_cerrado():
    """Si se pidió schema y el modelo devolvió prosa, se descarta la salida."""
    cliente = _ClienteFalso(respuesta_converse=_respuesta_texto())
    with pytest.raises(BedrockError):
        BedrockProvider(cliente=cliente).generar(PROMPT, json_schema={"type": "object"})


# --- (b2) postvalidación: schema y stopReason ------------------------------

def test_estructurada_fuera_de_schema_se_descarta():
    """Que el modelo use la herramienta no basta: el objeto debe cumplir el schema."""
    cliente = _ClienteFalso(
        respuesta_converse=_respuesta_tooluse({"explicacion": 42, "extra": "x"}))

    with pytest.raises(BedrockError) as exc:
        BedrockProvider(cliente=cliente).generar(PROMPT, json_schema=SCHEMA_SINTETICO)

    # La salida se descarta DESPUÉS de Converse y nunca se devuelve.
    assert cliente.operaciones == ["apply_guardrail", "converse"]
    # El mensaje lleva el validador incumplido, no el valor que falló.
    assert "42" not in str(exc.value)
    assert "validador=" in str(exc.value)


def test_estructurada_sin_campo_obligatorio_se_descarta():
    cliente = _ClienteFalso(respuesta_converse=_respuesta_tooluse({}))
    with pytest.raises(BedrockError):
        BedrockProvider(cliente=cliente).generar(PROMPT, json_schema=SCHEMA_SINTETICO)


def test_json_schema_invalido_falla_cerrado():
    datos = {"explicacion": "ok"}
    cliente = _ClienteFalso(respuesta_converse=_respuesta_tooluse(datos))
    with pytest.raises(BedrockError):
        BedrockProvider(cliente=cliente).generar(
            PROMPT, json_schema={"type": "object", "required": "no-es-lista"})


@pytest.mark.parametrize("respuesta, schema", [
    (_respuesta_texto("Prosa cortada a mitad de", stop_reason="max_tokens"), None),
    (_respuesta_tooluse({"explicacion": "ok"}, stop_reason="max_tokens"),
     SCHEMA_SINTETICO),
])
def test_salida_truncada_por_max_tokens_se_descarta(respuesta, schema):
    """Una generación cortada por maxTokens no se entrega como completa."""
    cliente = _ClienteFalso(respuesta_converse=respuesta)

    with pytest.raises(BedrockError) as exc:
        BedrockProvider(cliente=cliente).generar(PROMPT, json_schema=schema)

    assert "maxTokens" in str(exc.value)
    assert cliente.operaciones == ["apply_guardrail", "converse"]


# --- (c) Guardrail INPUT: no debe llegar a Converse ------------------------

def test_guardrail_input_bloquea_antes_de_converse():
    cliente = _ClienteFalso(acciones_guardrail=["GUARDRAIL_INTERVENED"],
                            respuesta_converse=_respuesta_texto())

    with pytest.raises(GuardrailIntervino) as exc:
        BedrockProvider(cliente=cliente).generar(PROMPT)

    assert str(exc.value) == "INPUT"
    assert cliente.operaciones == ["apply_guardrail"]
    assert "converse" not in cliente.operaciones
    # La llamada evaluó la entrada con la fuente correcta.
    kwargs = cliente.llamadas[0][1]
    assert kwargs["source"] == "INPUT"
    assert kwargs["guardrailIdentifier"] == GUARDRAIL_SINTETICO
    assert kwargs["guardrailVersion"] == "1"


# --- (d) Guardrail OUTPUT: la salida nunca se devuelve ---------------------

def test_guardrail_output_descarta_la_salida():
    cliente = _ClienteFalso(acciones_guardrail=["NONE", "GUARDRAIL_INTERVENED"],
                            respuesta_converse=_respuesta_texto("salida bloqueada"))

    with pytest.raises(GuardrailIntervino) as exc:
        BedrockProvider(cliente=cliente).generar(PROMPT)

    assert str(exc.value) == "OUTPUT"
    assert cliente.operaciones == ["apply_guardrail", "converse", "apply_guardrail"]
    assert cliente.llamadas[2][1]["source"] == "OUTPUT"


# --- (e) sin E3_GUARDRAIL_ID: no se llama a Bedrock en absoluto ------------

def test_sin_guardrail_no_llama_a_bedrock(monkeypatch):
    monkeypatch.delenv("E3_GUARDRAIL_ID", raising=False)
    cliente = _ClienteFalso(respuesta_converse=_respuesta_texto())
    p = BedrockProvider(cliente=cliente)

    with pytest.raises(GuardrailNoConfigurado):
        p.generar(PROMPT)

    assert cliente.llamadas == []


def test_get_provider_bedrock_sin_guardrail_falla_cerrado(monkeypatch):
    """La fábrica tampoco construye un cliente real sin segunda barrera."""
    monkeypatch.delenv("E3_GUARDRAIL_ID", raising=False)
    monkeypatch.setenv("E3_LLM_PROVIDER", "bedrock")
    with pytest.raises(GuardrailNoConfigurado):
        prov.get_provider()


# --- (f) errores de boto3 -> BedrockError capturable -----------------------

def test_error_de_boto3_se_convierte_en_bedrock_error():
    cliente = _ClienteFalso(
        respuesta_converse=None,
        error_converse=_ErrorBoto3Falso(f"ValidationException: {PROMPT}"),
    )
    with pytest.raises(BedrockError) as exc:
        BedrockProvider(cliente=cliente).generar(PROMPT)

    # El llamador puede capturar un solo tipo y degradar a TemplateProvider.
    assert isinstance(exc.value, BedrockError)
    assert "_ErrorBoto3Falso" in str(exc.value)


def test_respuesta_con_forma_inesperada_falla_cerrado():
    cliente = _ClienteFalso(respuesta_converse={"output": {}})
    with pytest.raises(BedrockError):
        BedrockProvider(cliente=cliente).generar(PROMPT)


def test_mensaje_de_error_no_ecoa_el_prompt():
    """Ni el mensaje del error ni el del Guardrail transportan contenido."""
    cliente = _ClienteFalso(
        respuesta_converse=None,
        error_converse=_ErrorBoto3Falso(f"ValidationException: {PROMPT}"),
    )
    with pytest.raises(BedrockError) as exc:
        BedrockProvider(cliente=cliente).generar(PROMPT)
    assert PROMPT not in str(exc.value)
    assert "BEN-001" not in str(exc.value)

    cliente2 = _ClienteFalso(acciones_guardrail=["GUARDRAIL_INTERVENED"])
    with pytest.raises(GuardrailIntervino) as exc2:
        BedrockProvider(cliente=cliente2).generar(PROMPT)
    assert str(exc2.value) == "INPUT"


# --- (g) throttle: cubre las tres llamadas y no duerme en los tests --------

def test_throttle_espacia_las_tres_llamadas(reloj):
    cliente = _ClienteFalso(respuesta_converse=_respuesta_texto())
    BedrockProvider(cliente=cliente).generar(PROMPT)

    # Tres llamadas a Bedrock (INPUT, Converse, OUTPUT) => tres esperas.
    assert len(reloj.esperas) == 3
    assert all(e == pytest.approx(prov.ESPERA_MINIMA_S) for e in reloj.esperas)


def test_throttle_no_espera_si_ya_paso_el_intervalo(reloj):
    # La fixture deja ``_ultima_llamada`` en 0.0; adelantar el reloj falso
    # equivale a que la última llamada fue hace mucho rato.
    reloj.t = 1000.0
    cliente = _ClienteFalso(respuesta_converse=_respuesta_texto())

    BedrockProvider(cliente=cliente).generar(PROMPT)

    # La primera llamada no espera; las dos siguientes sí (mismo instante falso).
    assert reloj.esperas == [pytest.approx(prov.ESPERA_MINIMA_S)] * 2


def test_la_suite_no_duerme_de_verdad():
    cliente = _ClienteFalso(respuesta_converse=_respuesta_texto())
    inicio = time.perf_counter()
    BedrockProvider(cliente=cliente).generar(PROMPT)
    assert time.perf_counter() - inicio < 0.5


# --- (g2) presupuesto de tiempo: se rinde antes del tope del gateway ------

def test_presupuesto_acotado_por_debajo_del_tope_del_gateway():
    """El peor caso de una generación cabe antes del tope de integración (30 s)."""
    assert prov.PRESUPUESTO_TOTAL_S < 30.0
    assert prov.COSTO_MAXIMO_LLAMADA_S == (
        prov.TIMEOUT_CONEXION_S + prov.TIMEOUT_LECTURA_S)
    # Una llamada solo arranca si cabe completa en lo que queda del presupuesto.
    assert prov.COSTO_MAXIMO_LLAMADA_S < prov.PRESUPUESTO_TOTAL_S


def test_bedrock_lento_agota_el_presupuesto_y_falla_cerrado(reloj):
    """Con Bedrock degradado, el provider se rinde en vez de colgar al gateway."""
    cliente = _ClienteFalso(respuesta_converse=_respuesta_texto(),
                            reloj=reloj, demora_s=prov.TIMEOUT_LECTURA_S)

    with pytest.raises(BedrockError) as exc:
        BedrockProvider(cliente=cliente).generar(PROMPT)

    assert "presupuesto" in str(exc.value)
    # Se gastó el presupuesto en las primeras llamadas; la última no arrancó.
    assert len(cliente.operaciones) < 3
    assert reloj.t < prov.PRESUPUESTO_TOTAL_S


# --- (h) boto3 perezoso y logs sin contenido ------------------------------

def test_el_modulo_no_importa_boto3_a_nivel_de_modulo():
    """La garantía se afirma sobre el provider, no sobre ``sys.modules`` global.

    Con boto3 instalado cualquier otra dependencia podría haberlo importado
    antes; lo que debe cumplirse es que ESTE módulo no lo importe al cargarse.
    """
    arbol = ast.parse(Path(prov.__file__).read_text(encoding="utf-8"))
    importados: list[str] = []
    for nodo in arbol.body:  # solo el nivel superior del módulo
        if isinstance(nodo, ast.Import):
            importados += [a.name.split(".")[0] for a in nodo.names]
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.append(nodo.module.split(".")[0])

    assert "boto3" not in importados
    assert "botocore" not in importados
    # El import perezoso sigue existiendo donde corresponde.
    fuente_crear = inspect.getsource(BedrockProvider._crear_cliente)
    assert "import boto3" in fuente_crear
    assert "from botocore.config import Config" in fuente_crear


def test_cliente_inyectado_no_construye_el_cliente_real(monkeypatch):
    """Con ``cliente=`` no se llega a ``_crear_cliente`` (ni se toca boto3)."""
    def _no_debe_llamarse(self):
        raise AssertionError("se intentó construir el cliente real de boto3")

    monkeypatch.setattr(BedrockProvider, "_crear_cliente", _no_debe_llamarse)
    cliente = _ClienteFalso(respuesta_converse=_respuesta_texto())
    assert BedrockProvider(cliente=cliente).generar(PROMPT).proveedor == "bedrock"


def test_logs_sin_prompt_ni_respuesta_y_con_request_id(caplog):
    with caplog.at_level(logging.DEBUG, logger="app.genai.provider"):
        cliente = _ClienteFalso(respuesta_converse=_respuesta_texto("respuesta modelo"))
        BedrockProvider(cliente=cliente).generar(
            PROMPT, request_id=REQUEST_ID_SINTETICO)
        cliente2 = _ClienteFalso(acciones_guardrail=["GUARDRAIL_INTERVENED"])
        with pytest.raises(GuardrailIntervino):
            BedrockProvider(cliente=cliente2).generar(
                PROMPT, request_id=REQUEST_ID_SINTETICO)

    texto_logs = "\n".join(r.getMessage() for r in caplog.records)
    assert PROMPT not in texto_logs
    assert "BEN-001" not in texto_logs
    assert "respuesta modelo" not in texto_logs
    assert GUARDRAIL_SINTETICO not in texto_logs
    # Sí se registran métricas agregadas, la fuente de la barrera y el
    # request_id (único campo que permite cruzar con la evidencia AWS).
    assert "latencia_ms=" in texto_logs
    assert "output_tokens=40" in texto_logs
    assert "fuente=INPUT" in texto_logs
    assert f"request_id={REQUEST_ID_SINTETICO}" in texto_logs
    # El request_id tampoco viaja al modelo.
    assert REQUEST_ID_SINTETICO not in json.dumps(cliente.llamadas[1][1])
