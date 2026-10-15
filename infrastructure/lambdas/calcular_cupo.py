"""ESBOZO — Lee el cupo contingente de la versión vigente de BEN-018.

Stage previo al reduce `cupo_ben018.py`. Replica exactamente
`AccesoService._cupo_ben018()` del backend: lee `cupo_contingente` de la versión
vigente de BEN-018, con fallback a 75. Lo pasa como `$.cupo` al reduce.

Se mantiene separado del reduce para que el número de cupo sea explícito en el
historial de la state machine (trazable) y configurable sin tocar el ranking.

Entrada:  { "snapshot_id": "...", "fecha_evaluacion": "..."? }
Salida:   { "snapshot_id": "...", "cupo": 75 }
"""
from __future__ import annotations

import os
import sqlite3

# Reutiliza el Evaluator del backend (version_vigente ya resuelve vigencia).
from app.access.service import BEN_CUPO, CUPO_BEN018_DEFAULT
from app.engine.evaluator import Evaluator

DB_PATH = os.environ.get("E3_DB_PATH", "/opt/e3.db")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def _cupo_vigente(conn: sqlite3.Connection, fecha: str | None) -> int:
    ev = Evaluator(conn, fecha) if fecha else Evaluator(conn, _fecha_default())
    version = ev.version_vigente(BEN_CUPO)
    if version is not None:
        raw = version["cupo_contingente"]
        try:
            if raw not in (None, ""):
                return int(raw)
        except (ValueError, TypeError):
            pass
    return CUPO_BEN018_DEFAULT


def _fecha_default() -> str:
    from app.config import FECHA_EVALUACION
    return FECHA_EVALUACION


def handler(event: dict, _context=None) -> dict:
    snapshot_id = event["snapshot_id"]
    fecha = event.get("fecha_evaluacion")
    conn = _conn()
    try:
        cupo = _cupo_vigente(conn, fecha)
    finally:
        conn.close()
    return {"snapshot_id": snapshot_id, "cupo": cupo}
