"""Motor real detrás de ``E3_MOCK=0`` (B1): snapshot inmutable en memoria.

Lee el precálculo persistido del Rol 1 (tablas ``evaluaciones`` + ``accesos`` que
genera ``python -m app.db.build_views``: es la salida exacta de
``AccesoService``, C1 + acceso + cupo BEN-018) y el contexto C2
(``ContextoBuilder``), y arma UNA vez por proceso las vistas C3 de las 500
familias y los 50 jardines. Después, cada request es un lookup y una copia.

Reglas (decisiones 2–10 del plan B1 y ajustes del usuario del 2026-10-15):

- La API no recalcula ni altera elegibilidad, nivel ni acceso: los copia del
  motor y valida las invariantes ``oneOf`` de C3 (falla cerrado).
- U/B/V, score y prioridad familiar salen de ``app.priority`` con el C4 YAML
  del Rol 4 (``content/``, DEC-048). Este módulo no tiene números de negocio:
  solo límites de C3 (largos, ``maxItems``) y el umbral de mayoría de edad del
  enum ``CompositionMember`` (DEC-049).
- ``position``/``top_*`` siguen el orden por grupo de acción (DEC-053); la
  prioridad familiar usa la lista por score de ``score_opportunities``.
- Un beneficio sin cita HTTPS en C4 (hoy BEN-018/019/020, PREG-045) no se
  emite como ``Opportunity``; sigue completo en ``benefit_results`` (DEC-050).
- Degradación (decisión 4): ``obtener_snapshot()`` devuelve ``None`` y la ruta
  usa los mocks cuando ``E3_MOCK`` está activo o algo falla; en ese caso se
  loguea ``runtime_degradado_a_mock: motivo=<CODIGO>`` con un código fijo, sin
  IDs ni valores. El fallo se cachea contra la misma clave (DB, manifest y
  cada archivo de su ``files[]``, DEC-063): se registra una vez y se reintenta
  solo cuando cambia alguno.
- ``meta`` de las rutas que sirven el snapshot declara ``content_version`` y
  ``content_bundle_hash`` del bundle con que se armó (``procedencia``, DEC-062).
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import re
import sqlite3
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from app.access.model import SEMAFORO, EstadoAcceso
from app.api import mock_data, runtime
from app.api.deps import SNAPSHOT_ID, mock_habilitado
from app.api.errors import ApiError
from app.api.models import validar_benefit_result, validar_opportunity
from app.catalog import territorial
from app.context import ContextoBuilder
from app.engine.model import Nivel, Tri
from app.priority import (
    BenefitInput,
    ConfigInvalida,
    RankingConfig,
    UrgencySignals,
    VulnerabilitySignals,
    family_priority_score,
    score_opportunities,
)
from app.priority import content_c4
from app.priority.content_c4 import ContenidoC4, cargar_contenido_c4
from app.priority.orden import ORDENES, ordenar_por_grupo_accion, ordenar_vista

logger = logging.getLogger("app.api")

# --- códigos fijos de degradación (nunca IDs ni valores) ---------------------

MOTIVO_DB_AUSENTE = "DB_AUSENTE"
MOTIVO_PRECALCULO_AUSENTE = "PRECALCULO_AUSENTE"
MOTIVO_DB_ILEGIBLE = "DB_ILEGIBLE"
MOTIVO_C4_INVALIDO = "C4_INVALIDO"
MOTIVO_INVARIANTE = "INVARIANTE_MOTOR"

# --- límites y vocabularios de C3 --------------------------------------------

_PATRON_ID = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")
_PATRON_CODIGO = re.compile(r"^[a-z0-9_.-]+$")
_PATRON_IDIOMA = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")
_PATRON_CURSOR = re.compile(r"^[0-9]{1,6}$")
_MAX_ID = 80
_MAX_CODIGO = 80
_MAX_CAMPO = 120
_MAX_TRAZA = 200
_MAX_CODIGOS = 20
_MAX_PREGUNTAS = 10
_MAX_TOP = 3  # FamilySummary.top_benefit_ids / FamilyDetail.top_opportunities
_EDAD_MIN, _EDAD_MAX = 0, 120

_OPERADORES_C3 = frozenset({
    "EQ", "LT", "LTE", "GT", "GTE", "IN", "BETWEEN", "ACTIVE_ON_DATE",
    "RANGE_LOOKUP", "REF_EQ", "COUNT_REL_GTE", "NOT_EXISTS_WITHIN",
})
_RESULTADO_TRAZA = {"SI": "CUMPLE", "NO": "NO_CUMPLE", "INDETERMINADO": "INDETERMINADO"}
_TRAMOS_RSH = frozenset({40, 50, 60, 70, 80, 90, 100})
_ZONAS = frozenset({"URBANA", "RURAL"})

# DEC-049: mapeos C2 -> C3 por allowlist.
_ROL_REFERENCIA = "ADULTA_REFERENCIA"
_EDAD_MAYORIA = 18  # CompositionMember: CHILD si edad < 18, si no OTHER_ADULT
_INGRESO_C3 = {
    "MENOS_110K": "UNDER_110K",
    "ENTRE_110K_250K": "110K_250K",
    "ENTRE_250K_400K": "250K_400K",
    "MAS_400K": "OVER_400K",
}
_FORMATO_C3 = {"TEXTO": "TEXT", "VISUAL": "VISUAL", "AUDIO": "AUDIO"}
# no_informado de C2 -> enum cerrado FamilyContextView.missing_codes.
_NO_INFORMADO_C3 = {
    "tramo_rsh": "rsh_band",
    "chile_crece_contigo": "chile_crece_contigo_access",
    "embarazo": "pregnancy",
    "vivienda": "housing_type",
    "edad_nino_jardin": "child_age",
    "ingreso_per_capita": "income_band",
}

_ACCION_POR_ESTADO = {
    "INDETERMINADO": "ASK_FIRST",
    "PENDIENTE_ANTECEDENTES": "ASK_FIRST",
    "ASIGNADO": "FOLLOW_UP",
    "GESTION_EN_CURSO": "FOLLOW_UP",
    "GESTION_RECHAZADA": "FOLLOW_UP",
    "SIN_CUPO": "FOLLOW_UP",
}

# Frase fija por estado. "Nunca prometer": siempre "podría calificar" / "vale la
# pena consultar" (fuente funcional §2.4.2 y tabla de estados, §6 de la
# división, CONT-003, content/prompts/explicacion.md §5; DEC-054 del workflow
# GenAI). Sin cifras. ASIGNADO y GESTION_EN_CURSO describen hechos del dato.
# Ninguna clave de content/ cubre este copy: Rol 4 debería ser su dueño.
_WHY_FIRST = {
    "ELEGIBLE_SIN_ASIGNACION": (
        "Podría calificar y no registra una gestión. Vale la pena consultar o pedirlo."
    ),
    "PENDIENTE_ANTECEDENTES": (
        "Podría calificar si acredita los antecedentes que faltan. "
        "Vale la pena consultar en la institución."
    ),
    "INDETERMINADO": "Aún no se puede saber si podría calificar: falta información.",
    "GESTION_RECHAZADA": (
        "Podría calificar, pero su gestión fue rechazada. "
        "Vale la pena consultar qué opciones hay."
    ),
    "GESTION_EN_CURSO": "Tiene una gestión en curso. Vale la pena esperar la respuesta.",
    "SIN_CUPO": (
        "Podría calificar, pero hoy no hay cupo. Vale la pena consultar por la lista de espera."
    ),
    "ASIGNADO": "La familia ya tiene este beneficio.",
}

# Semáforo de la tarjeta: precedencia verde > amarillo > azul (app.access.model).
_SEMAFORO_C3 = (("verde", "VERDE"), ("amarillo", "AMARILLO"), ("azul", "AZUL"))

_TABLAS_REQUERIDAS = frozenset({
    "familias", "jardines", "comunas", "beneficios", "beneficios_versiones",
    "evaluaciones", "accesos",
})


class _PrecalculoAusente(Exception):
    """La DB existe pero no trae el precálculo completo de ``build_views``."""


@dataclass(frozen=True)
class MotorSnapshot:
    """Vistas C3 ya construidas desde el motor. Nunca se mutan."""

    # Misma forma que ``mock_data.FAMILIAS[id]``: summary (estática, sin
    # conversación), garden_id, composition, rsh_band, informed (False),
    # benefit_results, opportunities (por position) y context.
    familias: dict[str, dict]
    # (prioridad sin conversación, prioridad conversada) por familia.
    prioridades: dict[str, tuple[float, float]]
    # benefit_id por orden de vista (``prioridad``/``urgencia``/``beneficio``).
    ordenes: dict[str, dict[str, tuple[str, ...]]]
    # JardinSummary sin los conteos de conversaciones (se suman por request).
    jardines: dict[str, dict]
    orden_jardines: tuple[str, ...]
    # Familias del jardín por prioridad estática desc y family_id asc.
    familias_por_jardin: dict[str, tuple[str, ...]]
    content_version: str
    content_bundle_hash: str
    segundos_build: float
    # Huella de la clave de caché (DB, manifest y files[]). Va dentro del cursor para
    # que una página pedida tras regenerar la DB dé 422 (``snapshot_id`` sigue
    # siendo la constante de demo).
    huella: str


# --- caché del snapshot ------------------------------------------------------

_LOCK = threading.Lock()
# Último snapshot construido, con su clave.
_CACHE: tuple[tuple, MotorSnapshot] | None = None
# Clave del último fallo ya registrado: no se reintenta (ni se vuelve a loguear)
# hasta que cambie la DB, el manifest o un archivo de su ``files[]``.
_FALLO: tuple | None = None
# Rutas de ``files[]`` por (ruta, estado) del manifest: el YAML se parsea solo
# cuando cambia el manifest; cada request hace un ``stat`` por archivo. Se
# asigna como una tupla (atómica): una carrera solo repite el parseo.
_RUTAS_MANIFEST: tuple[tuple, tuple[Path, ...]] | None = None


def limpiar_cache() -> None:
    """Olvida el snapshot, el último fallo y las rutas del manifest (tests)."""
    global _CACHE, _FALLO, _RUTAS_MANIFEST
    with _LOCK:
        _CACHE = None
        _FALLO = None
        _RUTAS_MANIFEST = None
        _DECLARADAS.clear()


def _degradar(motivo: str) -> None:
    logger.warning("runtime_degradado_a_mock: motivo=%s", motivo)


def _estado_archivo(path: Path) -> tuple[int, int] | None:
    """(mtime_ns, tamaño) o ``None`` si el archivo no existe o no se puede leer."""
    try:
        st = path.stat()
    except (OSError, ValueError):  # ValueError: ruta con caracteres inválidos
        return None
    return st.st_mtime_ns, st.st_size


def _leer_rutas_files(manifest: Path) -> tuple[Path, ...]:
    """``files[].path`` del manifest, sin validar; ``()`` si no se puede leer.

    Solo dice qué archivos vigilar. La validación (schema, rutas bajo la raíz,
    sha256) es de ``cargar_contenido_c4``; las rutas se resuelven igual que
    allí, contra el padre del directorio del manifest.
    """
    try:
        doc = yaml.safe_load(manifest.read_bytes().decode("utf-8"))
        raiz = manifest.resolve().parent.parent
        return tuple(raiz / str(e["path"]) for e in doc["files"])
    except (OSError, UnicodeDecodeError, yaml.YAMLError, TypeError, KeyError):
        return ()


def _rutas_files(manifest: Path, estado: tuple[int, int] | None) -> tuple[Path, ...]:
    global _RUTAS_MANIFEST
    clave = (str(manifest.resolve()), estado)
    cacheado = _RUTAS_MANIFEST
    if cacheado is not None and cacheado[0] == clave:
        return cacheado[1]
    rutas = _leer_rutas_files(manifest) if estado is not None else ()
    _RUTAS_MANIFEST = (clave, rutas)
    return rutas


def _huella(clave: tuple) -> str:
    """Huella corta de la clave (no expone rutas ni tiempos)."""
    return hashlib.sha256(repr(clave).encode("utf-8")).hexdigest()[:16]


def _intentar(db: Path, manifest: Path, clave: tuple) -> tuple[MotorSnapshot | None, str]:
    """Construye el snapshot o devuelve ``(None, motivo)`` con un código fijo."""
    if clave[1] is None:
        return None, MOTIVO_DB_AUSENTE
    if clave[3] is None:
        return None, MOTIVO_C4_INVALIDO
    try:
        contenido = cargar_contenido_c4(manifest)
        return _construir(db, contenido, _huella(clave)), ""
    except ConfigInvalida:
        return None, MOTIVO_C4_INVALIDO
    except _PrecalculoAusente:
        return None, MOTIVO_PRECALCULO_AUSENTE
    except sqlite3.Error:
        return None, MOTIVO_DB_ILEGIBLE
    except (ValueError, KeyError, TypeError):
        # Incluye InvarianteError (ValueError): una combinación incoherente
        # del motor nunca llega a la respuesta.
        return None, MOTIVO_INVARIANTE


def obtener_snapshot() -> MotorSnapshot | None:
    """Snapshot del motor real, o ``None`` si hay que servir mocks.

    Lee ``runtime.DB_PATH`` y ``content_c4.CONTENT_MANIFEST`` en cada llamada.
    La clave de caché es (ruta, mtime y tamaño) de la DB, del manifest C4 y de
    cada archivo de su ``files[]`` (DEC-063): si se regenera la DB con
    ``build_views`` o se edita ``content/``, el siguiente request lo toma. Un
    fallo también se cachea contra su clave: se loguea una vez y no se
    reconstruye en cada request.
    """
    global _CACHE, _FALLO
    if mock_habilitado():
        return None
    db = Path(runtime.DB_PATH)
    manifest = Path(content_c4.CONTENT_MANIFEST)
    estado_manifest = _estado_archivo(manifest)
    clave = (
        str(db.resolve()), _estado_archivo(db),
        str(manifest.resolve()), estado_manifest,
        tuple(
            (str(ruta), _estado_archivo(ruta))
            for ruta in _rutas_files(manifest, estado_manifest)
        ),
    )
    with _LOCK:
        if _CACHE is not None and _CACHE[0] == clave:
            return _CACHE[1]
        if _FALLO == clave:
            return None
        snap, motivo = _intentar(db, manifest, clave)
        if snap is None:
            _FALLO = clave
            _degradar(motivo)
            return None
        _CACHE = (clave, snap)
        _FALLO = None
        logger.info(
            "motor_real_snapshot_listo familias=%d jardines=%d build_s=%.2f",
            len(snap.familias), len(snap.jardines), snap.segundos_build,
        )
        return snap


# --- existencia (rutas que no leen la ficha) ---------------------------------
# El llamador resuelve el snapshot UNA vez (``obtener_snapshot()``) y lo pasa a
# estos helpers: así existencia y jardín salen de la misma fuente aunque la DB
# cambie entre medio.


def garden_de(snap: MotorSnapshot | None, family_id: str) -> str | None:
    """Jardín de la familia (snapshot real o mock), o ``None`` si no existe."""
    fam = snap.familias.get(family_id) if snap is not None else mock_data.FAMILIAS.get(family_id)
    return None if fam is None else fam["garden_id"]


def estados_oportunidades(snap: MotorSnapshot | None, family_id: str) -> dict[str, str] | None:
    """``{benefit_id: access_state}`` de las oportunidades de la familia (DEC-060).

    Del snapshot real o de ``mock_data``; ``None`` si la familia no existe. Guion
    y mensaje solo aceptan estos IDs: lo demás responde 422.
    """
    fam = snap.familias.get(family_id) if snap is not None else mock_data.FAMILIAS.get(family_id)
    if fam is None:
        return None
    return {o["benefit_id"]: o["access_state"] for o in fam["opportunities"]}


def procedencia(snap: MotorSnapshot | None) -> tuple[str, str] | None:
    """(content_version, content_bundle_hash) del snapshot, o ``None`` (mock)."""
    return None if snap is None else (snap.content_version, snap.content_bundle_hash)


def familia_existe(snap: MotorSnapshot | None, family_id: str) -> bool:
    return garden_de(snap, family_id) is not None


# --- vistas por request ------------------------------------------------------


def vista_familia(snap: MotorSnapshot, family_id: str, conversada: bool) -> dict:
    """Familia con ``informed``/``summary`` según las conversaciones vigentes.

    Si la familia tiene antecedentes declarados (``antecedentes_store``), es la
    ficha reevaluada con ellos (``_vigente``), igual que la respuesta del POST.
    Copia superficial: ``familia_detail_data`` hace la copia profunda.
    """
    fam, (pendiente, con_conversacion), _ordenes = _vigente(snap, family_id)
    summary = dict(
        fam["summary"],
        priority_score=con_conversacion if conversada else pendiente,
        conversation_status="CONVERSADA" if conversada else "PENDIENTE",
    )
    return {**fam, "summary": summary, "informed": conversada}


def resumen_familia(snap: MotorSnapshot, family_id: str, conversada: bool) -> dict:
    """``FamilySummary`` de C3 (copia).

    Sale del snapshot sin antecedentes declarados: la lista del jardín se ordena
    por la prioridad estática del snapshot (``familias_por_jardin``) y el
    resumen debe ser coherente con ese orden.
    """
    pendiente, con_conversacion = snap.prioridades[family_id]
    return dict(
        copy.deepcopy(snap.familias[family_id]["summary"]),
        priority_score=con_conversacion if conversada else pendiente,
        conversation_status="CONVERSADA" if conversada else "PENDIENTE",
    )


def contexto(snap: MotorSnapshot, family_id: str) -> dict:
    """``FamilyContextView`` de C3 (copia), con lo declarado aplicado."""
    return copy.deepcopy(_vigente(snap, family_id)[0]["context"])


def oportunidades(snap: MotorSnapshot, family_id: str, orden: str) -> list[dict]:
    """``Opportunity`` de la familia en el orden de vista pedido (copias).

    Con antecedentes declarados, las de la ficha reevaluada (``_vigente``).
    """
    fam, _prioridades, ordenes = _vigente(snap, family_id)
    por_id = {o["benefit_id"]: o for o in fam["opportunities"]}
    return [copy.deepcopy(por_id[bid]) for bid in ordenes[orden]]


# --- antecedentes declarados en las lecturas (DEC-081/DEC-082) ----------------
# ``POST /familias/{id}/antecedentes`` guarda los hechos en ``antecedentes_store``
# (memoria del proceso). Las lecturas de la ficha, el contexto y las
# oportunidades aplican esos hechos con la MISMA reevaluación que la respuesta
# del POST (``_reconstruir``), para que la ficha no "vuelva atrás" al recargar.
# Nada se escribe en la DB ni en el snapshot; se pierde al reiniciar.

# (huella del snapshot, family_id, campos canónicos) -> (familia, prioridades, órdenes)
_DECLARADAS: dict[tuple, tuple[dict, tuple[float, float], dict[str, tuple[str, ...]]]] = {}
_MAX_DECLARADAS = 256


def campos_declarados(hechos: list[dict]) -> dict:
    """Hechos acumulados -> campo de pantalla con su último valor conocido.

    El último hecho de un campo gana; un "No sé" no fuerza un dato: se omite y
    el campo sigue indeterminado (sigue faltando).
    """
    campos: dict = {}
    for hecho in hechos:
        if hecho["desconocido"]:
            campos.pop(hecho["campo"], None)
        else:
            campos[hecho["campo"]] = hecho["valor"]
    return campos


def _vigente(
    snap: MotorSnapshot, family_id: str
) -> tuple[dict, tuple[float, float], dict[str, tuple[str, ...]]]:
    """(familia, prioridades, órdenes) con lo declarado aplicado, o del snapshot.

    Sin hechos declarados (o si la reevaluación no puede operar) devuelve lo del
    snapshot, como antes. El resultado reevaluado se cachea por huella del
    snapshot y campos declarados: regenerar la DB o declarar algo nuevo invalida.
    """
    from app.api import antecedentes_store

    base = (snap.familias[family_id], snap.prioridades[family_id], snap.ordenes[family_id])
    campos = campos_declarados(antecedentes_store.declarados_get(family_id))
    if not campos:
        return base
    clave = (snap.huella, family_id, json.dumps(campos, sort_keys=True, default=str))
    cacheado = _DECLARADAS.get(clave)
    if cacheado is not None:
        return cacheado
    reevaluada = _reconstruir(family_id, campos)
    if reevaluada is None:
        return base
    if len(_DECLARADAS) >= _MAX_DECLARADAS:
        _DECLARADAS.clear()
    _DECLARADAS[clave] = reevaluada
    return reevaluada


def resumen_jardin(snap: MotorSnapshot, garden_id: str, conversadas: frozenset[str]) -> dict:
    """``JardinSummary`` con los conteos de conversaciones vigentes."""
    base = dict(snap.jardines[garden_id])
    total = base["families_total"]
    informadas = sum(1 for f in snap.familias_por_jardin[garden_id] if f in conversadas)
    base["families_informed"] = informadas
    base["informed_percentage"] = round(100 * informadas / total, 1) if total else None
    return base


def paginar(
    snap: MotorSnapshot, items: list, limit: int, cursor: str | None
) -> tuple[list, str | None]:
    """Página por cursor opaco ``<snapshot_id>:<huella>:<offset>`` (DEC-051).

    La huella identifica la DB, el manifest y su ``files[]`` con que se armó el
    snapshot: un cursor emitido antes de regenerar la DB (o editar ``content/``)
    no coincide y responde 422, en vez
    de duplicar o saltar ítems. Un cursor malformado, de otro snapshot o fuera
    de rango también responde 422.
    """
    offset = 0
    if cursor is not None:
        partes = cursor.split(":")
        if (
            len(partes) != 3
            or partes[0] != SNAPSHOT_ID
            or partes[1] != snap.huella
            or not _PATRON_CURSOR.match(partes[2])
        ):
            raise ApiError(status_code=422)
        offset = int(partes[2])
        if not 0 < offset < len(items):
            raise ApiError(status_code=422)
    fin = offset + limit
    siguiente = f"{SNAPSHOT_ID}:{snap.huella}:{fin}" if fin < len(items) else None
    return items[offset:fin], siguiente


# --- construcción ------------------------------------------------------------


def _conectar_solo_lectura(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@dataclass(frozen=True)
class _Precalculo:
    fecha: str
    familias: list[tuple[str, str]]          # (family_id, garden_id)
    beneficios: list[str]
    periodicidad: dict[str, str | None]       # id_version -> periodicidad
    evaluaciones: dict[tuple[str, str], sqlite3.Row]
    accesos: dict[tuple[str, str], sqlite3.Row]
    jardines: list[sqlite3.Row]


def _leer_precalculo(conn: sqlite3.Connection) -> _Precalculo:
    tablas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not _TABLAS_REQUERIDAS <= tablas:
        raise _PrecalculoAusente
    familias = [
        (r["id_familia"], r["id_jardin"])
        for r in conn.execute("SELECT id_familia, id_jardin FROM familias ORDER BY id_familia")
    ]
    beneficios = [
        r[0] for r in conn.execute("SELECT id_beneficio FROM beneficios ORDER BY id_beneficio")
    ]
    esperado = len(familias) * len(beneficios)
    n_eval = conn.execute("SELECT COUNT(*) FROM evaluaciones").fetchone()[0]
    n_acc = conn.execute("SELECT COUNT(*) FROM accesos").fetchone()[0]
    if not esperado or n_eval != esperado or n_acc != esperado:
        raise _PrecalculoAusente
    fechas = [r[0] for r in conn.execute("SELECT DISTINCT fecha_evaluacion FROM evaluaciones")]
    if len(fechas) != 1 or not fechas[0]:
        raise _PrecalculoAusente
    periodicidad = {
        r["id_version"]: r["periodicidad"]
        for r in conn.execute("SELECT id_version, periodicidad FROM beneficios_versiones")
    }
    evaluaciones = {
        (r["id_familia"], r["id_beneficio"]): r
        for r in conn.execute(
            "SELECT id_familia, id_beneficio, id_version, resultado, nivel, monto_estimado, "
            "datos_faltantes, traza_json FROM evaluaciones"
        )
    }
    accesos = {
        (r["id_familia"], r["id_beneficio"]): r
        for r in conn.execute(
            "SELECT id_familia, id_beneficio, estado, requiere_accion_familia FROM accesos"
        )
    }
    jardines = conn.execute(
        "SELECT j.id_jardin, j.id_comuna, j.tipo_zona, c.region_codigo "
        "FROM jardines j LEFT JOIN comunas c ON c.id_comuna = j.id_comuna "
        "ORDER BY j.id_jardin"
    ).fetchall()
    return _Precalculo(
        fecha=fechas[0], familias=familias, beneficios=beneficios,
        periodicidad=periodicidad, evaluaciones=evaluaciones, accesos=accesos,
        jardines=jardines,
    )


def _id_c3(valor) -> str:
    if not isinstance(valor, str) or len(valor) > _MAX_ID or not _PATRON_ID.match(valor):
        raise ValueError("ID fuera del patrón de C3")
    return valor


def _codigos_faltantes(raw: str | None) -> list[str]:
    """``datos_faltantes`` del motor (vocabulario C1) sin duplicados, hasta 20."""
    codigos: list[str] = []
    for codigo in json.loads(raw or "[]"):
        if (
            not isinstance(codigo, str)
            or len(codigo) > _MAX_CODIGO
            or not _PATRON_CODIGO.match(codigo)
        ):
            raise ValueError("missing_code fuera del patrón de C3")
        if codigo not in codigos:
            codigos.append(codigo)
    return codigos[:_MAX_CODIGOS]


def _traza(raw: str | None) -> list[dict]:
    """Traza C1 -> ``TraceItem`` de C3 por allowlist (sin observado/integrante)."""
    items: list[dict] = []
    for t in json.loads(raw or "[]")[:_MAX_TRAZA]:
        campo = t["campo"]
        if not isinstance(campo, str) or len(campo) > _MAX_CAMPO or not _PATRON_CODIGO.match(campo):
            raise ValueError("campo de traza fuera del patrón de C3")
        if t["operador"] not in _OPERADORES_C3:
            raise ValueError("operador de traza fuera de C3")
        resultado = _RESULTADO_TRAZA.get(t["resultado"])
        if resultado is None:
            raise ValueError("resultado de traza fuera de C3")
        items.append({
            "rule_id": _id_c3(t["id_regla"]),
            "field": campo,
            "operator": t["operador"],
            "result": resultado,
        })
    return items


def _composicion(integrantes: list[dict]) -> tuple[list[dict], bool]:
    """Roles C2 -> enum C3; omite edades ausentes o fuera de rango."""
    composicion: list[dict] = []
    omitido = False
    for m in integrantes:
        edad = m.get("edad")
        if isinstance(edad, bool) or not isinstance(edad, int) or not _EDAD_MIN <= edad <= _EDAD_MAX:
            omitido = True
            continue
        if m.get("rol") == _ROL_REFERENCIA:
            rol = "ADULT_REFERENCE"
        elif edad < _EDAD_MAYORIA:
            rol = "CHILD"
        else:
            rol = "OTHER_ADULT"
        composicion.append({"role": rol, "age": edad})
    return composicion[:_MAX_CODIGOS], omitido or len(composicion) > _MAX_CODIGOS


def _bool_o_none(valor) -> bool | None:
    return valor if isinstance(valor, bool) else None


def _contexto_c3(
    family_id: str, c2: dict, cfg: RankingConfig
) -> tuple[dict, UrgencySignals, VulnerabilitySignals]:
    """``FamilyContextView`` + señales del ranking desde C2 (DEC-049)."""
    composicion, omitido = _composicion(c2["composicion"])
    no_informado = set(c2["no_informado"])

    tramo = c2["rsh"]["tramo"]
    rsh_band = tramo if isinstance(tramo, int) and tramo in _TRAMOS_RSH else None
    # RSH desconocido (no_informado) no es "sin RSH": no se usa no_rsh.
    has_rsh = None if "tramo_rsh" in no_informado else _bool_o_none(c2["rsh"]["tiene"])
    income_band = _INGRESO_C3.get(c2["ingreso_per_capita_rango"])
    formato = _FORMATO_C3.get(c2["formato_preferido"])
    if formato is None:
        raise ValueError("formato_preferido sin mapeo a C3")
    idioma = c2["idioma_mensaje"]
    if not isinstance(idioma, str) or not _PATRON_IDIOMA.match(idioma):
        raise ValueError("idioma fuera del patrón de C3")

    v = cfg.vulnerability
    if rsh_band is not None:
        rsh_score = v["rsh_scores"].get(f"band_{rsh_band}")
    elif has_rsh is False:
        rsh_score = v["rsh_scores"].get("no_rsh")
    else:
        rsh_score = None
    income_score = v["income_band_scores"].get(income_band) if income_band else None
    discapacidad = _bool_o_none(c2["posible_discapacidad_nino"])

    urgencia = c2["senales_urgencia"]
    emergencia = _bool_o_none(urgencia["evento_emergencia"])
    indice = urgencia["inseguridad_alimentaria"]
    if isinstance(indice, (int, float)) and not isinstance(indice, bool):
        inseguridad = indice >= cfg.urgency["food_insecurity"]["minimum_index"]
    else:
        inseguridad = None

    faltantes = {_NO_INFORMADO_C3[k] for k in no_informado if k in _NO_INFORMADO_C3}
    if income_band is None:
        faltantes.add("income_band")
    if omitido:
        faltantes.add("composition")

    vista = {
        "family_id": family_id,
        "composition": composicion,
        "rsh_band": rsh_band,
        "income_band": income_band,
        "preferred_format": formato,
        "language": idioma,
        "urgency_signals": {
            "recent_emergency": emergencia,
            "limited_quota": None,
            "precarious_housing": None,
        },
        "vulnerability_signals": {
            "rsh_score": rsh_score,
            "income_score": income_score,
            "possible_child_disability": discapacidad,
        },
        # Las inconsistencias de C2 no mapean limpio al enum cerrado (DEC-049).
        "inconsistency_codes": [],
        "missing_codes": sorted(faltantes),
    }
    senales_u = UrgencySignals(recent_emergency=emergencia, food_insecure=inseguridad)
    senales_v = VulnerabilitySignals(
        rsh_band=rsh_band,
        has_rsh=has_rsh,
        income_band=income_band,
        possible_child_disability=discapacidad,
    )
    return vista, senales_u, senales_v


def _accion(estado: str, requiere_accion_familia: bool) -> str:
    if estado == "ELEGIBLE_SIN_ASIGNACION":
        return "FAMILY_ACTION" if requiere_accion_familia else "AUTOMATIC"
    return _ACCION_POR_ESTADO[estado]


def _preguntas_resolubles(codigos: list[str], contenido: ContenidoC4) -> int:
    """Preguntas distintas de ``preguntas.yaml`` que cubren estos faltantes."""
    return len({contenido.preguntas[c] for c in codigos if c in contenido.preguntas})


def _preguntas(codigos: list[str], contenido: ContenidoC4) -> list[str]:
    preguntas: list[str] = []
    for codigo in codigos:
        texto = contenido.preguntas.get(codigo)
        if texto is not None and texto not in preguntas:
            preguntas.append(texto)
    return preguntas[:_MAX_PREGUNTAS]


def _semaforo(opps: list[dict]) -> str:
    colores = {SEMAFORO[EstadoAcceso(o["access_state"])] for o in opps}
    for color, c3 in _SEMAFORO_C3:
        if color in colores:
            return c3
    return "SIN_OPORTUNIDADES"


def _familia(
    family_id: str,
    garden_id: str,
    datos: _Precalculo,
    c2: dict,
    contenido: ContenidoC4,
) -> tuple[dict, tuple[float, float], dict[str, tuple[str, ...]]]:
    cfg = contenido.ranking
    vista_ctx, senales_u, senales_v = _contexto_c3(family_id, c2, cfg)

    benefit_results: list[dict] = []
    entradas: list[BenefitInput] = []
    extra: dict[str, tuple] = {}
    for bid in datos.beneficios:
        ev = datos.evaluaciones[(family_id, bid)]
        ac = datos.accesos[(family_id, bid)]
        resultado, nivel, estado = ev["resultado"], ev["nivel"], ac["estado"]
        validar_benefit_result(resultado, nivel, estado)
        faltantes = _codigos_faltantes(ev["datos_faltantes"])
        benefit_results.append({
            "benefit_id": _id_c3(bid),
            "result": resultado,
            "level": nivel,
            "access_state": estado,
            "missing_codes": faltantes,
            "trace": _traza(ev["traza_json"]),
        })
        if resultado not in ("SI", "INDETERMINADO"):
            continue
        validar_opportunity(resultado, nivel, estado)
        catalogo = contenido.beneficios.get(bid)
        if catalogo is None:
            raise ConfigInvalida("Catálogo C4 sin un beneficio del motor")
        if catalogo.official_url is None:
            continue  # DEC-050: sin cita HTTPS no hay Opportunity.
        requiere = bool(ac["requiere_accion_familia"])
        extra[bid] = (catalogo, faltantes, requiere)
        entradas.append(BenefitInput(
            benefit_id=bid,
            result=Tri(resultado),
            level=Nivel(nivel) if nivel else None,
            access_state=EstadoAcceso(estado),
            monto=ev["monto_estimado"],
            periodicidad=datos.periodicidad.get(ev["id_version"]),
            requiere_accion_familia=requiere,
            # Solo preguntas distintas que C4 sabe hacer: DATO_ADMINISTRATIVO y
            # NO_SE_PREGUNTA_A_LA_FAMILIA no son resolubles con una pregunta.
            resolvable_question_count=_preguntas_resolubles(faltantes, contenido),
        ))

    por_score = score_opportunities(entradas, senales_u, senales_v, cfg, garden_id=garden_id)
    pendiente = family_priority_score(por_score, cfg, conversada=False)
    conversada = family_priority_score(por_score, cfg, conversada=True)
    ordenadas = ordenar_por_grupo_accion(por_score)

    opps: list[dict] = []
    for s in ordenadas:
        catalogo, faltantes, requiere = extra[s.benefit_id]
        estado = s.access_state.value
        nivel = s.level.value if s.level is not None else None
        validar_opportunity(s.result.value, nivel, estado)
        opps.append({
            "benefit_id": s.benefit_id,
            "simple_title": catalogo.simple_title,
            "result": s.result.value,
            "level": nivel,
            "access_state": estado,
            "urgency": s.urgency,
            "benefit": s.benefit,
            "vulnerability": s.vulnerability,
            "score": s.score,
            "position": s.position,
            "estimated_annual_amount": s.estimated_annual_amount,
            # DEC-050: sin monto anual, B queda en 0 y se marca como estimado.
            "benefit_estimated": s.benefit_estimated or s.estimated_annual_amount is None,
            "action_type": _accion(estado, requiere),
            "why_first": _WHY_FIRST[estado],
            "missing_codes": list(faltantes),
            "suggested_questions": _preguntas(faltantes, contenido),
            "where_to_go": catalogo.where_to_go,
            "sources": [{
                "source_id": catalogo.official_source_id,
                "url": catalogo.official_url,
            }],
        })

    familia = {
        "summary": {
            "family_id": family_id,
            "priority_score": pendiente.priority_score,
            "vulnerability": pendiente.vulnerability,
            "opportunity_count": len(opps),
            "conversation_status": "PENDIENTE",
            "traffic_light": _semaforo(opps),
            "top_benefit_ids": [o["benefit_id"] for o in opps[:_MAX_TOP]],
        },
        "garden_id": garden_id,
        "composition": copy.deepcopy(vista_ctx["composition"]),
        "rsh_band": vista_ctx["rsh_band"],
        "informed": False,
        "benefit_results": benefit_results,
        "opportunities": opps,
        "context": vista_ctx,
    }
    ordenes = {
        orden: tuple(o.benefit_id for o in ordenar_vista(ordenadas, orden)) for orden in ORDENES
    }
    return familia, (pendiente.priority_score, conversada.priority_score), ordenes


def _construir(db: Path, contenido: ContenidoC4, huella: str) -> MotorSnapshot:
    inicio = time.perf_counter()
    conn = _conectar_solo_lectura(db)
    try:
        datos = _leer_precalculo(conn)
        contenido = territorial.con_overlay(contenido, datos.beneficios)  # B2 solo demo
        constructor = ContextoBuilder(conn, datos.fecha)
        familias: dict[str, dict] = {}
        prioridades: dict[str, tuple[float, float]] = {}
        ordenes: dict[str, dict[str, tuple[str, ...]]] = {}
        por_jardin: dict[str, list[str]] = {}
        for family_id, garden_id in datos.familias:
            _id_c3(family_id)
            _id_c3(garden_id)
            c2 = constructor.build(family_id)
            if c2 is None:
                raise ValueError("familia sin contexto C2")
            familias[family_id], prioridades[family_id], ordenes[family_id] = _familia(
                family_id, garden_id, datos, c2, contenido
            )
            por_jardin.setdefault(garden_id, []).append(family_id)
    finally:
        conn.close()

    jardines: dict[str, dict] = {}
    for r in datos.jardines:
        if r["tipo_zona"] not in _ZONAS:
            raise ValueError("zona de jardín fuera de C3")
        gid = _id_c3(r["id_jardin"])
        jardines[gid] = {
            "garden_id": gid,
            "commune_id": _id_c3(r["id_comuna"]),
            "region_id": _id_c3(r["region_codigo"]),
            "zone": r["tipo_zona"],
            "families_total": len(por_jardin.get(gid, ())),
        }
    if not set(por_jardin) <= set(jardines):
        raise ValueError("familia con jardín inexistente")

    familias_por_jardin = {
        gid: tuple(sorted(por_jardin.get(gid, []), key=lambda f: (-prioridades[f][0], f)))
        for gid in jardines
    }
    return MotorSnapshot(
        familias=familias,
        prioridades=prioridades,
        ordenes=ordenes,
        jardines=jardines,
        orden_jardines=tuple(sorted(jardines)),
        familias_por_jardin=familias_por_jardin,
        content_version=contenido.content_version,
        content_bundle_hash=contenido.content_bundle_hash,
        segundos_build=time.perf_counter() - inicio,
        huella=huella,
    )


# --- reevaluación en vivo de UNA familia con hechos declarados (B2) -----------
# El flujo normal sirve un snapshot inmutable precalculado. Cuando la familia
# declara un dato (``POST /familias/{id}/antecedentes``) hay que recalcular SOLO
# esa familia incorporando el dato. Se reusa ``_familia`` (la misma maquinaria
# del batch) sustituyendo las filas de ``evaluaciones`` de esa familia por el
# resultado reevaluado del motor. Los ``accesos`` se preservan del precálculo
# salvo en los beneficios cuyo (resultado, nivel) cambió: ahí se recalculan en
# memoria con las gestiones de la base (DEC-082). Nada se escribe en la DB.


def _fila_evaluacion_declarada(res, periodicidad: dict[str, str | None]) -> dict:
    """``ResultadoBeneficio`` reevaluado -> fila con la forma que lee ``_familia``.

    ``_familia`` consume la evaluación como un ``sqlite3.Row`` (acceso por clave);
    un dict sirve igual. Se serializan ``datos_faltantes`` y la traza a JSON,
    exactamente como vienen de la tabla ``evaluaciones`` del precálculo.
    """
    d = res.to_dict()
    traza = [
        {
            "id_regla": t["id_regla"],
            "campo": t["campo"],
            "operador": t["operador"],
            "resultado": t["resultado"],
        }
        for t in d["traza"]
    ]
    return {
        "id_familia": d["id_familia"],
        "id_beneficio": d["id_beneficio"],
        "id_version": d["id_version"],
        "resultado": d["resultado"],
        "nivel": d["nivel"],
        "monto_estimado": d["monto_estimado"],
        "datos_faltantes": json.dumps(d["datos_faltantes"]),
        "traza_json": json.dumps(traza),
    }


def reconstruir_familia_declarada(family_id: str, campos: dict) -> dict | None:
    """Ficha C3 (``FamiliaDetailEnvelope.data``) de una familia reevaluada en vivo.

    Lee la DB real (solo lectura), traduce los campos declarados por la familia
    (``campos``: el cuerpo de la pantalla sin ``data_classification``) a hechos
    del motor, reevalúa los beneficios de ``family_id`` incorporándolos y
    reconstruye su vista C3 con la misma maquinaria del snapshot. ``None`` si no
    se puede operar sobre el motor real (sin DB/precálculo/C4 válidos): el
    llamador decide el fallback.

    Si ``campos`` no aporta ningún dato que el motor pueda usar, se reevalúa sin
    ``declarados``: la ficha sale del motor igual, sin cambios por declaración.
    Los beneficios cuyo resultado o nivel cambió recalculan su acceso en memoria
    (``AccesoService.estado_reevaluado``, DEC-082). No muta el snapshot cacheado
    ni la DB. Un dato declarado nunca da CONFIRMADO (lo garantiza el motor), así
    que la ficha resultante respeta las invariantes.
    """
    reevaluada = _reconstruir(family_id, campos)
    return None if reevaluada is None else reevaluada[0]


def _contexto_declarado(ctx: dict, campos: dict) -> dict:
    """Vista de contexto coherente con lo declarado (copia).

    C2 sale de la DB y no conoce lo declarado: un campo declarado con valor
    conocido deja de figurar en ``missing_codes`` (enum cerrado de C3). Un
    "No sé" no llega en ``campos`` y sigue faltando. ``rsh_band`` e
    ``income_band`` se reflejan tal cual, igual que ``aplicar_declarados``.
    """
    from app.api.models_antecedentes import CAMPO_A_MISSING_CODE

    ctx = copy.deepcopy(ctx)
    conocidos = {CAMPO_A_MISSING_CODE[c] for c in campos if c in CAMPO_A_MISSING_CODE}
    ctx["missing_codes"] = sorted(set(ctx["missing_codes"]) - conocidos)
    if "rsh_band" in campos:
        ctx["rsh_band"] = campos["rsh_band"]
    if "household_income_band" in campos:
        ctx["income_band"] = campos["household_income_band"]
    return ctx


def _reconstruir(
    family_id: str, campos: dict
) -> tuple[dict, tuple[float, float], dict[str, tuple[str, ...]]] | None:
    """(familia, prioridades, órdenes) reevaluados con ``campos``, o ``None``.

    Núcleo de ``reconstruir_familia_declarada`` (POST) y de ``_vigente`` (GET):
    la misma reevaluación para ambos caminos.
    """
    # Imports locales: evitan un ciclo con engine.service y aíslan el puente B2.
    from app.access.service import AccesoService
    from app.api.antecedentes_motor import declarados_para_motor
    from app.engine.service import evaluar_familia

    db = Path(runtime.DB_PATH)
    manifest = Path(content_c4.CONTENT_MANIFEST)
    if _estado_archivo(db) is None or _estado_archivo(manifest) is None:
        return None
    try:
        contenido = cargar_contenido_c4(manifest)
    except ConfigInvalida:
        return None

    conn = _conectar_solo_lectura(db)
    try:
        try:
            datos = _leer_precalculo(conn)
        except (_PrecalculoAusente, sqlite3.Error):
            return None
        garden_id = dict(datos.familias).get(family_id)
        if garden_id is None:
            return None

        declarados = declarados_para_motor(conn, family_id, campos, datos.fecha)
        contenido = territorial.con_overlay(contenido, datos.beneficios)
        resultados = evaluar_familia(family_id, conn=conn, fecha=datos.fecha,
                                     declarados=declarados or None)

        # Sustituye SOLO las evaluaciones de esta familia. El acceso se recalcula
        # en memoria solo para los beneficios cuyo (resultado, nivel) cambió
        # (DEC-082: SI sin gestión -> ELEGIBLE_SIN_ASIGNACION); los demás
        # conservan su fila de ``accesos`` del precálculo.
        evaluaciones = dict(datos.evaluaciones)
        accesos = dict(datos.accesos)
        servicio_acceso = None
        for res in resultados:
            clave = (family_id, res.id_beneficio)
            fila = _fila_evaluacion_declarada(res, datos.periodicidad)
            previa = datos.evaluaciones.get(clave)
            if previa is None or (previa["resultado"], previa["nivel"]) != (
                    fila["resultado"], fila["nivel"]):
                if servicio_acceso is None:
                    servicio_acceso = AccesoService(conn, datos.fecha)
                estado, requiere = servicio_acceso.estado_reevaluado(family_id, res)
                accesos[clave] = {
                    "id_familia": family_id,
                    "id_beneficio": res.id_beneficio,
                    "estado": estado.value,
                    "requiere_accion_familia": int(requiere),
                }
            evaluaciones[clave] = fila
        datos_mod = replace(datos, evaluaciones=evaluaciones, accesos=accesos)

        c2 = ContextoBuilder(conn, datos.fecha).build(family_id)
        if c2 is None:
            return None
        try:
            familia, prioridades, ordenes = _familia(
                family_id, garden_id, datos_mod, c2, contenido)
        except (ValueError, KeyError, TypeError, ConfigInvalida):
            # Combinación incoherente: no se emite una ficha dudosa.
            return None
        familia["context"] = _contexto_declarado(familia["context"], campos)
        if "rsh_band" in campos:
            familia["rsh_band"] = familia["context"]["rsh_band"]
        return familia, prioridades, ordenes
    finally:
        conn.close()


def umbral_semanas_gestacion() -> int | None:
    """N de la pregunta de semanas de gestación (parámetro ``P006-02`` vía R00301).

    Lee ``runtime.DB_PATH`` en solo lectura con la fecha única de
    ``evaluaciones`` (o ``config.FECHA_EVALUACION`` si no hay precálculo), en
    ambos modos ``E3_MOCK``. ``None`` si no se puede leer (falla cerrada).
    """
    from app.api.antecedentes_motor import umbral_semanas_gestacion as _umbral
    from app.config import FECHA_EVALUACION

    db = Path(runtime.DB_PATH)
    if _estado_archivo(db) is None:
        return None
    try:
        conn = _conectar_solo_lectura(db)
    except sqlite3.Error:
        return None
    try:
        fecha = FECHA_EVALUACION
        try:
            fechas = [r[0] for r in conn.execute(
                "SELECT DISTINCT fecha_evaluacion FROM evaluaciones")]
            if len(fechas) == 1 and fechas[0]:
                fecha = fechas[0]
        except sqlite3.Error:
            pass  # sin precálculo: fecha de configuración
        return _umbral(conn, fecha)
    except sqlite3.Error:
        return None
    finally:
        conn.close()
