"""Adaptador YAML del bundle C4 del Rol 4 (``content/manifest.yaml``) — DEC-022.

Es el C4 runtime del modo real (``E3_MOCK=0``) de la demo local, por decisión
del dueño de producto (propuesta DEC-048, 2026-10-15), aunque ``content/README``
y DEC-040 lo declaran no publicable hasta API-T14 y la revisión humana. El mock
JSON del Rol 2 (``backend/fixtures/c4_mock``) sigue siendo el de ``E3_MOCK=1`` y
el de los tests que ya lo usan (``config.cargar_ranking_config``).

``content/`` es de SOLO LECTURA: este módulo no escribe nada. Expone tres cosas:

- ``ranking``: el mismo ``RankingConfig`` que consume ``scoring`` (U/B/V,
  medianas por jardín, pesos de estado, prioridad familiar).
- ``beneficios``: catálogo de presentación de ``beneficios.yaml`` (título
  simple, dónde ir y cita oficial HTTPS) por ``benefit_id``.
- ``preguntas``: texto de ``preguntas.yaml`` por ``missing_code`` del motor.

Falla cerrado (``ConfigInvalida``) ante cualquier duda: schema C4 cerrado,
``sha256`` de cada archivo de ``files[]`` (bytes LF, DEC-045) y
``content_bundle_hash`` (SUP-041), rutas bajo la raíz y sin duplicados, las seis
clases obligatorias, suma U/B/V = 1 ± 1e-6 e ingreso default positivo,
``ranking``/``accessibility`` idénticos a sus archivos (SUP-040), y catálogo y
preguntas con IDs, URLs HTTPS y largos compatibles con C3. Los mensajes de error
son fijos: no ecoan contenido de los archivos.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import jsonschema
import yaml

from app.priority.config import (
    _C4_SCHEMA_PATH,
    _REPO_DIR,
    ConfigInvalida,
    RankingConfig,
    _validar_invariantes_negocio,
)

# Manifest por defecto del bundle del Rol 4. Se lee en cada carga (no se copia
# al importar) para que los tests puedan apuntar a una copia manipulada.
CONTENT_MANIFEST = _REPO_DIR / "content" / "manifest.yaml"

# Clases de archivo obligatorias de C4 (CONT-002).
CLASES_OBLIGATORIAS = frozenset(
    {"WEIGHTS", "QUESTIONS", "BENEFITS", "PROMPT", "ACCESSIBILITY", "I18N"}
)

# Clases que este adaptador lee y que, por eso, deben ser un único archivo.
_CLASES_UNICAS = ("WEIGHTS", "QUESTIONS", "BENEFITS", "ACCESSIBILITY")

# Motivos de ``sin_pregunta`` admitidos por ``preguntas.yaml``.
_SIN_PREGUNTA = frozenset(
    {"DATO_ADMINISTRATIVO", "SE_RESUELVE_CON_OTRA_PREGUNTA", "NO_SE_PREGUNTA_A_LA_FAMILIA"}
)

# Patrones y largos máximos de C3 para lo que sale de este catálogo
# (``Id``, ``missing_codes``, ``Opportunity.simple_title``/``where_to_go``,
# ``suggested_questions``). Son límites del contrato, no números de negocio.
_ID = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")
_MISSING_CODE = re.compile(r"^[a-z0-9_.-]+$")
_MAX_ID = 80
_MAX_MISSING_CODE = 80
_MAX_TITULO = 100
_MAX_DONDE = 160
_MAX_PREGUNTA = 200

_BOM = b"\xef\xbb\xbf"


@dataclass(frozen=True)
class BeneficioC4:
    """Entrada del catálogo de presentación (``beneficios.yaml``)."""

    benefit_id: str
    simple_title: str
    where_to_go: str | None
    official_source_id: str | None
    official_url: str | None


@dataclass(frozen=True)
class ContenidoC4:
    """Bundle C4 del Rol 4 ya validado (solo lectura)."""

    ranking: RankingConfig
    content_version: str
    content_bundle_hash: str
    beneficios: dict[str, BeneficioC4]
    preguntas: dict[str, str]


# --- lectura -----------------------------------------------------------------


def _leer_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ConfigInvalida("Archivo del bundle C4 ausente o ilegible") from exc


def _yaml_de_bytes(data: bytes) -> dict:
    if data.startswith(_BOM):
        raise ConfigInvalida("Archivo del bundle C4 con BOM")
    try:
        doc = yaml.safe_load(data.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ConfigInvalida("Archivo del bundle C4 no es YAML UTF-8 válido") from exc
    if not isinstance(doc, dict):
        raise ConfigInvalida("Archivo del bundle C4 sin objeto raíz")
    return doc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ruta_bajo_raiz(raiz: Path, ruta: str) -> Path:
    """Resuelve ``ruta`` (POSIX relativa) y exige que quede bajo ``raiz``."""
    rel = PurePosixPath(ruta)
    if rel.is_absolute() or ".." in rel.parts:
        raise ConfigInvalida("Ruta del bundle C4 fuera de la raíz")
    destino = (raiz / Path(*rel.parts)).resolve()
    try:
        destino.relative_to(raiz.resolve())
    except ValueError as exc:
        raise ConfigInvalida("Ruta del bundle C4 fuera de la raíz") from exc
    return destino


# --- validaciones del manifest ----------------------------------------------


def _validar_schema(manifest: dict) -> None:
    try:
        with _C4_SCHEMA_PATH.open(encoding="utf-8") as fh:
            schema = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigInvalida("Schema C4 no disponible") from exc
    try:
        jsonschema.validate(manifest, schema)
    except jsonschema.ValidationError as exc:
        raise ConfigInvalida("Bundle C4 no cumple el schema cerrado") from exc


def _validar_archivos(manifest: dict, raiz: Path) -> dict[str, bytes]:
    """Hashes, unicidad y clases; devuelve los bytes de cada clase única."""
    rutas: set[str] = set()
    por_clase: dict[str, list[bytes]] = {}
    for entrada in manifest["files"]:
        ruta = entrada["path"]
        if ruta in rutas:
            raise ConfigInvalida("Ruta duplicada en files[] del bundle C4")
        rutas.add(ruta)
        data = _leer_bytes(_ruta_bajo_raiz(raiz, ruta))
        if _sha256(data) != entrada["sha256"]:
            # Incluye CRLF: DEC-045 fija LF y el hash se calculó con LF.
            raise ConfigInvalida("sha256 de un archivo del bundle C4 no coincide")
        por_clase.setdefault(entrada["kind"], []).append(data)

    faltantes = CLASES_OBLIGATORIAS - set(por_clase)
    if faltantes:
        raise ConfigInvalida("Bundle C4 sin todas las clases obligatorias")
    for clase in _CLASES_UNICAS:
        if len(por_clase[clase]) != 1:
            raise ConfigInvalida("Bundle C4 con una clase única repetida")

    # SUP-041: sha256 de las líneas '<sha256>  <path>\n' ordenadas por path.
    lineas = "".join(
        f"{e['sha256']}  {e['path']}\n"
        for e in sorted(manifest["files"], key=lambda e: e["path"])
    )
    if _sha256(lineas.encode("utf-8")) != manifest["content_bundle_hash"]:
        raise ConfigInvalida("content_bundle_hash del bundle C4 no coincide")

    return {clase: por_clase[clase][0] for clase in _CLASES_UNICAS}


# --- catálogo y preguntas ----------------------------------------------------


def _texto(valor, maximo: int, *, nulo: bool) -> str | None:
    if valor is None and nulo:
        return None
    if not isinstance(valor, str) or not valor.strip() or len(valor) > maximo:
        raise ConfigInvalida("Texto del catálogo C4 vacío o demasiado largo")
    return valor


def _id_valido(valor) -> bool:
    return isinstance(valor, str) and len(valor) <= _MAX_ID and bool(_ID.match(valor))


def _cargar_beneficios(doc: dict) -> dict[str, BeneficioC4]:
    lista = doc.get("beneficios")
    if not isinstance(lista, list) or not lista:
        raise ConfigInvalida("Catálogo de beneficios C4 vacío")
    catalogo: dict[str, BeneficioC4] = {}
    for item in lista:
        if not isinstance(item, dict) or not _id_valido(item.get("benefit_id")):
            raise ConfigInvalida("benefit_id inválido en el catálogo C4")
        bid = item["benefit_id"]
        if bid in catalogo:
            raise ConfigInvalida("benefit_id duplicado en el catálogo C4")
        fuente = item.get("official_source_id")
        url = item.get("official_url")
        # Cita oficial: ambas o ninguna (PREG-045); URL siempre HTTPS.
        if (fuente is None) != (url is None):
            raise ConfigInvalida("Cita oficial incompleta en el catálogo C4")
        if fuente is not None and not _id_valido(fuente):
            raise ConfigInvalida("official_source_id inválido en el catálogo C4")
        if url is not None and (not isinstance(url, str) or not url.startswith("https://")):
            raise ConfigInvalida("official_url no HTTPS en el catálogo C4")
        catalogo[bid] = BeneficioC4(
            benefit_id=bid,
            simple_title=_texto(item.get("simple_title"), _MAX_TITULO, nulo=False),
            where_to_go=_texto(item.get("where_to_go"), _MAX_DONDE, nulo=True),
            official_source_id=fuente,
            official_url=url,
        )
    return catalogo


def _cargar_preguntas(doc: dict) -> dict[str, str]:
    """``missing_code`` -> texto. ``ver`` resuelve a la pregunta referida."""
    lista = doc.get("preguntas")
    if not isinstance(lista, list) or not lista:
        raise ConfigInvalida("Catálogo de preguntas C4 vacío")
    entradas: dict[str, dict] = {}
    for item in lista:
        code = item.get("missing_code") if isinstance(item, dict) else None
        if (
            not isinstance(code, str)
            or len(code) > _MAX_MISSING_CODE
            or not _MISSING_CODE.match(code)
        ):
            raise ConfigInvalida("missing_code inválido en preguntas C4")
        if code in entradas:
            raise ConfigInvalida("missing_code duplicado en preguntas C4")
        tiene_texto = "pregunta" in item
        motivo = item.get("sin_pregunta")
        if tiene_texto == (motivo is not None):
            raise ConfigInvalida("Pregunta C4 sin texto ni motivo, o con ambos")
        if motivo is not None and motivo not in _SIN_PREGUNTA:
            raise ConfigInvalida("Motivo sin_pregunta desconocido en preguntas C4")
        if tiene_texto:
            _texto(item["pregunta"], _MAX_PREGUNTA, nulo=False)
        entradas[code] = item

    preguntas: dict[str, str] = {}
    for code, item in entradas.items():
        if "pregunta" in item:
            preguntas[code] = item["pregunta"]
        elif item["sin_pregunta"] == "SE_RESUELVE_CON_OTRA_PREGUNTA":
            destino = entradas.get(item.get("ver"))
            if destino is None or "pregunta" not in destino:
                raise ConfigInvalida("Referencia ver inválida en preguntas C4")
            preguntas[code] = destino["pregunta"]
        # DATO_ADMINISTRATIVO / NO_SE_PREGUNTA_A_LA_FAMILIA: sin pregunta.
    return preguntas


# --- API pública -------------------------------------------------------------


def cargar_contenido_c4(manifest_path: str | Path | None = None) -> ContenidoC4:
    """Carga y valida el bundle C4 YAML del Rol 4; falla cerrado.

    Las rutas de ``files[]`` (``content/...``) se resuelven contra el padre del
    directorio del manifest, así una copia ``<tmp>/content/`` es relocalizable.
    """
    path = Path(manifest_path) if manifest_path is not None else Path(CONTENT_MANIFEST)
    manifest = _yaml_de_bytes(_leer_bytes(path))
    _validar_schema(manifest)
    _validar_invariantes_negocio(manifest)

    raiz = path.resolve().parent.parent
    datos = _validar_archivos(manifest, raiz)

    pesos = _yaml_de_bytes(datos["WEIGHTS"])
    accesibilidad = _yaml_de_bytes(datos["ACCESSIBILITY"])
    if pesos.get("ranking") != manifest["ranking"]:
        raise ConfigInvalida("ranking del manifest distinto de su archivo (SUP-040)")
    if accesibilidad.get("accessibility") != manifest["accessibility"]:
        raise ConfigInvalida("accessibility del manifest distinto de su archivo (SUP-040)")

    ranking = manifest["ranking"]
    config = RankingConfig(
        axis_weights=ranking["axis_weights"],
        urgency=ranking["urgency"],
        benefit_impact=ranking["benefit_impact"],
        vulnerability=ranking["vulnerability"],
        opportunity_score=ranking["opportunity_score"],
        family_priority=ranking["family_priority"],
        kpi=manifest["kpi"],
        accessibility=manifest["accessibility"],
        content_version=manifest["content_version"],
        content_bundle_hash=manifest["content_bundle_hash"],
    )
    return ContenidoC4(
        ranking=config,
        content_version=manifest["content_version"],
        content_bundle_hash=manifest["content_bundle_hash"],
        beneficios=_cargar_beneficios(_yaml_de_bytes(datos["BENEFITS"])),
        preguntas=_cargar_preguntas(_yaml_de_bytes(datos["QUESTIONS"])),
    )
