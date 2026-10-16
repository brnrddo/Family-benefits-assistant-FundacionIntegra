"""Proveedor de texto determinista SIN AWS (FEAT-002).

``TemplateProvider`` es el **plan B** permanente (spec §4, API-008): produce
guion, mensaje y respuesta de asistente usando solo plantillas y campos ya
autorizados, sin red, sin boto3 y sin inventar hechos. Es también el fallback
cuando Bedrock, Guardrails o la postvalidación fallan de forma recuperable.

Garantías de seguridad (API-008/API-009, PRIVACIDAD_DEMO):

- Produce únicamente los campos cerrados de C3 (``ScriptContent``,
  ``MessageContent`` con ``PrintableCard`` CARD_V1, ``AssistantEnvelope``).
- El texto habla SOLO de los ``benefit_ids`` pedidos, en el orden pedido, con
  su nombre y descripción del catálogo C4; nunca sustituye un beneficio por
  otro. Un ID sin respaldo es un ``TemplateError`` (el servidor responde 422).
- Guion y mensaje reciben el estado de acceso de cada ID (DEC-060): los
  ofrecibles van en el marco del Rol 4 y los de seguimiento con la frase por
  estado, fuera de ese marco; ASIGNADO o un estado ausente es ``TemplateError``.
- ``PrintableCard`` transporta SOLO strings inertes y ``SourceCitation``
  tipadas; nunca HTML/CSS/handlers/atributos ni URLs libres. Todo texto se
  neutraliza (markup se vuelve texto plano) y se recorta a los límites C3.
- Cada cita proviene del catálogo C4 autorizado (URL HTTPS); un beneficio sin
  cita no lleva sección en la tarjeta y nunca se le inventa una URL (PREG-045).
- ``provider = 'PLANTILLA'`` y ``disclaimer`` exacto con tildes.
- ``/asistente``: una consulta de elegibilidad individual se detecta
  determinísticamente y devuelve ``REQUIRES_DETERMINISTIC_EVALUATION`` sin
  invocar ningún proveedor LLM.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

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
_MAX_CITATIONS = 8
_MAX_ASSISTANT_MATCHES = 3

# Placeholders literales de las plantillas de respaldo del Rol 4
# (content/prompts/*.md). Se renderizan con ``str.replace`` sobre valores ya
# neutralizados; nunca con ``str.format``.
PH_TITULOS = "{{catalog_items[].title}}"
PH_INSTITUCION = "{{catalog_items[].institution}}"

# Estados de acceso del motor (``app.access.model.EstadoAcceso``) según cómo se
# nombran en el texto (instrucción 5 de content/prompts, DEC-060):
# - ofrecibles: van en el marco "podrían servirle" del Rol 4;
# - seguimiento: se nombran con la frase por estado, fuera de ese marco;
# - ASIGNADO: la familia ya lo tiene; el servidor lo omite antes de llegar aquí.
ESTADOS_OFRECIBLES = frozenset({
    "ELEGIBLE_SIN_ASIGNACION", "PENDIENTE_ANTECEDENTES", "INDETERMINADO",
})
ESTADOS_SEGUIMIENTO = ("GESTION_EN_CURSO", "GESTION_RECHAZADA", "SIN_CUPO")
ESTADO_ASIGNADO = "ASIGNADO"

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


_RE_PRIMERA_FRASE = re.compile(r"^(.+?[.!?])(?=\s|$)")


def primera_frase(texto: str) -> str:
    """Primera oración de ``texto`` (hasta el primer '.', '!' o '?' seguido de espacio o fin).

    El guion usa solo la primera frase de cada descripción para quedar dentro de
    las 120 palabras de la instrucción 8 de ``content/prompts/guion.md`` (DEC-061).
    Sin un cierre de oración, devuelve el texto completo.
    """
    s = (texto or "").strip()
    m = _RE_PRIMERA_FRASE.match(s)
    return m.group(1) if m else s


def _con_aviso(cuerpo: str, limite: int) -> str:
    """Neutraliza ``cuerpo`` y agrega el aviso exacto (que lleva ';') al final."""
    texto = _inert(cuerpo, limite - len(DISCLAIMER) - 1)
    return f"{texto} {DISCLAIMER}".strip()


_RE_FIN_ORACION = re.compile(r"[.!?]")


def saludo_de(marco: str) -> str:
    """Saludo de una frase marco: las oraciones anteriores a ``PH_TITULOS``.

    Corta tras el último '.', '?' o '!' antes del placeholder ("Hola, ¿cómo
    está?" en el guion, "Hola. Le escribimos desde el jardín." en el WhatsApp).
    Devuelve ``""`` si no hay una oración completa antes del placeholder.
    """
    antes = (marco or "").split(PH_TITULOS, 1)[0]
    fines = list(_RE_FIN_ORACION.finditer(antes))
    return antes[: fines[-1].end()].strip() if fines else ""


# --- Política de copy (DEC-054) -----------------------------------------------

def _normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con espacios simples (para comparar texto)."""
    s = unicodedata.normalize("NFKD", texto)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return _RE_WS.sub(" ", s.lower()).strip()


# Promesas de elegibilidad o montos (PROD-008, "Prohibiciones" de los prompts
# C4 y PREG-047). Se evalúan sobre el texto normalizado (sin tildes).
_RE_PROMESA = re.compile(
    r"\btiene(?:n)? derecho\b"
    r"|\brecibira(?:n)?\b"
    r"|\b(?:le|les) corresponde(?:n)?\b"
    r"|\bcorresponderle(?:s)?\b"
    r"|\bgarantiza\w*"
    r"|\basegurad[oa]s?\b"
    r"|\bcalifica(?:n)?\b"
    r"|\b(?:es|son) elegibles?\b"
    r"|\$"
    r"|\b\d{4,}\b"
    r"|\b\d{1,3}(?:\.\d{3})+\b"
)

# Marcas que un texto plano de catálogo nunca debe traer.
_RE_NO_PLANO = re.compile(r"[<>{};]|https?://|javascript:|on\w+\s*=", re.IGNORECASE)


def contiene_promesa(texto: str) -> bool:
    """True si ``texto`` promete un resultado o menciona montos."""
    return bool(_RE_PROMESA.search(_normalizar(texto or "")))


def es_texto_plano(texto: str) -> bool:
    """True si ``texto`` no trae markup, llaves, ';', URLs ni handlers."""
    return isinstance(texto, str) and not _RE_NO_PLANO.search(texto)


# --- Tipos ----------------------------------------------------------------------

@dataclass(frozen=True)
class SourceCitation:
    """Cita tipada: solo ``source_id`` + URL HTTPS inventariada (C3)."""
    source_id: str
    url: str

    def to_dict(self) -> dict:
        return {"source_id": self.source_id, "url": self.url}


@dataclass(frozen=True)
class CatalogEntry:
    """Entrada del catálogo C4 autorizado para un beneficio.

    ``source_id``/``source_url`` valen ``""`` cuando el beneficio no tiene
    fuente oficial con URL (BEN-018/019/020, PREG-045).

    ``actions``/``source_ids`` son aditivos y traen lo que ``content_catalog``
    ya lee y valida del bundle C4: los exige el envelope interno
    ``FamilyGenerationRequestV1`` del camino Bedrock. El ``TemplateProvider`` no
    los usa, por eso llevan default vacío.
    """
    benefit_id: str
    title: str
    description: str
    institution: str
    where_to_go: str | None
    source_id: str
    source_url: str
    actions: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlantillasTexto:
    """Frases marco del TemplateProvider (sin el aviso final).

    ``guion``, ``whatsapp`` y ``asistente_catalogo`` contienen ``PH_TITULOS``;
    ``seccion_accion`` contiene ``PH_INSTITUCION``. ``frases_estado_guion`` y
    ``frases_estado_mensaje`` llevan una frase por cada estado de
    ``ESTADOS_SEGUIMIENTO``.
    """
    guion: str
    whatsapp: str
    tarjeta_titulo: str
    tarjeta_introduccion: str
    seccion_razon: str
    seccion_accion: str
    asistente_individual: str
    asistente_catalogo: str
    etiqueta_donde_ir: str
    frases_estado_guion: Mapping[str, str]
    frases_estado_mensaje: Mapping[str, str]


# Frases neutras por estado de seguimiento (sin "podría" ni "vale la pena").
_FRASES_ESTADO_NEUTRAS = MappingProxyType({
    "GESTION_EN_CURSO": "El trámite ya está en curso. Espere la respuesta de la institución.",
    "GESTION_RECHAZADA": "Consulte en la institución qué opciones hay.",
    "SIN_CUPO": "Consulte en la institución qué opciones hay.",
})

# Marcos fijos neutros: sin "podría", sin "vale la pena" y sin promesas.
PLANTILLAS_NEUTRAS = PlantillasTexto(
    guion=(
        "Hola, ¿cómo está? Revisamos algunos apoyos para conversar con su familia: "
        f"{PH_TITULOS}. Para confirmar, consulte en la institución de cada apoyo."
    ),
    whatsapp=(
        "Hola. Le escribimos desde el jardín. Revisamos algunos apoyos para "
        f"conversar con su familia: {PH_TITULOS}. Para confirmar, consulte en la "
        "institución de cada apoyo."
    ),
    tarjeta_titulo="Apoyos para consultar",
    tarjeta_introduccion=(
        "Estos apoyos son para conversar con su familia. Confirme cada uno en su institución."
    ),
    seccion_razon="Según la revisión del jardín, este apoyo es para conversar con su familia.",
    seccion_accion=f"Consulte en {PH_INSTITUCION}.",
    asistente_individual=(
        "Esta pregunta es sobre una familia en particular. Abra su ficha en la "
        "aplicación: ahí verá los apoyos revisados y qué antecedentes faltan. Hoy "
        "puede conversar con la familia y pedirle esos documentos."
    ),
    asistente_catalogo=(
        "Para avanzar hoy: revise la ficha de la familia, converse con ella sobre "
        "ingresos y documentos, y oriéntela a acercarse a la oficina municipal. "
        f"Apoyos del catálogo para conversar: {PH_TITULOS}."
    ),
    etiqueta_donde_ir="Dónde ir",
    frases_estado_guion=_FRASES_ESTADO_NEUTRAS,
    frases_estado_mensaje=_FRASES_ESTADO_NEUTRAS,
)

# Textos fijos cuando el catálogo C4 no está disponible (DEC-058): no nombran
# ningún beneficio.
GUION_SIN_CATALOGO = (
    "Hola, ¿cómo está? Por ahora no está disponible el texto de estos apoyos. "
    "Revise la ficha de la familia en la aplicación."
)
ASISTENTE_SIN_CATALOGO = (
    "Para avanzar hoy: revise la ficha de la familia, converse con ella sobre "
    "ingresos y documentos, y oriéntela a acercarse a la oficina municipal."
)
WARNING_SIN_CATALOGO = "CATALOGO_C4_NO_DISPONIBLE"


def _es_https(url: str) -> bool:
    return isinstance(url, str) and url.startswith("https://")


def _envelope_asistente(request_id: str, intent: str, answer: str,
                        citations: list[dict], warnings: list[str]) -> dict:
    return {
        "request_id": request_id,
        "intent": intent,
        "answer": answer,
        "citations": citations,
        "disclaimer": DISCLAIMER,
        "provider": PROVIDER,
        "warnings": warnings,
    }


def asistente_sin_catalogo(request_id: str, question: str) -> dict:
    """``AssistantEnvelope`` válido cuando el catálogo C4 no carga (DEC-058).

    La derivación individual no cambia; la respuesta general es un texto fijo,
    sin citas y con el warning de código fijo.
    """
    if es_pregunta_individual(question):
        answer = _con_aviso(PLANTILLAS_NEUTRAS.asistente_individual, _MAX_ANSWER)
        return _envelope_asistente(
            request_id, "REQUIRES_DETERMINISTIC_EVALUATION", answer, [], []
        )
    answer = _con_aviso(ASISTENTE_SIN_CATALOGO, _MAX_ANSWER)
    return _envelope_asistente(
        request_id, "CATALOG_INFO", answer, [], [WARNING_SIN_CATALOGO]
    )


# --- Recuperación determinista por nombre (DEC-059) ----------------------------

_RE_NO_ALNUM = re.compile(r"[^a-z0-9]+")
_RE_DEMO = re.compile(r"\(programa de demostracion\)")


def _clave_busqueda(texto: str) -> str:
    s = _RE_DEMO.sub(" ", _normalizar(texto))
    return _RE_NO_ALNUM.sub(" ", s).strip()


class TemplateProvider:
    """Genera texto seguro a partir del catálogo C4 autorizado (sin AWS)."""

    nombre = "plantilla"
    provider = PROVIDER

    def __init__(self, catalogo: dict[str, CatalogEntry],
                 plantillas: PlantillasTexto | None = None, *,
                 procedencia: tuple[str, str] | None = None):
        # Catálogo indexado por benefit_id (ya autorizado y validado por C4).
        self._catalogo = dict(catalogo)
        self._plantillas = plantillas or PLANTILLAS_NEUTRAS
        # (content_version, content_bundle_hash) del bundle del catálogo, para
        # ``meta`` (DEC-062); ``None`` si el catálogo no viene de ``content/``.
        self.procedencia = procedencia

    # -- catálogo -----------------------------------------------------------

    def conoce(self, benefit_id: str) -> bool:
        """True si ``benefit_id`` tiene respaldo en el catálogo C4."""
        return benefit_id in self._catalogo

    def tiene_cita(self, benefit_id: str) -> bool:
        """True si el beneficio tiene una fuente oficial HTTPS en el catálogo."""
        entrada = self._catalogo.get(benefit_id)
        return entrada is not None and self._cita(entrada) is not None

    def _entrada(self, benefit_id: str) -> CatalogEntry:
        entrada = self._catalogo.get(benefit_id)
        if entrada is None:
            raise TemplateError("benefit_id sin respaldo en catálogo C4")
        return entrada

    def _cita(self, entrada: CatalogEntry) -> SourceCitation | None:
        """Devuelve la cita del catálogo solo si la URL es HTTPS inventariada."""
        if not entrada.source_id or not _es_https(entrada.source_url):
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

    @staticmethod
    def _titulo(entrada: CatalogEntry) -> str:
        return _inert(entrada.title, _MAX_SECTION_HEADING) or entrada.benefit_id

    def _titulos(self, entradas: list[CatalogEntry]) -> str:
        return ", ".join(self._titulo(e) for e in entradas)

    # -- estado de acceso (DEC-060) ---------------------------------------

    @staticmethod
    def _validar_estados(benefit_ids: list[str], estados: Mapping[str, str]) -> None:
        """Falla cerrada: cada ID trae un estado ofrecible o de seguimiento.

        ASIGNADO, un estado desconocido o un ID sin estado son ``TemplateError``:
        el servidor ya omitió los ASIGNADO y rechazó los ajenos a la familia.
        """
        for bid in benefit_ids:
            estado = estados.get(bid)
            if estado not in ESTADOS_OFRECIBLES and estado not in ESTADOS_SEGUIMIENTO:
                raise TemplateError("benefit_id sin estado de acceso compatible")

    @staticmethod
    def _frase_estado(frases: Mapping[str, str], estado: str) -> str:
        frase = frases.get(estado)
        if not frase:
            raise TemplateError("estado de seguimiento sin frase")
        return frase

    def _marco(self, plantilla: str, ofrecibles: list[CatalogEntry]) -> str:
        """Marco del Rol 4 con SOLO los títulos ofrecibles; sin ellos, el saludo."""
        if ofrecibles:
            return plantilla.replace(PH_TITULOS, self._titulos(ofrecibles))
        return saludo_de(plantilla)

    # -- guion --------------------------------------------------------------

    def generar_guion(self, benefit_ids: list[str], *, estados: Mapping[str, str]) -> dict:
        """``ScriptContent``: benefit_ids (1–3) + guion ≤1200 chars y ≤120 palabras.

        Marco del Rol 4 con los títulos ofrecibles (o solo el saludo); luego,
        en el orden pedido, ``Título: primera frase`` para cada ofrecible y
        ``Título: frase por estado`` para cada seguimiento; al final, el aviso.
        """
        self._validar_estados(benefit_ids, estados)
        ids = self._normalizar_benefit_ids(benefit_ids)
        entradas = [self._entrada(bid) for bid in ids]
        ofrecibles = [e for e in entradas if estados[e.benefit_id] in ESTADOS_OFRECIBLES]
        marco = _inert(self._marco(self._plantillas.guion, ofrecibles), _MAX_SCRIPT)
        detalle: list[str] = []
        for e in entradas:
            estado = estados[e.benefit_id]
            if estado in ESTADOS_OFRECIBLES:
                # Solo la primera frase de la descripción: 120 palabras como
                # máximo (DEC-061). Mensaje y asistente conservan la completa.
                texto = _inert(primera_frase(e.description), _MAX_SCRIPT)
            else:
                texto = _inert(
                    self._frase_estado(self._plantillas.frases_estado_guion, estado),
                    _MAX_SCRIPT,
                )
            if texto:
                detalle.append(f"{self._titulo(e)}: {texto}")
        # El cuerpo dinámico se neutraliza; el disclaimer exacto (con ';') se
        # añade después para no alterar su literal obligatorio.
        guion = _con_aviso(" ".join([marco, *detalle]), _MAX_SCRIPT)
        return {"benefit_ids": ids, "script": guion}

    # -- mensaje ------------------------------------------------------------

    def _seccion(self, entrada: CatalogEntry, cita: SourceCitation, razon: str) -> dict:
        institucion = _inert(entrada.institution, _MAX_SECTION_ACTION) or "la institución"
        where = _inert(entrada.where_to_go, _MAX_WHERE_TO_GO) if entrada.where_to_go else ""
        return {
            "benefit_id": entrada.benefit_id,
            "heading": self._titulo(entrada),
            "reason": _inert(f"{razon} {entrada.description}", _MAX_SECTION_REASON),
            "action": _inert(
                self._plantillas.seccion_accion.replace(PH_INSTITUCION, institucion),
                _MAX_SECTION_ACTION,
            ),
            "where_to_go": where or None,
            "sources": [cita.to_dict()],
        }

    def generar_mensaje(self, benefit_ids: list[str], *, estados: Mapping[str, str]) -> dict:
        """``MessageContent``: preview WhatsApp + ``PrintableCard`` CARD_V1.

        El preview lleva el marco del Rol 4 con los títulos ofrecibles (o solo
        el saludo) y ``Título: frase por estado`` por cada seguimiento. La
        tarjeta lleva una sección solo por beneficio con cita HTTPS (C3 exige
        ≥1 fuente por sección); si ninguno la tiene, ``TemplateError``. La
        introducción del Rol 4 va solo si todas las secciones son ofrecibles.
        """
        self._validar_estados(benefit_ids, estados)
        ids = self._normalizar_benefit_ids(benefit_ids)
        entradas = [self._entrada(bid) for bid in ids]
        frases = self._plantillas.frases_estado_mensaje
        secciones: list[dict] = []
        todas_ofrecibles = True
        for e in entradas:
            cita = self._cita(e)
            if cita is None:
                continue
            estado = estados[e.benefit_id]
            if estado in ESTADOS_OFRECIBLES:
                razon = self._plantillas.seccion_razon
            else:
                razon = self._frase_estado(frases, estado)
                todas_ofrecibles = False
            secciones.append(self._seccion(e, cita, razon))
        if not secciones:
            raise TemplateError("ningún beneficio con cita HTTPS inventariada")

        ofrecibles = [e for e in entradas if estados[e.benefit_id] in ESTADOS_OFRECIBLES]
        seguimiento = [
            f"{self._titulo(e)}: {self._frase_estado(frases, estados[e.benefit_id])}"
            for e in entradas if estados[e.benefit_id] not in ESTADOS_OFRECIBLES
        ]
        preview = _con_aviso(
            " ".join([self._marco(self._plantillas.whatsapp, ofrecibles), *seguimiento]),
            _MAX_WHATSAPP,
        )
        introduccion = (
            self._plantillas.tarjeta_introduccion if todas_ofrecibles
            else saludo_de(self._plantillas.whatsapp)
        )
        card = {
            "format_version": "CARD_V1",
            "title": _inert(self._plantillas.tarjeta_titulo, _MAX_CARD_TITLE),
            "introduction": _inert(introduccion, _MAX_CARD_INTRO),
            "sections": secciones,
        }
        return {
            "benefit_ids": ids,
            "whatsapp_preview": preview,
            "printable_card": card,
        }

    # -- asistente ----------------------------------------------------------

    def _coincidencias(self, question: str) -> list[CatalogEntry]:
        """Beneficios cuyo nombre aparece en la pregunta (gana el más específico)."""
        pregunta = f" {_clave_busqueda(question or '')} "
        halladas: list[tuple[str, CatalogEntry]] = []
        for e in self._catalogo.values():
            clave = _clave_busqueda(e.title)
            if clave and f" {clave} " in pregunta:
                halladas.append((clave, e))
        especificas = [
            e for clave, e in halladas
            if not any(clave != otra and f" {clave} " in f" {otra} " for otra, _ in halladas)
        ]
        return especificas[:_MAX_ASSISTANT_MATCHES]

    def _por_situacion(self, question: str) -> list[CatalogEntry]:
        """Beneficios de la tabla cerrada ``SITUACIONES`` presentes en el catálogo."""
        texto = _normalizar(question or "")
        ids: list[str] = []
        for _nombre, patron, bids in SITUACIONES:
            if patron.search(texto):
                ids.extend(b for b in bids if b in self._catalogo and b not in ids)
        return [self._catalogo[b] for b in ids[:_MAX_SITUACION]]

    def entradas_relevantes(self, question: str) -> list[CatalogEntry]:
        """Entradas del catálogo ordenadas por relevancia para ``question``.

        Determinista: primero las coincidencias por nombre, luego la tabla
        ``SITUACIONES`` y al final el resto del catálogo en su orden, sin
        duplicados. Con prefijo "Contexto de la familia:" se mira primero el
        texto de la tía (situaciones y nombres) y después el contexto. No
        filtra: el filtro de egreso hacia el modelo lo aplica
        ``asistente_bedrock``.
        """
        contexto, texto_tia = separar_contexto(question)
        if contexto:
            fuentes = [*self._por_situacion(texto_tia), *self._coincidencias(texto_tia),
                       *self._por_situacion(contexto), *self._coincidencias(contexto)]
        else:
            fuentes = [*self._coincidencias(question), *self._por_situacion(question)]
        vistas: dict[str, CatalogEntry] = {}
        for e in [*fuentes, *self._catalogo.values()]:
            vistas.setdefault(e.benefit_id, e)
        return list(vistas.values())

    def _responder_situacion(self, request_id: str, question: str) -> dict | None:
        """Respuesta concreta y corta para una situación de la tabla cerrada.

        El texto solo nombra apoyos del catálogo C4 y dónde se consultan; no
        afirma elegibilidad (el motor decide). Sin coincidencias o si el texto
        trae una promesa, devuelve ``None`` y se usa la respuesta general.
        """
        return self._responder_entradas_situacion(request_id, self._por_situacion(question))

    def _responder_entradas_situacion(self, request_id: str,
                                      entradas: list[CatalogEntry]) -> dict | None:
        """Arma la respuesta de situación para ``entradas`` ya elegidas."""
        if not entradas:
            return None
        titulos = [self._titulo(e) for e in entradas]
        lista = titulos[0] if len(titulos) == 1 else (
            ", ".join(titulos[:-1]) + " y " + titulos[-1]
        )
        partes = [f"Por lo que cuenta, le recomiendo presentarles {lista}."]
        for e in entradas:
            parte = f"{self._titulo(e)}: {primera_frase(e.description)}"
            if e.where_to_go:
                parte += f" {self._plantillas.etiqueta_donde_ir}: {e.where_to_go}"
            partes.append(parte)
        partes.append("Revise la ficha de la familia para ver el detalle y el siguiente paso.")
        answer = _con_aviso(" ".join(partes), _MAX_ANSWER)
        if contiene_promesa(answer.replace(DISCLAIMER, "")):
            return None
        citas: list[dict] = []
        for e in entradas:
            cita = self._cita(e)
            if cita is not None and cita.to_dict() not in citas:
                citas.append(cita.to_dict())
        return _envelope_asistente(
            request_id, "CATALOG_INFO", answer, citas[:_MAX_CITATIONS], []
        )

    def responder_asistente(self, request_id: str, question: str) -> dict:
        """``AssistantEnvelope``: catálogo general o derivación determinista.

        Una pregunta de elegibilidad individual (¿califico?, ¿me corresponde?)
        se detecta sin LLM y devuelve ``REQUIRES_DETERMINISTIC_EVALUATION``.
        """
        if es_pregunta_individual(question):
            answer = _con_aviso(self._plantillas.asistente_individual, _MAX_ANSWER)
            return _envelope_asistente(
                request_id, "REQUIRES_DETERMINISTIC_EVALUATION", answer, [], []
            )

        contexto, texto_tia = separar_contexto(question)
        if contexto:
            # Chat de familia: el contexto lo arma el frontend solo con datos
            # permitidos (roles/edades, tramo RSH, títulos y estado), nunca
            # nombres ni IDs. Manda lo que cuenta la tía; el contexto (los
            # beneficios en la ficha) es el respaldo antes de la respuesta general.
            coincidencias: list[CatalogEntry] = []
            for parte in (texto_tia, contexto):
                situacion = self._responder_situacion(request_id, parte)
                if situacion is not None:
                    return situacion
                coincidencias = self._coincidencias(parte)
                if coincidencias:
                    break
        else:
            coincidencias = self._coincidencias(question)
            if not coincidencias:
                situacion = self._responder_situacion(request_id, question)
                if situacion is not None:
                    return situacion
        if coincidencias:
            partes: list[str] = []
            for e in coincidencias:
                parte = f"{self._titulo(e)}: {e.description}"
                if e.where_to_go:
                    parte += f" {self._plantillas.etiqueta_donde_ir}: {e.where_to_go}"
                partes.append(parte)
            answer = _con_aviso(" ".join(partes), _MAX_ANSWER)
            seleccion = coincidencias
        else:
            # Información general: los primeros beneficios con fuente oficial.
            seleccion = [e for e in self._catalogo.values() if self._cita(e)][:_MAX_CITATIONS]
            answer = _con_aviso(
                self._plantillas.asistente_catalogo.replace(
                    PH_TITULOS, self._titulos(seleccion)
                ),
                _MAX_ANSWER,
            )

        citas: list[dict] = []
        for e in seleccion:
            cita = self._cita(e)
            if cita is not None and cita.to_dict() not in citas:
                citas.append(cita.to_dict())
        return _envelope_asistente(
            request_id, "CATALOG_INFO", answer, citas[:_MAX_CITATIONS], []
        )


# Palabras que delatan una consulta de elegibilidad individual (determinista).
# Solo verbos de elegibilidad: "mi hijo" o "mi familia" describen una situación
# y se responden con la tabla de situaciones (no deciden nada).
_PATRONES_INDIVIDUAL = re.compile(
    r"\b("
    r"califico|calificar|califica|calificaria|me corresponde|le corresponde|"
    r"les corresponde|tengo derecho|tiene derecho|soy elegible|es elegible|"
    r"cumplo|cumple los requisitos"
    r")\b",
)


def es_pregunta_individual(question: str) -> bool:
    """Detecta determinísticamente una pregunta de elegibilidad individual.

    Con prefijo "Contexto de la familia:" solo se evalúa lo que cuenta la tía:
    el contexto (roles, tramo, beneficios y su estado) nunca la dispara.
    """
    if not isinstance(question, str):
        return False
    contexto, texto_tia = separar_contexto(question)
    texto = texto_tia if contexto else question
    return bool(_PATRONES_INDIVIDUAL.search(_normalizar(texto)))


# --- Chat de familia: prefijo de contexto ---------------------------------------

# El chat de la ficha antepone un contexto armado en el frontend con datos
# permitidos (roles/edades, tramo RSH, títulos de beneficios y su estado); nunca
# nombres ni IDs. Formato: "Contexto de la familia: <...>. Situación que cuenta
# la tía: <texto>".
PREFIJO_CONTEXTO = "Contexto de la familia:"
MARCA_SITUACION = "Situación que cuenta la tía:"
_PREFIJO_NORM = _normalizar(PREFIJO_CONTEXTO)
_MARCA_NORM = _normalizar(MARCA_SITUACION)


def separar_contexto(question: str) -> tuple[str, str]:
    """Separa ``(contexto, texto_tia)`` de una pregunta del chat de familia.

    Sin prefijo devuelve ``("", question)``. Con prefijo, ``texto_tia`` es lo
    que sigue a la marca de situación (``""`` si falta). La comparación tolera
    tildes y mayúsculas; los textos devueltos son normalizados.
    """
    if not isinstance(question, str):
        return "", ""
    norm = _normalizar(question)
    if not norm.startswith(_PREFIJO_NORM):
        return "", question
    resto = norm[len(_PREFIJO_NORM):]
    contexto, _, texto_tia = resto.partition(_MARCA_NORM)
    # Un contexto vacío sigue marcando la pregunta como del chat de familia.
    contexto = contexto.strip(" .") or _PREFIJO_NORM
    return contexto, texto_tia.strip()


# --- Situaciones (chat de la tía) ----------------------------------------------

# Tabla cerrada situación → beneficios del catálogo C4, en orden de la tabla.
# Se evalúa sobre texto normalizado (minúsculas, sin tildes). Solo se usan los
# IDs presentes en el catálogo cargado.
SITUACIONES: tuple[tuple[str, re.Pattern, tuple[str, ...]], ...] = (
    ("embarazo", re.compile(r"embaraz|gestante|prenatal|espera (una )?guagua"),
     ("BEN-003", "BEN-009")),
    ("sin_trabajo", re.compile(
        r"sin trabajo|sin pega|cesante|desemplead|perdio (el|su) trabajo"
        r"|lo despidieron|la despidieron"), ("BEN-016", "BEN-017")),
    ("discapacidad", re.compile(r"discapacidad|credencial|silla de ruedas"), ("BEN-006",)),
    ("terapia", re.compile(r"terapia|rehabilitacion"), ("BEN-019",)),
    ("adulto_mayor", re.compile(r"adulto mayor|abuel|tercera edad|mayor de 65"),
     ("BEN-004", "BEN-011")),
    ("agua", re.compile(r"\bagua\b|alcantarillado"), ("BEN-005",)),
    ("alimentos", re.compile(r"comida|aliment|canasta|hambre"), ("BEN-007", "BEN-018")),
    ("vivienda", re.compile(r"vivienda|arriendo|desalojo|incendio|allegad|emergencia"),
     ("BEN-020",)),
    ("recien_nacido", re.compile(r"recien nacid|\bnacio\b|guagua"), ("BEN-008", "BEN-012")),
)
_MAX_SITUACION = 4

# Datos personales que nunca deben viajar en una pregunta (RUT, teléfono, correo).
_RE_RUT = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK]\b")
_RE_TELEFONO = re.compile(r"(?:\+?56\s?)?9\s?\d{4}\s?\d{4}|\d{8,}")
_RE_CORREO = re.compile(r"[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}")


def contiene_dato_personal(texto: str) -> bool:
    """True si ``texto`` trae un RUT, un teléfono o un correo."""
    if not isinstance(texto, str):
        return False
    return bool(_RE_RUT.search(texto) or _RE_TELEFONO.search(texto)
                or _RE_CORREO.search(texto))
