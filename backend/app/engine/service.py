"""Servicio de alto nivel del motor (M2): evaluar familia(s) completas."""
from __future__ import annotations

import sqlite3

from ..config import DB_PATH, FECHA_EVALUACION
from .evaluator import Evaluator
from .model import ResultadoBeneficio


def _conn(db_path=None) -> sqlite3.Connection:
    c = sqlite3.connect(str(db_path or DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def beneficios(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT id_beneficio FROM beneficios ORDER BY id_beneficio").fetchall()]


def evaluar_familia(id_familia: str, conn=None, fecha=FECHA_EVALUACION,
                    declarados: dict | None = None) -> list[ResultadoBeneficio]:
    """Evalúa los 20 beneficios para una familia (bajo demanda).

    ``declarados`` (opcional) inyecta hechos DECLARADO por la familia para
    desbloquear beneficios que de otro modo quedarían INDETERMINADO por un dato
    ausente. El resultado nunca será CONFIRMADO por un dato declarado.
    """
    propia = conn is None
    conn = conn or _conn()
    try:
        ev = Evaluator(conn, fecha)
        return [ev.evaluar(id_familia, b, declarados) for b in beneficios(conn)]
    finally:
        if propia:
            conn.close()


def reevaluar_con_declarados(id_familia: str, declarados: dict,
                             conn=None, fecha=FECHA_EVALUACION
                             ) -> list[ResultadoBeneficio]:
    """Reevalúa una familia incorporando hechos DECLARADO (P1).

    Azúcar sobre ``evaluar_familia`` que deja explícito el flujo de la ficha
    digital: la tía responde preguntas -> se arma ``declarados`` -> se reevalúa.
    """
    return evaluar_familia(id_familia, conn=conn, fecha=fecha, declarados=declarados)


def precalcular_todo(conn=None, fecha=FECHA_EVALUACION
                     ) -> dict[str, list[ResultadoBeneficio]]:
    """Envoltorio: evalúa las 500 familias x 20 beneficios."""
    propia = conn is None
    conn = conn or _conn()
    try:
        ev = Evaluator(conn, fecha)
        bens = beneficios(conn)
        familias = [r[0] for r in conn.execute(
            "SELECT id_familia FROM familias ORDER BY id_familia").fetchall()]
        return {fam: [ev.evaluar(fam, b) for b in bens] for fam in familias}
    finally:
        if propia:
            conn.close()
