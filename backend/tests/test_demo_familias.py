"""3 familias demo verificadas (P3, plan Día 2 #8).

Fija tres familias REALES del dataset E-3, cada una ilustrando un arquetipo del
pitch, y asserta su comportamiento. Sirve de:
  - regresión: si el motor/acceso cambia y rompe un arquetipo, el test avisa.
  - guion de demo: estos ids son los que se muestran en vivo.

Arquetipos (elegidos para que sean claros y NO se solapen entre sí):
  - BRECHA         FAM-SIM-E3-00231 — varios ELEGIBLE_SIN_ASIGNACION (la brecha
                   estrella: califica confirmado y nunca lo pidió).
  - DISCAPACIDAD   FAM-SIM-E3-00361 — BEN-006 (subsidio discapacidad <18) SI
                   CONFIRMADO por binding de discapacidad severa vigente.
  - SIN_RSH        FAM-SIM-E3-00256 — SIN_REGISTRO: beneficios que dependen del
                   tramo RSH quedan INDETERMINADO (se vuelve pregunta, nunca NO).

Documentadas también en el README (sección de familias demo).
"""
from __future__ import annotations

import pytest

from app.access.service import AccesoService
from app.engine.evaluator import Evaluator
from app.engine.model import Nivel, Tri

FAM_BRECHA = "FAM-SIM-E3-00231"
FAM_DISCAPACIDAD = "FAM-SIM-E3-00361"
FAM_SIN_RSH = "FAM-SIM-E3-00256"

BEN_DISCAPACIDAD = "BEN-006"


@pytest.fixture()
def fecha():
    from app.config import FECHA_EVALUACION
    return FECHA_EVALUACION


@pytest.fixture()
def evaluar(conn, fecha):
    ev = Evaluator(conn, fecha)
    return lambda fam, ben: ev.evaluar(fam, ben)


@pytest.fixture()
def acceso(conn, fecha):
    svc = AccesoService(conn, fecha)
    return svc


def _bens(conn):
    return [r[0] for r in conn.execute(
        "SELECT id_beneficio FROM beneficios ORDER BY id_beneficio").fetchall()]


# --- Arquetipo BRECHA --------------------------------------------------------

def test_brecha_tiene_elegible_sin_asignacion(conn, acceso):
    """La familia brecha tiene al menos un ELEGIBLE_SIN_ASIGNACION (la brecha)."""
    estados = [acceso.evaluar(FAM_BRECHA, b).estado.value for b in _bens(conn)]
    n_brechas = sum(e == "ELEGIBLE_SIN_ASIGNACION" for e in estados)
    assert n_brechas >= 1, f"se esperaba ≥1 brecha, hubo {n_brechas}"


def test_brecha_es_si_confirmado_sin_gestion(conn, acceso, evaluar):
    """Una brecha concreta: SI CONFIRMADO y sin gestión previa."""
    brechas = [b for b in _bens(conn)
               if acceso.evaluar(FAM_BRECHA, b).estado.value == "ELEGIBLE_SIN_ASIGNACION"]
    assert brechas
    ben = brechas[0]
    r = evaluar(FAM_BRECHA, ben)
    assert r.resultado == Tri.SI
    assert r.nivel == Nivel.CONFIRMADO           # brecha pura = confirmado
    acc = acceso.evaluar(FAM_BRECHA, ben)
    assert acc.tiene_gestion is False


# --- Arquetipo DISCAPACIDAD --------------------------------------------------

def test_discapacidad_ben006_si_confirmado(evaluar):
    """BEN-006 da SI CONFIRMADO por el binding de discapacidad severa vigente."""
    r = evaluar(FAM_DISCAPACIDAD, BEN_DISCAPACIDAD)
    assert r.resultado == Tri.SI
    assert r.nivel == Nivel.CONFIRMADO
    # La traza debe apoyarse en el dato de discapacidad del mismo integrante.
    campos = {t.campo for t in r.traza}
    assert any("discapacidad" in str(c).lower() for c in campos), campos


# --- Arquetipo SIN RSH -------------------------------------------------------

def test_sin_rsh_es_indeterminado_no_no(conn, evaluar):
    """Sin RSH, los beneficios que piden tramo quedan IND (pregunta), nunca NO."""
    inds = [b for b in _bens(conn)
            if (r := evaluar(FAM_SIN_RSH, b)).resultado == Tri.INDETERMINADO
            and "tramo_rsh" in r.datos_faltantes]
    assert inds, "se esperaba ≥1 beneficio IND por tramo_rsh faltante"
    # Y el motivo debe señalar explícitamente el RSH faltante.
    r = evaluar(FAM_SIN_RSH, inds[0])
    assert "DATO_RSH_FALTANTE" in r.motivos


def test_sin_rsh_estado_registro(conn):
    """Confirma el supuesto del arquetipo: la familia no tiene RSH vigente."""
    row = conn.execute(
        "SELECT estado_rsh_corte, tramo_rsh_corte FROM familias WHERE id_familia = ?",
        (FAM_SIN_RSH,)).fetchone()
    assert row is not None
    assert row["estado_rsh_corte"] != "VIGENTE" or not row["tramo_rsh_corte"]


# --- Las tres existen y son distintas ----------------------------------------

def test_tres_familias_demo_existen_y_son_distintas(conn):
    ids = {FAM_BRECHA, FAM_DISCAPACIDAD, FAM_SIN_RSH}
    assert len(ids) == 3
    for fam in ids:
        row = conn.execute(
            "SELECT 1 FROM familias WHERE id_familia = ?", (fam,)).fetchone()
        assert row is not None, f"familia demo inexistente: {fam}"
