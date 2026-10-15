"""Alcance territorial y overlay del beneficio SOLO DEMO (B2, DEC-071/DEC-072).

- ``con_overlay``/``catalogo_texto``: si la DB local trae ``BEN-DEMO-LOCAL-01``
  (cargado con ``app.demo_territorial.cargar``), le dan título, dónde ir y
  texto de catálogo, sin fuente ni URL. Si ``content/`` ya lo trae, manda
  ``content/``. Sin el ID en la DB no cambian nada.
- ``alcance``: marca cada beneficio de la DB como ``LOCAL`` (todas sus
  alternativas de la versión vigente restringen ``comuna_residencia`` a una
  lista que no cubre todas las comunas) o ``NACIONAL``. Solo lee reglas: la
  elegibilidad de cada familia la decide el motor del Rol 1.

Las respuestas nunca llevan IDs ni nombres de comuna.
"""
from __future__ import annotations

import dataclasses
import json
import sqlite3
import threading
from pathlib import Path

from app.api import mock_data
from app.api.deps import mock_habilitado
from app.demo_territorial import DEMO_BENEFIT_ID, demo_cargado
from app.engine.evaluator import Evaluator
from app.engine.facts import Repo
from app.genai.content_catalog import CatalogoContenido
from app.genai.template_provider import CatalogEntry
from app.priority.content_c4 import BeneficioC4, ContenidoC4, cargar_contenido_c4

DEMO_TITULO = "Programa Municipal Sintético de Apoyo Familiar (solo demo)"
DEMO_DONDE_IR = "Municipalidad de su comuna (solo demo)"
DEMO_DESCRIPCION = (
    "SOLO DEMO. Beneficio inventado para mostrar un apoyo que existe solo en una "
    "comuna. No es un beneficio real."
)
DEMO_INSTITUCION = "Municipalidad Sintética (solo demo)"

LOCAL = "LOCAL"
NACIONAL = "NACIONAL"

_CAMPO_COMUNA = "comuna_residencia"


# --- overlay de presentación y texto -----------------------------------------


def con_overlay(contenido: ContenidoC4, beneficios_db) -> ContenidoC4:
    """Agrega la presentación C4 del ejemplo demo si la DB lo trae y content/ no."""
    if DEMO_BENEFIT_ID not in beneficios_db or DEMO_BENEFIT_ID in contenido.beneficios:
        return contenido
    beneficios = dict(contenido.beneficios)
    beneficios[DEMO_BENEFIT_ID] = BeneficioC4(
        benefit_id=DEMO_BENEFIT_ID,
        simple_title=DEMO_TITULO,
        where_to_go=DEMO_DONDE_IR,
        official_source_id=None,
        official_url=None,
    )
    return dataclasses.replace(contenido, beneficios=beneficios)


def catalogo_texto(cat: CatalogoContenido, db_path) -> CatalogoContenido:
    """Agrega la entrada de texto del ejemplo demo (modo real y DB con el ID)."""
    if mock_habilitado() or DEMO_BENEFIT_ID in cat.entradas or not demo_cargado(db_path):
        return cat
    entradas = dict(cat.entradas)
    entradas[DEMO_BENEFIT_ID] = CatalogEntry(
        benefit_id=DEMO_BENEFIT_ID,
        title=DEMO_TITULO,
        description=DEMO_DESCRIPCION,
        institution=DEMO_INSTITUCION,
        where_to_go=DEMO_DONDE_IR,
        source_id="",
        source_url="",
    )
    return dataclasses.replace(cat, entradas=entradas)


# --- alcance -----------------------------------------------------------------

_LOCK = threading.Lock()
_CACHE: tuple[tuple, list[dict]] | None = None


def _estado(path: Path) -> tuple[str, int, int] | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return str(path.resolve()), st.st_mtime_ns, st.st_size


def _lista_comunas(conn: sqlite3.Connection, regla: sqlite3.Row) -> list | None:
    if regla["id_parametro_version"]:
        fila = conn.execute(
            "SELECT valor_texto FROM parametros_version WHERE id_parametro = ?",
            (regla["id_parametro_version"],),
        ).fetchone()
        crudo = fila["valor_texto"] if fila is not None else None
    else:
        crudo = regla["valor_literal"]
    try:
        valor = json.loads(crudo) if crudo else None
    except (TypeError, ValueError):
        return None
    return valor if isinstance(valor, list) else None


def _es_local(conn: sqlite3.Connection, ev: Evaluator, bid: str, comunas: set) -> bool:
    version = ev.version_vigente(bid)
    if version is None:
        return False
    grupos: dict[str, bool] = {}
    for regla in conn.execute(
        "SELECT * FROM reglas_elegibilidad WHERE id_version = ? ORDER BY grupo_or, orden",
        (version["id_version"],),
    ):
        restringe = False
        if (
            Repo._vig(regla["vigencia_desde"], regla["vigencia_hasta"], ev.fecha)
            and regla["campo_dato"] == _CAMPO_COMUNA
            and regla["operador"] == "IN"
        ):
            lista = _lista_comunas(conn, regla)
            restringe = lista is not None and not comunas <= set(lista)
        grupos[regla["grupo_or"]] = grupos.get(regla["grupo_or"], False) or restringe
    return bool(grupos) and all(grupos.values())


def _calcular(db_path: Path, manifest_path: Path) -> list[dict]:
    conn = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        fecha = conn.execute("SELECT MIN(fecha_evaluacion) FROM evaluaciones").fetchone()[0]
        beneficios = [
            r[0] for r in conn.execute("SELECT id_beneficio FROM beneficios ORDER BY id_beneficio")
        ]
        comunas = {r[0] for r in conn.execute("SELECT id_comuna FROM comunas")}
        ev = Evaluator(conn, fecha)
        contenido = con_overlay(cargar_contenido_c4(manifest_path), beneficios)
        items = []
        for bid in beneficios:
            presentacion = contenido.beneficios.get(bid)
            if presentacion is None:
                raise KeyError("beneficio sin presentación C4")
            items.append({
                "benefit_id": bid,
                "scope": LOCAL if _es_local(conn, ev, bid, comunas) else NACIONAL,
                "simple_title": presentacion.simple_title,
                "demo": bid == DEMO_BENEFIT_ID,
            })
        return items
    finally:
        conn.close()


def alcance(db_path, manifest_path) -> list[dict]:
    """Alcance por beneficio de la DB (copias). Cacheado por ruta, mtime y tamaño.

    Lanza ``sqlite3.Error``, ``ConfigInvalida`` o ``KeyError``; el router responde 503.
    """
    global _CACHE
    db, manifest = Path(db_path), Path(manifest_path)
    clave = (_estado(db), _estado(manifest))
    with _LOCK:
        if _CACHE is None or _CACHE[0] != clave:
            _CACHE = (clave, _calcular(db, manifest))
        return [dict(i) for i in _CACHE[1]]


def alcance_mock() -> list[dict]:
    """Alcance de los beneficios de los mocks: todos NACIONAL, ninguno demo."""
    titulos: dict[str, str] = {}
    for fam in mock_data.FAMILIAS.values():
        for o in fam["opportunities"]:
            titulos.setdefault(o["benefit_id"], o["simple_title"])
        for b in fam["benefit_results"]:
            titulos.setdefault(b["benefit_id"], b["benefit_id"])
    return [
        {"benefit_id": bid, "scope": NACIONAL, "simple_title": titulos[bid], "demo": False}
        for bid in sorted(titulos)
    ]
