"""Tests del evaluador de elegibilidad (M2) contra la DB real.

Expectativas verificadas con la traza del motor sobre el dataset E-3.
NO se compara contra el paquete interno de respuestas (no disponible); se validan
casos construidos y coherencia estructural (spec §12.3: no sobreajustar).
"""
from __future__ import annotations

import pytest

from app.engine.evaluator import Evaluator
from app.engine.model import Nivel, Tri


@pytest.fixture()
def ev(conn, fecha):
    return Evaluator(conn, fecha)


@pytest.fixture()
def fecha():
    from app.config import FECHA_EVALUACION
    return FECHA_EVALUACION


# --- selección de versión vigente --------------------------------------------

def test_version_vigente_ben001_es_v002(ev):
    v = ev.version_vigente("BEN-001")
    assert v is not None and v["id_version"] == "V002"


# --- SUF (BEN-001): brecha estrella, SI PRELIMINAR ---------------------------

def test_suf_familia_vulnerable_da_si_preliminar(ev):
    r = ev.evaluar("FAM-SIM-E3-00100", "BEN-001")
    assert r.resultado == Tri.SI
    assert r.nivel == Nivel.PRELIMINAR          # supuesto antecedente_edad
    assert r.monto_estimado == 22000            # V002
    # El causante ganador quedó registrado
    assert "CAUSANTE_1" in r.entidad_ganadora


def test_suf_tramo_alto_da_no(ev):
    """Alguna familia de tramo alto debe dar NO en SUF (criterio tramo_rsh)."""
    # Buscar una familia con tramo > 60.
    fam = ev.conn.execute(
        "SELECT id_familia FROM familias WHERE CAST(tramo_rsh_corte AS INTEGER) > 60 LIMIT 1"
    ).fetchone()
    assert fam is not None
    r = ev.evaluar(fam[0], "BEN-001")
    assert r.resultado == Tri.NO


def test_suf_sin_rsh_da_indeterminado(ev):
    """Familia sin tramo RSH -> INDETERMINADO (no NO) en SUF."""
    fam = ev.conn.execute(
        "SELECT id_familia FROM familias WHERE tramo_rsh_corte IS NULL OR tramo_rsh_corte='' LIMIT 1"
    ).fetchone()
    assert fam is not None
    r = ev.evaluar(fam[0], "BEN-001")
    assert r.resultado == Tri.INDETERMINADO


# --- discapacidad (BEN-006): binding "mismo niño", nivel CONFIRMADO ----------

def test_discapacidad_da_si_confirmado_y_binding(ev):
    fam = ev.conn.execute(
        """SELECT i.id_familia FROM condiciones_integrante ci
           JOIN integrantes i ON i.id_integrante = ci.id_integrante
           WHERE ci.tipo_condicion='DISCAPACIDAD' AND ci.valor_texto='SEVERA' LIMIT 1"""
    ).fetchone()
    assert fam is not None
    r = ev.evaluar(fam[0], "BEN-006")
    assert r.resultado == Tri.SI
    assert r.nivel == Nivel.CONFIRMADO          # dato acreditado real
    assert r.entidad_ganadora.get("CAUSANTE_1")  # el niño con discapacidad


def test_discapacidad_familia_sin_el_dato_da_indeterminado(ev):
    r = ev.evaluar("FAM-SIM-E3-00100", "BEN-006")
    assert r.resultado == Tri.INDETERMINADO
    assert "discapacidad_severidad" in r.datos_faltantes


# --- fuera de vigencia --------------------------------------------------------

def test_beneficio_inexistente_sin_version_da_no(ev):
    r = ev.evaluar("FAM-SIM-E3-00001", "BEN-999")
    assert r.resultado == Tri.NO
    assert r.id_version is None


# --- coherencia por "zonas" de arquetipo (spec §12.4) ------------------------

def test_coherencia_arquetipo_brecha_califica_suf(ev):
    """Las familias de la zona 'brecha' (~91-230) deben calificar a SUF."""
    aciertos = 0
    for n in range(91, 131):
        fam = f"FAM-SIM-E3-{n:05d}"
        if ev.evaluar(fam, "BEN-001").resultado == Tri.SI:
            aciertos += 1
    assert aciertos >= 30, f"Se esperaban muchas brechas de SUF, hubo {aciertos}/40"


def test_traza_presente_en_todo_resultado(ev):
    """Todo resultado debe traer traza regla-por-regla (explicabilidad)."""
    r = ev.evaluar("FAM-SIM-E3-00100", "BEN-001")
    assert len(r.traza) >= 1
    for t in r.traza:
        assert t.id_regla and t.campo and t.operador
