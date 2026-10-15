"""Proveedor de texto determinista SIN AWS (FEAT-002).

``TemplateProvider`` es el **plan B** permanente (spec §4, API-008): produce
guion, mensaje y respuesta de asistente usando solo plantillas y campos ya
autorizados, sin red, sin boto3 y sin inventar hechos. Es también el fallback
cuando Bedrock, Guardrails o la postvalidación fallan de forma recuperable.

Garantías de seguridad (API-008/API-009, PRIVACIDAD_DEMO):

- Produce únicamente los campos cerrados de C3 (``ScriptContent``,
  ``MessageContent`` con ``PrintableCard`` CARD_V1, ``AssistantEnvelope``).
- ``PrintableCard`` transporta SOLO strings inertes y ``SourceCitation``
  tipadas; nunca HTML/CSS/handlers/atributos ni URLs libres. Todo texto se
  neutraliza (markup se vuelve texto plano) y se recorta a los límites C3.
- Cada cita proviene del catálogo C4 autorizado; una cita sin respaldo se
  descarta.
- ``provider = 'PLANTILLA'`` y ``disclaimer`` exacto con tildes.
- ``/asistente``: una consulta de elegibilidad individual se detecta
  determinísticamente y devuelve ``REQUIRES_DETERMINISTIC_EVALUATION`` sin
  invocar ningún proveedor LLM.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PROVIDER = "PLANTILLA"

# Aviso exacto exigido por C3 (con tildes). No modificar.
DISCLAIMER = "Orientación referencial; no determina derechos. Confirmar en la institución."

# Límites de longitud de C3 (fuente: C3-api.openapi.yaml).
_MAX_SCRIPT = 1200
_MAX_WHATSAPP = 600
_MAX_CARD_TITLE = 100
_MAX_CARD_INTRO = 240
_MAX_SECTION_HEADING = 100
_MAX_SECTION_REASON = 240
_MAX_SECTION_ACTION = 240
_MAX_WHERE_TO_GO = 160
_MAX_ANSWER = 2000

# Patrones de markup/handler/URL que NUNCA deben transportarse como activos.
_RE_TAG = re.compile(r"<[^>]*>")                 # <script>, <b>, etc.
_RE_HANDLER = re.compile(r"on\w+\s*=", re.IGNORECASE)   # onclick=, onerror=
_RE_URL = re.compile(r"https?://\S+", re.IGNORECASE)    # URLs libres en texto
_RE_CSS = re.compile(r"(?:style\s*=|[{};])")            # css/estilos inline
_RE_WS = re.compile(r"\s+")


class TemplateError(Exception):
    """Entrada incompatible con la plantilla segura (p. ej. sin beneficios)."""


def _inert(texto: object, limite: int) -> str:
    """Neutraliza un string: quita markup/handlers/URLs/CSS y recorta.

    El resultado es texto plano inerte: aunque la entrada parezca ``<script>``
    o ``onerror=``, no sobrevive ningún tag, handler, estilo ni URL activa.
    """
    s = "" if texto is None else str(texto)
    s = _RE_TAG.sub(" ", s)
    s = _RE_HANDLER.sub(" ", s)
    s = _RE_URL.sub(" ", s)
    s = _RE_CSS.sub(" ", s)
    s = _RE_WS.sub(" ", s).strip()
    if len(s) > limite:
        s = s[:limite].rstrip()
    return s


@dataclass(frozen=True)
class SourceCitation:
    """Cita tipada: solo ``source_id`` + URL HTTPS inventariada (C3)."""
    source_id: str
    url: str

    def to_dict(self) -> dict:
        return {"source_id": self.source_id, "url": self.url}


@dataclass(frozen=True)
class CatalogEntry:
    """Entrada del catálogo C4 autorizado para un beneficio."""
    benefit_id: str
    title: str
    reason: str
    action: str
    where_to_go: str | None
    source_id: str
    source_url: str


def _es_https(url: str) -> bool:
    return isinstance(url, str) and url.startswith("https://")


class TemplateProvider:
    """Genera texto seguro a partir del catálogo C4 autorizado (sin AWS)."""

    nombre = "plantilla"
    provider = PROVIDER

    def __init__(self, catalogo: dict[str, CatalogEntry]):
        # Catálogo indexado por benefit_id (ya autorizado y validado por C4).
        self._catalogo = dict(catalogo)

    # -- catálogo -----------------------------------------------------------

    def _entrada(self, benefit_id: str) -> CatalogEntry:
        entrada = self._catalogo.get(benefit_id)
        if entrada is None:
            raise TemplateError(f"benefit_id sin respaldo en catálogo C4: {benefit_id}")
        return entrada

    def _cita(self, entrada: CatalogEntry) -> SourceCitation | None:
        """Devuelve la cita del catálogo solo si la URL es HTTPS inventariada."""
        if not _es_https(entrada.source_url):
            return None
        return SourceCitation(source_id=entrada.source_id, url=entrada.source_url)

    def _normalizar_benefit_ids(self, benefit_ids: list[str]) -> list[str]:
        if not benefit_ids:
            raise TemplateError("se requieren entre 1 y 3 benefit_ids")
        vistos: list[str] = []
        for bid in benefit_ids:
            self._entrada(bid)  # valida respaldo
            if bid not in vistos:
                vistos.append(bid)
        return vistos[:3]

    # -- guion --------------------------------------------------------------

    def generar_guion(self, benefit_ids: list[str]) -> dict:
        """``ScriptContent``: benefit_ids (1–3) + guion ≤1200 chars."""
        ids = self._normalizar_benefit_ids(benefit_ids)
        partes: list[str] = []
        for bid in ids:
            e = self._entrada(bid)
            partes.append(
                f"Sobre {e.title}: {e.reason} Vale la pena consultar: {e.action}"
            )
        # El cuerpo dinámico se neutraliza; el disclaimer exacto (con ';') se
        # añade después para no alterar su literal obligatorio.
        cuerpo = _inert(" ".join(partes), _MAX_SCRIPT - len(DISCLAIMER) - 1)
        guion = f"{cuerpo} {DISCLAIMER}".strip()
        return {"benefit_ids": ids, "script": guion}

    # -- mensaje ------------------------------------------------------------

    def _seccion(self, benefit_id: str) -> dict:
        e = self._entrada(benefit_id)
        cita = self._cita(e)
        sources = [cita.to_dict()] if cita else []
        if not sources:
            raise TemplateError(f"beneficio sin cita HTTPS inventariada: {benefit_id}")
        where = _inert(e.where_to_go, _MAX_WHERE_TO_GO) if e.where_to_go else None
        return {
            "benefit_id": benefit_id,
            "heading": _inert(e.title, _MAX_SECTION_HEADING) or benefit_id,
            "reason": _inert(e.reason, _MAX_SECTION_REASON) or "Puede corresponderle.",
            "action": _inert(e.action, _MAX_SECTION_ACTION) or "Consulte en la institución.",
            "where_to_go": where,
            "sources": sources,
        }

    def generar_mensaje(self, benefit_ids: list[str]) -> dict:
        """``MessageContent``: preview WhatsApp + ``PrintableCard`` CARD_V1."""
        ids = self._normalizar_benefit_ids(benefit_ids)
        secciones = [self._seccion(bid) for bid in ids]

        titulos = ", ".join(s["heading"] for s in secciones)
        preview_cuerpo = _inert(
            f"Hola. Podrían corresponderle estos apoyos: {titulos}.",
            _MAX_WHATSAPP - len(DISCLAIMER) - 1,
        )
        preview = f"{preview_cuerpo} {DISCLAIMER}".strip()
        card = {
            "format_version": "CARD_V1",
            "title": _inert("Apoyos que vale la pena consultar", _MAX_CARD_TITLE),
            "introduction": _inert(
                "Esta tarjeta resume orientaciones. Confirme en la institución.",
                _MAX_CARD_INTRO,
            ),
            "sections": secciones,
        }
        return {
            "benefit_ids": ids,
            "whatsapp_preview": preview,
            "printable_card": card,
        }

    # -- asistente ----------------------------------------------------------

    def responder_asistente(self, request_id: str, question: str) -> dict:
        """``AssistantEnvelope``: catálogo general o derivación determinista.

        Una pregunta de elegibilidad individual (¿califico?, ¿me corresponde?)
        se detecta sin LLM y devuelve ``REQUIRES_DETERMINISTIC_EVALUATION``.
        """
        if es_pregunta_individual(question):
            return {
                "request_id": request_id,
                "intent": "REQUIRES_DETERMINISTIC_EVALUATION",
                "answer": _inert(
                    "Para saber si a usted le corresponde un beneficio, use la "
                    "evaluación con los datos de su ficha. Esta respuesta no decide "
                    "su caso.",
                    _MAX_ANSWER,
                ),
                "citations": [],
                "disclaimer": DISCLAIMER,
                "provider": PROVIDER,
                "warnings": [],
            }

        # Información general del catálogo (sin decidir elegibilidad individual).
        citas: list[dict] = []
        for entrada in self._catalogo.values():
            cita = self._cita(entrada)
            if cita:
                citas.append(cita.to_dict())
            if len(citas) >= 8:
                break
        return {
            "request_id": request_id,
            "intent": "CATALOG_INFO",
            "answer": _inert(
                "Le comparto información general del catálogo de beneficios. "
                "Revise los requisitos y consulte en la institución indicada.",
                _MAX_ANSWER,
            ),
            "citations": citas,
            "disclaimer": DISCLAIMER,
            "provider": PROVIDER,
            "warnings": [],
        }


# Palabras que delatan una consulta de elegibilidad individual (determinista).
_PATRONES_INDIVIDUAL = re.compile(
    r"\b("
    r"califico|calificar|me corresponde|me toca|tengo derecho|puedo postular|"
    r"puedo recibir|puedo acceder|mi familia|mi hijo|mi hija|mi caso|"
    r"soy elegible|me dan|me darian|me darían|cumplo"
    r")\b",
    re.IGNORECASE,
)


def es_pregunta_individual(question: str) -> bool:
    """Detecta determinísticamente una pregunta de elegibilidad individual."""
    if not isinstance(question, str):
        return False
    return bool(_PATRONES_INDIVIDUAL.search(question))


def catalogo_desde_benefits(benefits_c4: list[dict], i18n: dict | None = None) -> dict[str, CatalogEntry]:
    """Construye el índice de catálogo desde el archivo BENEFITS de C4.

    Reutilizable por FEAT-003 para alimentar al ``TemplateProvider`` sin
    hardcodear copy. ``i18n`` opcional resuelve ``title_key`` a texto visible.
    """
    i18n = i18n or {}
    catalogo: dict[str, CatalogEntry] = {}
    for b in benefits_c4:
        bid = b["benefit_id"]
        title = i18n.get(b.get("title_key", ""), b.get("title_key", bid))
        catalogo[bid] = CatalogEntry(
            benefit_id=bid,
            title=title,
            reason=b.get("reason", "Según su ficha, podría corresponderle."),
            action=b.get("action", "Consulte en la institución para confirmar."),
            where_to_go=b.get("where_to_go"),
            source_id=b.get("source_id", "SRC-OFICIAL"),
            source_url=b.get("source_url", ""),
        )
    return catalogo
