"""Abstracción de proveedor LLM — contrato para el Rol 2 (spec §4).

Define una interfaz única (`LLMProvider`) para que el resto del backend no
dependa de un proveedor concreto. Trae dos implementaciones:

- ``StubProvider``   : determinista, SIN red ni AWS. Es el **plan B** que exige
  la spec §4 ("poder correr local con otra API si Bedrock falla") y permite
  que los tests y la demo funcionen sin credenciales.
- ``BedrockProvider`` : esqueleto para Amazon Bedrock (Claude vía Converse API).
  El Rol 2 rellena la llamada real; `boto3` se importa de forma perezosa para
  no obligar a instalarlo en entornos sin AWS.

Selección por entorno:
    E3_LLM_PROVIDER = "stub" (default) | "bedrock"
    E3_BEDROCK_MODEL_ID = p. ej. un Claude Haiku (rápido/barato para la tía)
    E3_BEDROCK_REGION   = p. ej. "us-east-1" (Bedrock no está en región Chile)
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


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
    """

    nombre = "abstract"

    @abstractmethod
    def generar(self, prompt: str, *, system: str | None = None,
                json_schema: dict | None = None, temperatura: float = 0.2,
                max_tokens: int = 1024) -> LLMResponse:
        ...


class StubProvider(LLMProvider):
    """Proveedor local determinista (sin red). Para tests y plan B.

    No "inventa": si se pide un `json_schema`, devuelve un objeto con las claves
    del schema vacías/placeholder, de modo que el flujo end-to-end funcione y
    sea obvio que la respuesta vino del stub (campo `proveedor="stub"`).
    """

    nombre = "stub"

    def generar(self, prompt: str, *, system=None, json_schema=None,
                temperatura: float = 0.2, max_tokens: int = 1024) -> LLMResponse:
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


class BedrockProvider(LLMProvider):
    """Esqueleto para Amazon Bedrock (Claude · Converse API). LO RELLENA ROL 2.

    Pasos que debe implementar el Rol 2 (dejados como guía, no funcional aún):

      1. Cliente perezoso:
             import boto3
             self._client = boto3.client("bedrock-runtime", region_name=region)

      2. Llamada Converse (API unificada de Bedrock):
             resp = self._client.converse(
                 modelId=self.model_id,
                 messages=[{"role": "user", "content": [{"text": prompt}]}],
                 system=[{"text": system}] if system else [],
                 inferenceConfig={"temperature": temperatura,
                                  "maxTokens": max_tokens},
                 # Para salida estructurada: usar toolConfig con el json_schema
                 # (Tool Use) o la función de Structured Outputs de Bedrock.
             )

      3. Normalizar la respuesta a `LLMResponse` (texto / datos / uso).

      4. Manejar errores de red/credenciales y, si falla, degradar al
         StubProvider (plan B §4) para no romper la demo.

    Mientras no esté implementado, `generar` lanza NotImplementedError con una
    pista clara; el default del sistema sigue siendo el StubProvider.
    """

    nombre = "bedrock"

    def __init__(self, model_id: str | None = None, region: str | None = None):
        self.model_id = model_id or os.environ.get(
            "E3_BEDROCK_MODEL_ID", "anthropic.claude-haiku")  # Rol 2: fijar id exacto
        self.region = region or os.environ.get("E3_BEDROCK_REGION", "us-east-1")
        self._client = None  # Rol 2: inicializar boto3 aquí (perezoso)

    def generar(self, prompt: str, *, system=None, json_schema=None,
                temperatura: float = 0.2, max_tokens: int = 1024) -> LLMResponse:
        raise NotImplementedError(
            "BedrockProvider es un esqueleto para el Rol 2: implementar la "
            "llamada Converse con boto3 (ver docstring). Mientras tanto usar "
            "E3_LLM_PROVIDER=stub."
        )


def get_provider(nombre: str | None = None) -> LLMProvider:
    """Fábrica: devuelve el proveedor según entorno (default: stub).

    `E3_LLM_PROVIDER=bedrock` selecciona Bedrock (cuando Rol 2 lo implemente);
    cualquier otro valor, o ausencia, devuelve el StubProvider seguro.
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
