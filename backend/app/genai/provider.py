"""Abstracción de proveedor LLM — contrato para el Rol 2 (spec §4).

Define una interfaz única (`LLMProvider`) para que el resto del backend no
dependa de un proveedor concreto. Trae dos implementaciones:

- ``StubProvider``   : determinista, SIN red ni AWS. Es el **plan B** que exige
  la spec §4 ("poder correr local con otra API si Bedrock falla") y permite
  que los tests y la demo funcionen sin credenciales.
- ``BedrockProvider`` : Amazon Bedrock (Claude vía Converse API) con Guardrails
  INPUT/OUTPUT como segunda barrera. `boto3` se importa de forma perezosa para
  no obligar a instalarlo en entornos sin AWS.

El LLM **nunca decide elegibilidad** (spec §2.4.1): redacta y explica hechos ya
resueltos por el motor determinista.

Selección por entorno:
    E3_LLM_PROVIDER      = "stub" (default) | "bedrock"
    E3_BEDROCK_MODEL_ID  = perfil de inferencia versionado (default: Claude
                           Haiku 4.5; los ids sin prefijo de región no son
                           invocables bajo demanda)
    E3_BEDROCK_REGION    = "us-east-1" (Bedrock no está en región Chile)
    E3_GUARDRAIL_ID      = OBLIGATORIO para Bedrock: sin Guardrail no se llama
    E3_GUARDRAIL_VERSION = versión del Guardrail (default "1")
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import jsonschema

logger = logging.getLogger(__name__)

# Perfil de inferencia versionado (cross-region) para llamadas bajo demanda.
# Los ids "bare" del catálogo (p. ej. anthropic.claude-haiku) no son invocables.
MODELO_DEFAULT = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# Única región permitida en el evento.
REGION_DEFAULT = "us-east-1"

# El evento recomienda < 1 llamada/seg a Bedrock. Margen sobre 1.0 s.
ESPERA_MINIMA_S = 1.1

# Nombre de la herramienta usada para forzar salida estructurada en Converse.
TOOL_SALIDA = "responder"

# Timeouts explícitos del cliente boto3 (el default de botocore no acota la
# conexión). Sin reintentos del SDK: el "reintento" real es degradar a
# ``TemplateProvider``, y un reintento interno rompería el presupuesto de abajo.
TIMEOUT_CONEXION_S = 3.0
TIMEOUT_LECTURA_S = 10.0

# Peor caso de UNA llamada a Bedrock con un solo intento.
COSTO_MAXIMO_LLAMADA_S = TIMEOUT_CONEXION_S + TIMEOUT_LECTURA_S  # 13 s

# Presupuesto de tiempo de UNA generación completa. Debe quedar por debajo del
# tope de integración de API Gateway HTTP API (30 s en el perfil Demo de
# docs/ARQUITECTURA_AWS.md): si el presupuesto se agota, el provider falla
# cerrado A TIEMPO para que el llamador alcance a responder con plantilla
# (HTTP 200 + warnings, API-008) en vez de que el gateway corte la integración.
#
#   peor caso sin guarda = 3 × ESPERA_MINIMA_S + 3 × COSTO_MAXIMO_LLAMADA_S
#                        = 3,3 s + 39 s = 42,3 s  (> 30 s)
#
# De ahí la guarda de ``_exigir_presupuesto``: no se INICIA una llamada que no
# quepa en lo que resta del presupuesto, así el total queda acotado a
# PRESUPUESTO_TOTAL_S.
PRESUPUESTO_TOTAL_S = 25.0

# Converse corta la generación cuando se agotan los maxTokens: la salida queda
# truncada (prosa a medias o toolUse sin campos obligatorios) y se descarta.
STOP_REASON_TRUNCADA = "max_tokens"


@dataclass
class LLMResponse:
    """Respuesta normalizada del proveedor, agnóstica del backend concreto."""
    texto: str                              # texto plano (si se pidió prosa)
    datos: dict | None = None               # JSON estructurado (si se pidió schema)
    modelo: str | None = None               # id del modelo que respondió
    uso: dict = field(default_factory=dict)  # tokens, etc. (para KPIs/costos)
    proveedor: str = "stub"


class LLMProvider(ABC):
    """Interfaz mínima que el Rol 2 consume y puede intercambiar.

    `generar` recibe un prompt ya armado (texto) y, opcionalmente, un
    `json_schema` para forzar salida estructurada (Bedrock Structured Outputs /
    Tool Use). `temperatura` baja por defecto (spec §9.1: 0.2–0.4).

    `request_id` es opcional y solo se usa para CORRELACIONAR logs con la
    petición C3 que los originó (campo permitido por PRIVACIDAD_DEMO §"Logs y
    evidencia"); nunca viaja al modelo.

    `texto_guardrail_input` es opcional: si viene, el Guardrail INPUT evalúa
    SOLO ese texto (la entrada no confiable: pregunta del usuario o datos del
    envelope) en vez del prompt completo. Las instrucciones del servidor son
    confiables y, evaluadas como entrada, disparaban PROMPT_ATTACK/MISCONDUCT.
    Sin él se conserva el comportamiento previo (INPUT sobre ``prompt``).
    """

    nombre = "abstract"

    @abstractmethod
    def generar(self, prompt: str, *, system: str | None = None,
                json_schema: dict | None = None, temperatura: float = 0.2,
                max_tokens: int = 1024,
                request_id: str | None = None,
                texto_guardrail_input: str | None = None) -> LLMResponse:
        ...


class StubProvider(LLMProvider):
    """Proveedor local determinista (sin red). Para tests y plan B.

    No "inventa": si se pide un `json_schema`, devuelve un objeto con las claves
    del schema vacías/placeholder, de modo que el flujo end-to-end funcione y
    sea obvio que la respuesta vino del stub (campo `proveedor="stub"`).
    """

    nombre = "stub"

    def generar(self, prompt: str, *, system=None, json_schema=None,
                temperatura: float = 0.2, max_tokens: int = 1024,
                request_id: str | None = None,
                texto_guardrail_input: str | None = None) -> LLMResponse:
        if json_schema is not None:
            esqueleto = _esqueleto_desde_schema(json_schema)
            return LLMResponse(
                texto=json.dumps(esqueleto, ensure_ascii=False),
                datos=esqueleto, modelo="stub-0", proveedor="stub",
                uso={"input_tokens": 0, "output_tokens": 0},
            )
        # Prosa: respuesta neutra y trazable (no se usa en decisiones).
        return LLMResponse(
            texto="[stub] respuesta de ejemplo (sin modelo real).",
            datos=None, modelo="stub-0", proveedor="stub",
            uso={"input_tokens": 0, "output_tokens": 0},
        )


class BedrockError(Exception):
    """Fallo del proveedor Bedrock. El llamador debe degradar a ``TemplateProvider``.

    Es la **única** familia de excepciones que escapa de ``BedrockProvider``
    (errores de boto3, respuestas con forma inesperada, Guardrail ausente o
    Guardrail que interviene). Así el llamador captura un solo tipo y cae a
    plantilla conservando HTTP 200 (API-008).

    Los mensajes NUNCA transportan el prompt, la salida del modelo ni valores de
    campos: solo la operación, la fuente del Guardrail y, a lo sumo, el nombre
    de la clase de la excepción de origen (PRIVACIDAD_DEMO §"Logs y evidencia").
    """


class GuardrailNoConfigurado(BedrockError):
    """Sin ``E3_GUARDRAIL_ID`` no hay segunda barrera: no se llama a Bedrock."""


class GuardrailIntervino(BedrockError):
    """El Guardrail bloqueó la entrada o la salida.

    El mensaje es solo la fuente (``"INPUT"`` o ``"OUTPUT"``), nunca el texto
    evaluado.
    """


class BedrockProvider(LLMProvider):
    """Amazon Bedrock (Claude · Converse API) con Guardrails INPUT/OUTPUT.

    Flujo fijo de una generación, máximo tres llamadas a Bedrock:

        ApplyGuardrail(INPUT) → Converse → ApplyGuardrail(OUTPUT)

    Decisiones de diseño:

    - **El filtro de privacidad NO vive aquí.** Lo que llega en el prompt ya
      pasó por ``llm_context.construir_llm_context`` (allowlist positiva sobre
      el schema cerrado ``LlmContextV1``). Guardrails es una SEGUNDA barrera,
      jamás un reemplazo del filtro (PRIVACIDAD_DEMO §"Barrera previa y GenAI").
    - **Guardrail desacoplado**: dos llamadas explícitas a ``ApplyGuardrail``,
      no el guardrail embebido en ``Converse``, para poder descartar la salida
      completa antes de devolverla.
    - **Falla cerrado**: sin ``E3_GUARDRAIL_ID`` no se llama a Bedrock; si el
      Guardrail interviene (entrada o salida), si boto3 falla o si la respuesta
      no tiene la forma esperada, se lanza ``BedrockError``.
    - **Postvalidación de la salida estructurada**: cuando se pide
      ``json_schema``, el objeto devuelto por el modelo se valida contra ese
      schema y una generación truncada por ``maxTokens`` se descarta
      (PRIVACIDAD_DEMO §"Barrera previa y GenAI", paso "schema/grounding y
      postvalidación").
    - **Throttle de clase sobre las TRES llamadas**, no solo sobre ``Converse``:
      el evento recomienda < 1 llamada/seg, así que todo acceso al cliente pasa
      por ``_esperar_turno`` (lock de clase + ≥ ``ESPERA_MINIMA_S``).
    - **Presupuesto de tiempo acotado** (``PRESUPUESTO_TOTAL_S``): el provider
      se rinde antes que el tope de integración del gateway para que el
      llamador alcance a degradar a plantilla.
    - **boto3 perezoso**: se importa dentro de ``_crear_cliente``, nunca a nivel
      de módulo; el backend y la suite corren sin boto3 instalado.
    - **Cliente inyectable** (``cliente=``): los tests pasan un doble de prueba
      en lugar de construir el cliente real (sin red, sin boto3). Es el único
      cambio de firma respecto del esqueleto y no altera a los llamadores.
    """

    nombre = "bedrock"

    # Throttle POR PROCESO: estado de clase, así que serializa las llamadas de
    # todas las instancias creadas en este intérprete. NO es un límite por
    # cuenta: en el perfil Demo cada contenedor Lambda tiene su propio
    # ``_ultima_llamada``, y varios contenedores concurrentes pueden superar en
    # conjunto 1 llamada/seg. Un límite de cuenta tendría que venir de las
    # cuotas de Bedrock, no de aquí.
    _lock = threading.Lock()
    _ultima_llamada = 0.0  # time.monotonic() de la última llamada a Bedrock

    def __init__(self, model_id: str | None = None, region: str | None = None,
                 *, cliente: object | None = None):
        self.model_id = model_id or os.environ.get("E3_BEDROCK_MODEL_ID", MODELO_DEFAULT)
        self.region = region or os.environ.get("E3_BEDROCK_REGION", REGION_DEFAULT)
        self.guardrail_id = os.environ.get("E3_GUARDRAIL_ID")
        self.guardrail_version = os.environ.get("E3_GUARDRAIL_VERSION", "1")
        self._client = cliente if cliente is not None else self._crear_cliente()

    # -- cliente ------------------------------------------------------------

    def _crear_cliente(self):
        """Crea el cliente ``bedrock-runtime`` importando boto3 perezosamente."""
        # Falla cerrado ANTES de importar boto3: sin Guardrail no hay Bedrock.
        self._exigir_guardrail()
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:  # entorno sin AWS: el plan B es el stub
            raise BedrockError(
                "boto3 no disponible en el entorno: usar E3_LLM_PROVIDER=stub"
            ) from exc
        try:
            return boto3.client(
                "bedrock-runtime", region_name=self.region,
                config=Config(
                    connect_timeout=TIMEOUT_CONEXION_S,
                    read_timeout=TIMEOUT_LECTURA_S,
                    # ``total_max_attempts`` cuenta el intento inicial (en un
                    # Config, ``max_attempts`` son reintentos ADICIONALES): 1 =
                    # un solo intento. Los reintentos del SDK multiplicarían el
                    # peor caso por llamada y romperían PRESUPUESTO_TOTAL_S; el
                    # reintento útil aquí es degradar a ``TemplateProvider``.
                    retries={"total_max_attempts": 1, "mode": "standard"},
                ),
            )
        except Exception as exc:
            raise BedrockError(
                f"no se pudo crear el cliente bedrock-runtime: {type(exc).__name__}"
            ) from exc

    def _exigir_guardrail(self) -> str:
        """Devuelve el id del Guardrail o falla cerrado si no está configurado."""
        if not self.guardrail_id:
            raise GuardrailNoConfigurado(
                "sin E3_GUARDRAIL_ID configurado: no se llama a Bedrock"
            )
        return self.guardrail_id

    # -- throttle y presupuesto ---------------------------------------------

    @classmethod
    def _esperar_turno(cls) -> None:
        """Serializa el acceso a Bedrock: ≥ ``ESPERA_MINIMA_S`` entre llamadas.

        Cubre las **tres** llamadas de una generación (los dos ApplyGuardrail y
        el Converse), no solo Converse: el límite recomendado del evento es por
        llamada a la API, no por generación.
        """
        with BedrockProvider._lock:
            espera = ESPERA_MINIMA_S - (time.monotonic() - BedrockProvider._ultima_llamada)
            if espera > 0:
                time.sleep(espera)
            BedrockProvider._ultima_llamada = time.monotonic()

    @staticmethod
    def _exigir_presupuesto(inicio: float, operacion: str) -> None:
        """Falla cerrado si la llamada por hacer no cabe en el presupuesto.

        Se evalúa DESPUÉS de la espera del throttle y ANTES de tocar el cliente:
        una llamada solo arranca si lo que queda de ``PRESUPUESTO_TOTAL_S``
        alcanza para su peor caso (``COSTO_MAXIMO_LLAMADA_S``). Así una
        generación nunca excede el presupuesto y el llamador conserva margen
        para responder con ``TemplateProvider`` antes del tope del gateway.
        """
        restante = PRESUPUESTO_TOTAL_S - (time.monotonic() - inicio)
        if restante < COSTO_MAXIMO_LLAMADA_S:
            logger.warning(
                "bedrock_presupuesto_agotado: operacion=%s restante_ms=%d",
                operacion, int(restante * 1000),
            )
            raise BedrockError(
                f"presupuesto de tiempo agotado antes de {operacion}: se degrada a plantilla"
            )

    def _preparar_llamada(self, inicio: float, operacion: str) -> None:
        """Throttle + presupuesto: todo acceso al cliente pasa por aquí."""
        self._esperar_turno()
        self._exigir_presupuesto(inicio, operacion)

    # -- guardrails ---------------------------------------------------------

    def _guardrail(self, texto: str, fuente: str, *, inicio: float,
                   request_id: str | None = None) -> None:
        """Aplica el Guardrail a ``texto``; ``fuente`` es ``"INPUT"``/``"OUTPUT"``.

        Lanza ``GuardrailIntervino(fuente)`` si el Guardrail bloquea: el mensaje
        lleva solo la fuente, nunca el contenido evaluado.
        """
        guardrail_id = self._exigir_guardrail()
        self._preparar_llamada(inicio, "apply_guardrail")
        try:
            resp = self._client.apply_guardrail(
                guardrailIdentifier=guardrail_id,
                guardrailVersion=self.guardrail_version,
                source=fuente,
                content=[{"text": {"text": texto}}],
            )
            accion = resp["action"]
        except Exception as exc:
            logger.warning(
                "bedrock_error: operacion=apply_guardrail fuente=%s "
                "request_id=%s excepcion=%s",
                fuente, request_id or "-", type(exc).__name__,
            )
            raise BedrockError(
                f"fallo apply_guardrail ({fuente}): {type(exc).__name__}"
            ) from exc
        if accion == "GUARDRAIL_INTERVENED":
            logger.warning(
                "bedrock_guardrail_intervino: fuente=%s request_id=%s",
                fuente, request_id or "-")
            raise GuardrailIntervino(fuente)

    # -- generación ---------------------------------------------------------

    def generar(self, prompt: str, *, system=None, json_schema=None,
                temperatura: float = 0.2, max_tokens: int = 1024,
                request_id: str | None = None,
                texto_guardrail_input: str | None = None) -> LLMResponse:
        """Genera prosa o JSON estructurado entre las dos barreras Guardrail.

        Con ``json_schema`` se fuerza salida estructurada vía ``toolConfig``
        (Tool Use), ``datos`` trae el objeto y se POSTVALIDA contra ese schema;
        sin schema, ``texto`` trae prosa.

        ``request_id`` solo correlaciona los logs con la petición C3; no viaja
        al modelo ni se incorpora al prompt.

        ``texto_guardrail_input``: si viene, el Guardrail INPUT evalúa solo ese
        texto (la entrada no confiable). Medido en la cuenta: el prompt completo
        (instrucciones del servidor + catálogo + reglas) dispara PROMPT_ATTACK y
        MISCONDUCT, mientras que la pregunta sola pasa. Las instrucciones son
        del servidor y ya pasaron la inspección integral de egreso (primera
        barrera); a Converse sigue viajando ``prompt`` completo. Sin el
        parámetro, INPUT evalúa ``prompt`` como antes. OUTPUT no cambia.
        """
        inicio = time.monotonic()
        # barrera 1: ANTES de Converse, sobre la entrada no confiable
        entrada = prompt if texto_guardrail_input is None else texto_guardrail_input
        self._guardrail(entrada, "INPUT", inicio=inicio, request_id=request_id)

        kwargs: dict = {
            "modelId": self.model_id,
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"temperature": temperatura, "maxTokens": max_tokens},
        }
        if system:
            kwargs["system"] = [{"text": system}]
        if json_schema is not None:
            kwargs["toolConfig"] = {
                "tools": [{"toolSpec": {
                    "name": TOOL_SALIDA,
                    "description": "Devuelve la respuesta estructurada",
                    "inputSchema": {"json": json_schema},
                }}],
                "toolChoice": {"tool": {"name": TOOL_SALIDA}},
            }

        self._preparar_llamada(inicio, "converse")
        try:
            resp = self._client.converse(**kwargs)
        except Exception as exc:
            logger.warning(
                "bedrock_error: operacion=converse request_id=%s excepcion=%s",
                request_id or "-", type(exc).__name__)
            raise BedrockError(f"fallo converse: {type(exc).__name__}") from exc

        # Postvalidación (schema + stopReason) ANTES de la segunda barrera.
        texto, datos, uso = _normalizar_converse(resp, json_schema)
        # barrera 2: ANTES de devolver. En el camino estructurado evalúa el JSON
        # serializado, no prosa; el smoke test fechado debe confirmar que el
        # Guardrail detecta igual sobre ese formato (hallazgo 8 de la revisión).
        self._guardrail(texto, "OUTPUT", inicio=inicio, request_id=request_id)

        # Log permitido: request_id, operación, estado, latencia, versión lógica
        # y métricas agregadas. Nunca prompt, respuesta ni valores de campos.
        logger.info(
            "bedrock_generar: estado=OK request_id=%s modelo=%s latencia_ms=%d "
            "input_tokens=%d output_tokens=%d",
            request_id or "-", self.model_id,
            int((time.monotonic() - inicio) * 1000),
            uso.get("input_tokens", 0), uso.get("output_tokens", 0),
        )
        return LLMResponse(texto=texto, datos=datos, modelo=self.model_id,
                           proveedor=self.nombre, uso=uso)


def _postvalidar_schema(datos: dict, json_schema: dict) -> None:
    """Valida la salida estructurada contra el schema que se pidió.

    Último paso de la secuencia de la política (Guardrails INPUT → Converse →
    schema/grounding → Guardrails OUTPUT → postvalidación): que el modelo haya
    usado la herramienta no garantiza que el objeto cumpla el contrato.

    El mensaje de ``jsonschema`` incluye el VALOR que falló (salida del modelo),
    así que no se propaga: solo viaja el nombre del validador incumplido
    (``required``, ``type``, ``enum``…).
    """
    try:
        jsonschema.validate(datos, json_schema)
    except jsonschema.ValidationError as exc:
        raise BedrockError(
            f"salida estructurada fuera del schema pedido (validador={exc.validator})"
        ) from exc
    except jsonschema.SchemaError as exc:
        raise BedrockError(
            f"json_schema invalido: no se puede postvalidar (validador={exc.validator})"
        ) from exc


def _normalizar_converse(resp: dict, json_schema: dict | None) -> tuple[str, dict | None, dict]:
    """Normaliza la respuesta de Converse a ``(texto, datos, uso)``.

    Falla cerrado con ``BedrockError`` si la respuesta no tiene la forma
    esperada, si la generación quedó truncada por ``maxTokens``, si se pidió
    salida estructurada y el modelo no usó la herramienta, si el objeto no
    cumple el schema pedido, o si la prosa viene vacía. El mensaje no incluye
    el contenido recibido.
    """
    try:
        bloques = resp["output"]["message"]["content"]
        uso = {
            "input_tokens": resp["usage"]["inputTokens"],
            "output_tokens": resp["usage"]["outputTokens"],
        }
        stop_reason = resp.get("stopReason")
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        raise BedrockError(
            f"respuesta Converse con forma inesperada: {type(exc).__name__}"
        ) from exc

    # Una salida truncada no es una salida: prosa a medias o toolUse sin campos
    # obligatorios. Se descarta completa (el llamador degrada a plantilla).
    if stop_reason == STOP_REASON_TRUNCADA:
        raise BedrockError("Converse truncó la salida por maxTokens: se descarta")

    if json_schema is not None:
        datos = next(
            (b["toolUse"].get("input") for b in bloques
             if isinstance(b, dict) and isinstance(b.get("toolUse"), dict)),
            None,
        )
        if not isinstance(datos, dict):
            raise BedrockError("se pidió salida estructurada y Converse no devolvió toolUse")
        _postvalidar_schema(datos, json_schema)
        return json.dumps(datos, ensure_ascii=False), datos, uso

    texto = "".join(
        b.get("text", "") for b in bloques if isinstance(b, dict)).strip()
    if not texto:
        raise BedrockError("Converse devolvió una respuesta sin texto")
    return texto, None, uso


def get_provider(nombre: str | None = None) -> LLMProvider:
    """Fábrica: devuelve el proveedor según entorno (default: stub).

    `E3_LLM_PROVIDER=bedrock` selecciona Bedrock; cualquier otro valor, o
    ausencia, devuelve el StubProvider seguro. Con Bedrock seleccionado pero sin
    ``E3_GUARDRAIL_ID`` (o sin boto3) la construcción falla cerrado con
    ``BedrockError``: no se llama a AWS sin la segunda barrera.

    **Para quien integre el fallback a plantilla**: el ``try/except
    BedrockError`` debe envolver también ESTA llamada (y cualquier
    ``BedrockProvider(...)`` directo), no solo ``generar()``. La construcción
    crea el cliente y por diseño puede lanzar ``GuardrailNoConfigurado`` o
    ``BedrockError``; un fallback escrito solo alrededor de ``generar()``
    convierte un ``E3_GUARDRAIL_ID`` ausente en un 500 en vez de degradar a
    ``TemplateProvider`` con HTTP 200 y ``warnings`` (API-008).
    """
    nombre = (nombre or os.environ.get("E3_LLM_PROVIDER", "stub")).strip().lower()
    if nombre == "bedrock":
        return BedrockProvider()
    return StubProvider()


def _esqueleto_desde_schema(schema: dict) -> dict:
    """Construye un objeto vacío a partir de un JSON Schema simple.

    Soporta el subconjunto que usaremos (object con properties de tipos
    básicos). Sirve para que el StubProvider devuelva algo con la forma pedida.
    """
    if schema.get("type") != "object":
        return {}
    out: dict = {}
    for clave, prop in (schema.get("properties") or {}).items():
        t = prop.get("type")
        if t == "array":
            out[clave] = []
        elif t == "object":
            out[clave] = _esqueleto_desde_schema(prop)
        elif t == "boolean":
            out[clave] = False
        elif t in ("number", "integer"):
            out[clave] = None
        else:
            out[clave] = None
    return out
