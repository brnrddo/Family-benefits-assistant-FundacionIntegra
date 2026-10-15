"""Catálogo de texto C4 desde ``content/`` (Rol 4): solo lectura y falla cerrada.

Lee el bundle de contenido del Rol 4 (``content/manifest.yaml`` 0.2.1, DEC-048)
y arma el catálogo del ``TemplateProvider``:

- BENEFITS (``content/beneficios.yaml``): descripción, institución, dónde ir y
  fuente oficial (``official_source_id`` + ``official_url`` HTTPS).
- I18N (``content/i18n/es.json``): nombre visible ``benefit.<id>.name`` (debe
  ser igual a ``simple_title``), aviso ``notice.referential`` (debe ser igual
  al aviso de C3) y la etiqueta ``card_v1.where_label``.
- PROMPT (``content/prompts/*.md``): versión de cada prompt, las frases marco
  de la sección ``## Plantilla de respaldo`` (escritas por el Rol 4 para el
  TemplateProvider; el guion y el WhatsApp deben abrir con un saludo) y, para
  guion y mensaje, la frase por estado de seguimiento de la instrucción 5 de
  ``## Instrucciones`` (DEC-060).

Validación cerrada, en orden y con códigos fijos (``ContenidoInvalido.codigo``):
schema C4 cerrado, rutas dentro de ``content/``, sha256 de cada archivo sobre
bytes LF (DEC-045), ``content_bundle_hash`` (SUP-041), presencia de clases y
forma de cada archivo usado. Nunca escribe archivos ni loguea; el mensaje del
error es solo el código (sin rutas ni valores).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from urllib.parse import urlparse

import yaml
from jsonschema import Draft202012Validator

from app.genai.template_provider import (DISCLAIMER, ESTADOS_SEGUIMIENTO,
                                         PH_INSTITUCION, PH_TITULOS,
                                         CatalogEntry, PlantillasTexto,
                                         contiene_promesa, es_texto_plano,
                                         saludo_de)

REPO_DIR = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = REPO_DIR / "content" / "manifest.yaml"
_C4_SCHEMA_PATH = (
    REPO_DIR / ".kiro" / "specs" / "_shared" / "contracts" / "C4-contenido-manifest.schema.json"
)

PROMPT_GUION = "PROMPT-GUION"
PROMPT_MENSAJE = "PROMPT-MENSAJE-FAMILIA"
PROMPT_ASISTENTE = "PROMPT-ASISTENTE-CATALOGO"
_PROMPTS_REQUERIDOS = (PROMPT_GUION, PROMPT_MENSAJE, PROMPT_ASISTENTE)

_RE_ID = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")
_RE_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_RE_PLACEHOLDER = re.compile(r"\{\{[^{}]*\}\}")
_RE_RESPALDO = re.compile(r"^## Plantilla de respaldo[ \t]*$", re.MULTILINE)
_RE_INSTRUCCIONES = re.compile(r"^## Instrucciones[ \t]*$", re.MULTILINE)
_RE_SIGUIENTE_SECCION = re.compile(r"^## ", re.MULTILINE)
# Instrucción 5 de los prompts: "- `access_state` ESTADO( o ESTADO)*: frase".
_RE_FRASE_ESTADO = re.compile(
    r"^\s*- `access_state` ([A-Z_]+(?: o [A-Z_]+)*): (.+?)\s*$", re.MULTILINE
)

_CLAVES_BENEFITS = frozenset({"content_version", "estado", "beneficios"})
_CLAVES_BENEFICIO = frozenset({
    "benefit_id", "simple_title", "description", "actions", "institution",
    "where_to_go", "official_source_id", "official_url", "source_ids",
})


class ContenidoInvalido(Exception):
    """El bundle de ``content/`` no pasa la validación cerrada."""

    def __init__(self, codigo: str):
        self.codigo = codigo
        super().__init__(codigo)


@dataclass(frozen=True)
class PromptC4:
    """Prompt del Rol 4 tal como vino de ``content/prompts/*.md``.

    ``meta`` es el front matter completo (ya validado solo en
    ``prompt_template_id`` y ``prompt_version``) y ``cuerpo`` es el Markdown
    posterior, SIN tocar. Quien lo use (``app.genai.redaccion``) valida lo que
    necesite al usarlo: así un prompt futuro sin ``variables`` degrada el camino
    Bedrock en vez de invalidar todo el bundle C4.
    """
    template_id: str
    version: str
    meta: dict
    cuerpo: str


@dataclass(frozen=True)
class CatalogoContenido:
    """Catálogo validado (orden de ``beneficios.yaml``)."""
    content_version: str
    content_bundle_hash: str
    entradas: dict[str, CatalogEntry]
    plantillas: PlantillasTexto
    prompt_versions: dict[str, str]
    # Aditivo: prompts completos por ``prompt_template_id`` (camino Bedrock).
    prompts: dict[str, PromptC4] = field(default_factory=dict)


def cargar_catalogo_contenido(manifest_path: str | Path | None = None) -> CatalogoContenido:
    """Carga y valida el catálogo C4 de ``content/`` (solo lectura).

    ``DEFAULT_MANIFEST`` se lee al llamar (no al definir la función) para que
    los tests puedan apuntarlo a una copia. Cualquier fallo, incluso uno no
    previsto, se reporta como ``ContenidoInvalido`` con código fijo.
    """
    path = Path(manifest_path) if manifest_path is not None else DEFAULT_MANIFEST
    try:
        return _cargar(path)
    except ContenidoInvalido:
        raise
    except Exception:  # noqa: BLE001 — falla cerrada: nunca propagar detalles
        raise ContenidoInvalido("C4_ERROR_INESPERADO") from None


# --- Pasos de validación ---------------------------------------------------------


def _cargar(manifest_path: Path) -> CatalogoContenido:
    manifest = _leer_manifest(manifest_path)
    _validar_schema(manifest)
    root = manifest_path.resolve().parent.parent
    archivos = _verificar_archivos(manifest, root)
    _verificar_bundle_hash(manifest)

    benefits_path, i18n_path, prompts = _clases(manifest, archivos)
    i18n = _leer_i18n(archivos[i18n_path])
    entradas = _leer_beneficios(archivos[benefits_path], manifest["content_version"], i18n)
    plantillas = _leer_plantillas(prompts, i18n["card_v1.where_label"])
    return CatalogoContenido(
        content_version=manifest["content_version"],
        content_bundle_hash=manifest["content_bundle_hash"],
        entradas=entradas,
        plantillas=plantillas,
        prompt_versions={pid: p.version for pid, p in prompts.items()},
        prompts=prompts,
    )


def _leer_manifest(path: Path) -> dict:
    try:
        doc = yaml.safe_load(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        raise ContenidoInvalido("C4_MANIFEST_ILEGIBLE") from None
    if not isinstance(doc, dict):
        raise ContenidoInvalido("C4_MANIFEST_ILEGIBLE")
    return doc


def _validar_schema(manifest: dict) -> None:
    try:
        schema = json.loads(_C4_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ContenidoInvalido("C4_SCHEMA_INVALIDO") from None
    if not Draft202012Validator(schema).is_valid(manifest):
        raise ContenidoInvalido("C4_SCHEMA_INVALIDO")


def _verificar_archivos(manifest: dict, root: Path) -> dict[str, bytes]:
    """Verifica TODO ``files[]``: ruta dentro de ``content/``, existencia y sha256."""
    content_dir = (root / "content").resolve()
    vistos: set[Path] = set()
    archivos: dict[str, bytes] = {}
    for entrada in manifest["files"]:
        rel = entrada["path"]
        destino = (root / rel).resolve()
        if destino in vistos or not destino.is_relative_to(content_dir):
            raise ContenidoInvalido("C4_RUTA_INVALIDA")
        vistos.add(destino)
        try:
            datos = destino.read_bytes()
        except OSError:
            raise ContenidoInvalido("C4_ARCHIVO_AUSENTE") from None
        datos = datos.replace(b"\r\n", b"\n")  # DEC-045: el hash es sobre bytes LF
        if hashlib.sha256(datos).hexdigest() != entrada["sha256"]:
            raise ContenidoInvalido("C4_SHA256_DISTINTO")
        archivos[rel] = datos
    return archivos


def _verificar_bundle_hash(manifest: dict) -> None:
    """SUP-041: SHA-256 de ``'<sha256>  <path>\\n'`` por archivo, ordenado por path."""
    lineas = "".join(
        f"{f['sha256']}  {f['path']}\n"
        for f in sorted(manifest["files"], key=lambda f: f["path"])
    )
    if hashlib.sha256(lineas.encode("utf-8")).hexdigest() != manifest["content_bundle_hash"]:
        raise ContenidoInvalido("C4_BUNDLE_HASH_DISTINTO")


def _decodificar(datos: bytes, codigo: str) -> str:
    try:
        return datos.decode("utf-8")
    except UnicodeDecodeError:
        raise ContenidoInvalido(codigo) from None


def _clases(manifest: dict, archivos: dict[str, bytes]) -> tuple[str, str, dict]:
    """Un BENEFITS, el I18N canónico y los tres PROMPT requeridos."""
    files = manifest["files"]
    benefits = [f["path"] for f in files if f["kind"] == "BENEFITS"]
    i18n = [f["path"] for f in files
            if f["kind"] == "I18N" and f["path"] == manifest["canonical_i18n"]]
    if len(benefits) != 1 or len(i18n) != 1:
        raise ContenidoInvalido("C4_CLASE_FALTANTE")

    prompts: dict[str, PromptC4] = {}
    for f in files:
        if f["kind"] != "PROMPT":
            continue
        texto = _decodificar(archivos[f["path"]], "C4_PROMPT_INVALIDO")
        meta, cuerpo = _front_matter(texto)
        pid = meta["prompt_template_id"]
        if pid in prompts:
            raise ContenidoInvalido("C4_PROMPT_INVALIDO")
        prompts[pid] = PromptC4(
            template_id=pid, version=meta["prompt_version"], meta=meta, cuerpo=cuerpo,
        )
    if any(pid not in prompts for pid in _PROMPTS_REQUERIDOS):
        raise ContenidoInvalido("C4_CLASE_FALTANTE")
    return benefits[0], i18n[0], prompts


# --- I18N -------------------------------------------------------------------------


def _leer_i18n(datos: bytes) -> dict[str, str]:
    try:
        i18n = json.loads(_decodificar(datos, "C4_I18N_INVALIDO"))
    except ValueError:
        raise ContenidoInvalido("C4_I18N_INVALIDO") from None
    if not isinstance(i18n, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in i18n.items()
    ):
        raise ContenidoInvalido("C4_I18N_INVALIDO")
    if i18n.get("notice.referential") != DISCLAIMER:
        raise ContenidoInvalido("C4_I18N_INVALIDO")
    etiqueta = i18n.get("card_v1.where_label")
    if not etiqueta or not es_texto_plano(etiqueta) or contiene_promesa(etiqueta):
        raise ContenidoInvalido("C4_I18N_INVALIDO")
    return i18n


# --- BENEFITS ---------------------------------------------------------------------


def _texto_beneficio(valor: object, minimo: int, maximo: int) -> str:
    if (not isinstance(valor, str) or not minimo <= len(valor) <= maximo
            or not es_texto_plano(valor) or contiene_promesa(valor)):
        raise ContenidoInvalido("C4_BENEFITS_INVALIDO")
    return valor


def _es_id(valor: object) -> bool:
    return isinstance(valor, str) and len(valor) <= 80 and bool(_RE_ID.match(valor))


def _es_url_oficial(valor: object) -> bool:
    if not isinstance(valor, str) or not valor.startswith("https://"):
        return False
    if any(ch.isspace() for ch in valor):
        return False
    return bool(urlparse(valor).netloc)


def _leer_beneficios(datos: bytes, content_version: str,
                     i18n: dict[str, str]) -> dict[str, CatalogEntry]:
    try:
        doc = yaml.safe_load(_decodificar(datos, "C4_BENEFITS_INVALIDO"))
    except yaml.YAMLError:
        raise ContenidoInvalido("C4_BENEFITS_INVALIDO") from None
    if not isinstance(doc, dict) or set(doc) != _CLAVES_BENEFITS:
        raise ContenidoInvalido("C4_BENEFITS_INVALIDO")
    if doc["content_version"] != content_version:
        raise ContenidoInvalido("C4_BENEFITS_INVALIDO")
    items = doc["beneficios"]
    if not isinstance(items, list) or not items:
        raise ContenidoInvalido("C4_BENEFITS_INVALIDO")

    entradas: dict[str, CatalogEntry] = {}
    for b in items:
        entrada = _leer_beneficio(b)
        if entrada.benefit_id in entradas:
            raise ContenidoInvalido("C4_BENEFITS_INVALIDO")
        if i18n.get(f"benefit.{entrada.benefit_id.lower()}.name") != entrada.title:
            raise ContenidoInvalido("C4_I18N_INVALIDO")
        entradas[entrada.benefit_id] = entrada
    return entradas


def _leer_beneficio(b: object) -> CatalogEntry:
    if not isinstance(b, dict) or set(b) != _CLAVES_BENEFICIO:
        raise ContenidoInvalido("C4_BENEFITS_INVALIDO")
    bid = b["benefit_id"]
    if not _es_id(bid):
        raise ContenidoInvalido("C4_BENEFITS_INVALIDO")
    title = _texto_beneficio(b["simple_title"], 1, 100)
    description = _texto_beneficio(b["description"], 1, 500)
    institution = _texto_beneficio(b["institution"], 1, 100)
    where = b["where_to_go"]
    if where is not None:
        where = _texto_beneficio(where, 1, 160)

    actions = b["actions"]
    if (not isinstance(actions, list) or not 1 <= len(actions) <= 10
            or not all(isinstance(a, str) and a for a in actions)):
        raise ContenidoInvalido("C4_BENEFITS_INVALIDO")

    source_ids = b["source_ids"]
    if not isinstance(source_ids, list) or not source_ids or not all(map(_es_id, source_ids)):
        raise ContenidoInvalido("C4_BENEFITS_INVALIDO")

    source_id, url = b["official_source_id"], b["official_url"]
    if source_id is None and url is None:
        source_id, url = "", ""  # PREG-045: sin fuente oficial; nunca se inventa
    elif not (_es_id(source_id) and _es_url_oficial(url) and source_ids[0] == source_id):
        raise ContenidoInvalido("C4_BENEFITS_INVALIDO")

    return CatalogEntry(
        benefit_id=bid,
        title=title,
        description=description,
        institution=institution,
        where_to_go=where,
        source_id=source_id,
        source_url=url,
        actions=tuple(actions),
        source_ids=tuple(source_ids),
    )


# --- PROMPT -----------------------------------------------------------------------


def _front_matter(texto: str) -> tuple[dict, str]:
    if not texto.startswith("---\n"):
        raise ContenidoInvalido("C4_PROMPT_INVALIDO")
    fin = texto.find("\n---\n", 3)
    if fin < 0:
        raise ContenidoInvalido("C4_PROMPT_INVALIDO")
    try:
        meta = yaml.safe_load(texto[4:fin])
    except yaml.YAMLError:
        raise ContenidoInvalido("C4_PROMPT_INVALIDO") from None
    if (not isinstance(meta, dict) or not _es_id(meta.get("prompt_template_id"))
            or not isinstance(meta.get("prompt_version"), str)
            or not _RE_SEMVER.match(meta["prompt_version"])):
        raise ContenidoInvalido("C4_PROMPT_INVALIDO")
    return meta, texto[fin + 5:]


def _bloques_respaldo(cuerpo: str) -> list[dict[str, str]]:
    """Bloques ``> clave: valor`` de ``## Plantilla de respaldo`` (separados por línea)."""
    inicio = _RE_RESPALDO.search(cuerpo)
    if inicio is None:
        raise ContenidoInvalido("C4_PROMPT_INVALIDO")
    seccion = cuerpo[inicio.end():]
    siguiente = _RE_SIGUIENTE_SECCION.search(seccion)
    if siguiente is not None:
        seccion = seccion[:siguiente.start()]

    bloques: list[dict[str, str]] = []
    actual: dict[str, str] | None = None
    for linea in seccion.split("\n"):
        if not linea.startswith("> "):
            actual = None
            continue
        clave, sep, valor = linea[2:].partition(": ")
        if not sep or not clave.strip():
            raise ContenidoInvalido("C4_PROMPT_INVALIDO")
        if actual is None:
            actual = {}
            bloques.append(actual)
        if clave in actual:
            raise ContenidoInvalido("C4_PROMPT_INVALIDO")
        actual[clave] = valor.strip()
    return bloques


def _valor(bloques: list[dict[str, str]], clave: str,
           filtro: tuple[str, str] | None = None) -> str:
    """Valor de ``clave`` en el único bloque que la trae (y cumple ``filtro``)."""
    candidatos = [
        b for b in bloques
        if clave in b and (filtro is None or b.get(filtro[0]) == filtro[1])
    ]
    if len(candidatos) != 1:
        raise ContenidoInvalido("C4_PROMPT_INVALIDO")
    return candidatos[0][clave]


def _plantilla(valor: str, placeholder: str | None = None, con_aviso: bool = False) -> str:
    """Valida una frase marco del Rol 4 y la devuelve sin el aviso final."""
    texto = valor
    if con_aviso:
        sufijo = f" {DISCLAIMER}"
        if not texto.endswith(sufijo):
            raise ContenidoInvalido("C4_PROMPT_INVALIDO")
        texto = texto[: -len(sufijo)].rstrip()
    esperados = [placeholder] if placeholder else []
    if _RE_PLACEHOLDER.findall(texto) != esperados:
        raise ContenidoInvalido("C4_PROMPT_INVALIDO")
    limpio = texto.replace(placeholder, " ") if placeholder else texto
    if not limpio.strip() or not es_texto_plano(limpio) or contiene_promesa(limpio):
        raise ContenidoInvalido("C4_PROMPT_INVALIDO")
    return texto


def _frase_estado(texto: str) -> str:
    """Frase de la instrucción 5 lista para el texto: '; ' -> '. ' y mayúscula.

    "el trámite ya está en curso; vale la pena esperar la respuesta." pasa a
    "El trámite ya está en curso. Vale la pena esperar la respuesta." (igual que
    REF-01 de ``content/demo/salidas_referencia_prompts.json``).
    """
    partes = [p.strip().rstrip(".").strip() for p in texto.split(";")]
    if not all(partes):
        raise ContenidoInvalido("C4_PROMPT_INVALIDO")
    frase = ". ".join(p[0].upper() + p[1:] for p in partes) + "."
    if (not es_texto_plano(frase) or contiene_promesa(frase)
            or "`" in frase or "{{" in frase):
        raise ContenidoInvalido("C4_PROMPT_INVALIDO")
    return frase


def _frases_estado(cuerpo: str) -> MappingProxyType:
    """Frase por estado de seguimiento, desde ``## Instrucciones`` del prompt (DEC-060).

    Exige GESTION_EN_CURSO, GESTION_RECHAZADA y SIN_CUPO exactamente una vez;
    los demás estados de la instrucción 5 no se usan como frase.
    """
    inicio = _RE_INSTRUCCIONES.search(cuerpo)
    if inicio is None:
        raise ContenidoInvalido("C4_PROMPT_INVALIDO")
    seccion = cuerpo[inicio.end():]
    siguiente = _RE_SIGUIENTE_SECCION.search(seccion)
    if siguiente is not None:
        seccion = seccion[:siguiente.start()]

    frases: dict[str, str] = {}
    vistos: list[str] = []
    for m in _RE_FRASE_ESTADO.finditer(seccion):
        estados = m.group(1).split(" o ")
        vistos.extend(estados)
        for estado in estados:
            if estado in ESTADOS_SEGUIMIENTO:
                frases[estado] = _frase_estado(m.group(2))
    if any(vistos.count(estado) != 1 for estado in ESTADOS_SEGUIMIENTO):
        raise ContenidoInvalido("C4_PROMPT_INVALIDO")
    return MappingProxyType({estado: frases[estado] for estado in ESTADOS_SEGUIMIENTO})


def _con_saludo(marco: str) -> str:
    """El marco debe abrir con un saludo de texto plano y sin promesas."""
    saludo = saludo_de(marco)
    if not saludo or not es_texto_plano(saludo) or contiene_promesa(saludo):
        raise ContenidoInvalido("C4_PROMPT_INVALIDO")
    return marco


def _leer_plantillas(prompts: dict[str, PromptC4], etiqueta_donde_ir: str) -> PlantillasTexto:
    guion = _bloques_respaldo(prompts[PROMPT_GUION].cuerpo)
    mensaje = _bloques_respaldo(prompts[PROMPT_MENSAJE].cuerpo)
    asistente = _bloques_respaldo(prompts[PROMPT_ASISTENTE].cuerpo)
    individual = ("intent", "REQUIRES_DETERMINISTIC_EVALUATION")
    catalogo = ("intent", "CATALOG_INFO")
    return PlantillasTexto(
        guion=_con_saludo(_plantilla(_valor(guion, "script"), PH_TITULOS, con_aviso=True)),
        whatsapp=_con_saludo(
            _plantilla(_valor(mensaje, "whatsapp_preview"), PH_TITULOS, con_aviso=True)
        ),
        tarjeta_titulo=_plantilla(_valor(mensaje, "printable_card.title")),
        tarjeta_introduccion=_plantilla(_valor(mensaje, "printable_card.introduction")),
        seccion_razon=_plantilla(_valor(mensaje, "printable_card.sections[].reason")),
        seccion_accion=_plantilla(
            _valor(mensaje, "printable_card.sections[].action"), PH_INSTITUCION
        ),
        asistente_individual=_plantilla(
            _valor(asistente, "answer", individual), con_aviso=True
        ),
        asistente_catalogo=_plantilla(
            _valor(asistente, "answer", catalogo), PH_TITULOS, con_aviso=True
        ),
        etiqueta_donde_ir=etiqueta_donde_ir,
        frases_estado_guion=_frases_estado(prompts[PROMPT_GUION].cuerpo),
        frases_estado_mensaje=_frases_estado(prompts[PROMPT_MENSAJE].cuerpo),
    )
