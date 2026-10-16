"""Camino Bedrock de ``POST /asistente`` en modo demo.

Módulo **puro** (no importa ``app.api``): recibe la pregunta ya filtrada de
datos personales por el router y las entradas del catálogo C4 que eligió el
``TemplateProvider`` de forma determinista. Quien lo llama es
``app.api.runtime.responder_asistente``, que degrada a plantilla ante
cualquier ``RedaccionError``.

Todo el mundo de la demo es ficticio (familias, jardines y beneficios). El
prompt C4 permite al modelo proponer acciones o programas ficticios plausibles
cuando nada del catálogo calza, para que ninguna pregunta del jurado termine en
un callejón sin salida. El modelo nunca decide elegibilidad.

Barreras, en orden (PRIVACIDAD_DEMO §"Barrera previa y GenAI"):

1. ``catalog_items`` por allowlist positiva: solo las cinco claves de
   ``AssistantRequestV1``, sin BEN-018/019/020 (DEC-062) ni entradas sin
   fuente oficial HTTPS.
2. Envelope interno ``AssistantRequestV1`` validado con jsonschema.
3. Render del prompt C4 + inspección de TODO el payload de egreso.
4. Guardrails INPUT -> Converse -> Guardrails OUTPUT -> schema (``BedrockProvider``,
   vía ``redaccion._invocar_modelo``).
5. Postvalidación del copy (``redaccion._texto_modelo``: sin promesas, cifras
   ni markup, con el aviso exacto) y citas SOLO a entradas enviadas.

Los logs llevan solo operación, estado, motivo, request_id y latencia; nunca la
pregunta, la respuesta ni el prompt.
"""
from __future__ import annotations

import json
import logging
import re
import time
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from app.genai import redaccion, template_provider
from app.genai.content_catalog import (
    PROMPT_ASISTENTE,
    ContenidoInvalido,
    PromptC4,
    cargar_catalogo_contenido,
)
from app.genai.provider import LLMProvider
from app.genai.redaccion import RedaccionError
from app.genai.template_provider import CatalogEntry

logger = logging.getLogger(__name__)

OPERACION_ASISTENTE = "CATALOG_ASSISTANT"

# Ejemplos sintéticos de programas locales: no viajan a Bedrock (DEC-062).
BENEFICIOS_DEMO_LOCALES = frozenset({"BEN-018", "BEN-019", "BEN-020"})

MAX_ITEMS = 8                  # AssistantRequestV1.catalog_items.maxItems
MAX_CITAS = 3
LARGO_MAX_ANSWER = 2000        # C3 AssistantEnvelope.answer (con aviso)
LARGO_MAX_ANSWER_MODELO = 800  # ~90 palabras con holgura
MAX_TOKENS_ASISTENTE = 700
LARGO_MAX_PREGUNTA = 500
LARGO_MAX_TITULO = 100
LARGO_MAX_DESCRIPCION = 500

# Códigos internos que nunca deben quedar en la prosa visible.
_RE_COD_BENEFICIO = re.compile(r"\bBEN-\d+\b")
_RE_COD_FAMILIA_JARDIN = re.compile(r"\b(?:FAM|JAR)-[A-Z0-9-]+\b")

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / ".kiro" / "specs" / "_shared" / "contracts" / "schemas"
    / "AssistantRequestV1.schema.json"
)

SYSTEM_ASISTENTE = (
    "Usted es Brujula, el asistente de una DEMO para tias de jardin infantil en "
    "Chile. Todo es ficticio: familias, jardines y beneficios. Responda siempre "
    "en espanol de Chile con 1 a 3 acciones concretas para hoy. Si nada del "
    "catalogo calza, puede proponer un programa o accion ficticia plausible. El "
    "motor determinista decide elegibilidad: nunca afirme que alguien califica. "
    "Responda unicamente con la herramienta indicada."
)

# El modelo solo escribe la prosa y elige qué entradas usó; ``intent``,
# ``citations``, aviso y ``provider`` los pone el servidor.
SCHEMA_ASISTENTE = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "benefit_ids"],
    "properties": {
        "answer": {"type": "string", "minLength": 1, "maxLength": LARGO_MAX_ANSWER_MODELO},
        "benefit_ids": {
            "type": "array",
            "maxItems": MAX_CITAS,
            "uniqueItems": True,
            "items": {"type": "string", "pattern": "^[A-Z0-9][A-Z0-9_-]*$", "maxLength": 80},
        },
    },
}


def catalog_items_asistente(
    entradas: list[CatalogEntry],
) -> tuple[list[dict], dict[str, CatalogEntry]]:
    """``catalog_items`` por allowlist positiva y su índice por ``benefit_id``.

    Excluye los programas demo locales y las entradas sin URL HTTPS o sin
    ``source_ids``; corta en ``MAX_ITEMS``.
    """
    items: list[dict] = []
    enviadas: dict[str, CatalogEntry] = {}
    for e in entradas:
        if len(items) >= MAX_ITEMS:
            break
        if (
            e.benefit_id in BENEFICIOS_DEMO_LOCALES
            or e.benefit_id in enviadas
            or not template_provider._es_https(e.source_url)
            or not e.source_ids
        ):
            continue
        titulo = template_provider._inert(e.title, LARGO_MAX_TITULO)
        descripcion = template_provider._inert(e.description, LARGO_MAX_DESCRIPCION)
        if not titulo or not descripcion:
            continue
        items.append({
            "benefit_id": e.benefit_id,
            "title": titulo,
            "description": descripcion,
            "official_url": e.source_url,
            "source_ids": list(e.source_ids),
        })
        enviadas[e.benefit_id] = e
    return items, enviadas


@lru_cache(maxsize=1)
def _validador_envelope() -> Draft202012Validator:
    """Validador de ``AssistantRequestV1`` (schema de solo lectura en .kiro)."""
    return Draft202012Validator(json.loads(_SCHEMA_PATH.read_text(encoding="utf-8")))


def construir_envelope_asistente(question: str, items: list[dict], prompt: PromptC4) -> dict:
    """Serializa y valida el envelope interno ``AssistantRequestV1``.

    Es un contrato INTERNO: el cliente público solo aporta la pregunta.
    """
    pregunta = (question or "").strip()
    if not pregunta or len(pregunta) > LARGO_MAX_PREGUNTA:
        raise RedaccionError(redaccion.MOTIVO_ENVELOPE_INVALIDO)
    meta = prompt.meta if isinstance(prompt.meta, dict) else {}
    version_salida = meta.get("output_schema_version")
    if not isinstance(version_salida, str):
        raise RedaccionError(redaccion.MOTIVO_PROMPT_C4_INVALIDO)
    envelope = {
        "operation": OPERACION_ASISTENTE,
        "question": pregunta,
        "catalog_items": items,
        "prompt_template_id": prompt.template_id,
        "prompt_version": prompt.version,
        "output_schema_version": version_salida,
    }
    try:
        validador = _validador_envelope()
    except (OSError, ValueError):
        raise RedaccionError(redaccion.MOTIVO_ENVELOPE_INVALIDO) from None
    # Los mensajes de jsonschema incluyen el valor que falló: no se propagan.
    if not validador.is_valid(envelope):
        raise RedaccionError(redaccion.MOTIVO_ENVELOPE_INVALIDO)
    return envelope


def sin_codigos_internos(
    texto: str,
    catalogo: dict[str, CatalogEntry],
    enviadas: dict[str, CatalogEntry],
) -> str:
    """La prosa visible nunca lleva códigos internos.

    Un ``BEN-NNN`` del catálogo se reemplaza por su título legible; uno
    desconocido, un ID de familia o jardín (``FAM-``/``JAR-``) o un
    ``source_id`` enviado al modelo hacen fallar cerrado (degrada a plantilla).
    """
    def _titulo(m: re.Match) -> str:
        entrada = catalogo.get(m.group(0))
        if entrada is None or not entrada.title:
            raise RedaccionError(redaccion.MOTIVO_POSTVALIDACION)
        return entrada.title

    limpio = _RE_COD_BENEFICIO.sub(_titulo, texto)
    fuentes = {s for e in enviadas.values() for s in (e.source_id, *e.source_ids) if s}
    if _RE_COD_FAMILIA_JARDIN.search(limpio) or any(
        re.search(rf"\b{re.escape(s)}\b", limpio) for s in fuentes
    ):
        raise RedaccionError(redaccion.MOTIVO_POSTVALIDACION)
    return limpio


def _citas(benefit_ids: object, enviadas: dict[str, CatalogEntry]) -> list[dict]:
    """Citas solo de entradas enviadas al modelo; IDs desconocidos se ignoran.

    En modo demo el modelo puede nombrar programas ficticios: esos no se citan.
    """
    citas: list[dict] = []
    for bid in benefit_ids if isinstance(benefit_ids, list) else []:
        e = enviadas.get(bid) if isinstance(bid, str) else None
        if e is None or not e.source_id:
            continue
        cita = {"source_id": e.source_id, "url": e.source_url}
        if cita not in citas:
            citas.append(cita)
    return citas[:MAX_CITAS]


def responder_asistente(
    question: str,
    entradas: list[CatalogEntry],
    *,
    request_id: str,
    provider: LLMProvider | None = None,
) -> dict:
    """``AssistantEnvelope`` redactado por el modelo, o ``RedaccionError``.

    Cualquier fallo, incluso uno no previsto, sale como ``RedaccionError`` con
    código fijo; el llamador degrada a plantilla.
    """
    inicio = time.monotonic()
    try:
        return _responder(question, entradas, request_id=request_id,
                          provider=provider, inicio=inicio)
    except RedaccionError as exc:
        _log_degradado(exc.motivo, request_id, inicio)
        raise
    except Exception:  # noqa: BLE001 — falla cerrada: nunca propagar detalles
        _log_degradado(redaccion.MOTIVO_ERROR_INESPERADO, request_id, inicio)
        raise RedaccionError(redaccion.MOTIVO_ERROR_INESPERADO) from None


def _responder(question, entradas, *, request_id, provider, inicio) -> dict:
    try:
        catalogo = cargar_catalogo_contenido()
    except ContenidoInvalido:
        raise RedaccionError(redaccion.MOTIVO_CATALOGO_C4) from None
    prompt = catalogo.prompts.get(PROMPT_ASISTENTE)
    if prompt is None:
        raise RedaccionError(redaccion.MOTIVO_PROMPT_C4_INVALIDO)

    items, enviadas = catalog_items_asistente(entradas)
    envelope = construir_envelope_asistente(question, items, prompt)
    prompt_renderizado = redaccion.renderizar_prompt(prompt, envelope)
    redaccion._exigir_payload_limpio(prompt_renderizado, None)

    datos = redaccion._invocar_modelo(
        prompt_renderizado, prompt,
        provider=provider, json_schema=SCHEMA_ASISTENTE,
        max_tokens=MAX_TOKENS_ASISTENTE, request_id=request_id,
        system=SYSTEM_ASISTENTE,
    )
    texto = datos.get("answer")
    if not isinstance(texto, str):
        raise RedaccionError(redaccion.MOTIVO_POSTVALIDACION)
    texto = sin_codigos_internos(texto, catalogo.entradas, enviadas)
    answer = redaccion._texto_modelo(texto, LARGO_MAX_ANSWER)
    citas = _citas(datos.get("benefit_ids"), enviadas)

    envelope_c3 = template_provider._envelope_asistente(
        request_id, "CATALOG_INFO", answer, citas, []
    )
    envelope_c3["provider"] = redaccion.PROVIDER_BEDROCK
    redaccion._log_ok(OPERACION_ASISTENTE, request_id, inicio)
    return envelope_c3


def _log_degradado(motivo: str, request_id: str, inicio: float) -> None:
    # Solo campos sanitizados: nunca pregunta, respuesta ni prompt.
    logger.warning(
        "genai_asistente: operacion=%s estado=DEGRADADO motivo=%s request_id=%s "
        "latencia_ms=%d",
        OPERACION_ASISTENTE, motivo, request_id or "-",
        int((time.monotonic() - inicio) * 1000),
    )
