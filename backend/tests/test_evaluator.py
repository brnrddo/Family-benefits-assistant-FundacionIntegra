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


# --- monto por tramo (RANGE_LOOKUP): BEN-016 ---------------------------------

def test_range_lookup_fija_monto_del_tramo(ev):
    """BEN-016 usa RANGE_LOOKUP sobre el ingreso: cuando da SI, el monto estimado
    debe ser el del tramo que cumple (no None ni el referencial de la versión).

    La versión vigente (V033) define los tramos
    ``(0,360000]:26000;(360000,510000]:16000;(510000,660000]:6000``.
    """
    fam = ev.conn.execute(
        "SELECT id_familia FROM familias ORDER BY id_familia LIMIT 1").fetchone()
    r = ev.evaluar(fam[0], "BEN-016")
    assert r.resultado == Tri.SI
    # Debe venir de un tramo real del RANGE_LOOKUP vigente, nunca None.
    assert r.monto_estimado in (26000, 16000, 6000)


def test_range_lookup_monto_coincide_con_tramo_de_ingreso(ev):
    """El tramo elegido debe corresponder al ingreso_bruto del integrante."""
    # Toma una familia con un ingreso conocido para verificar el tramo exacto.
    row = ev.conn.execute(
        """SELECT ci.id_integrante, CAST(ci.valor_numero AS INTEGER) ingreso, i.id_familia
           FROM condiciones_integrante ci
           JOIN integrantes i ON i.id_integrante = ci.id_integrante
           WHERE ci.tipo_condicion='PREVISION' AND ci.subtipo='INGRESO_BRUTO'
             AND ci.valor_numero IS NOT NULL
           ORDER BY ci.id_integrante LIMIT 1"""
    ).fetchone()
    assert row is not None
    r = ev.evaluar(row["id_familia"], "BEN-016")
    if r.resultado == Tri.SI:
        ingreso = row["ingreso"]
        esperado = (26000 if ingreso <= 360000
                    else 16000 if ingreso <= 510000
                    else 6000 if ingreso <= 660000
                    else None)
        if esperado is not None:
            assert r.monto_estimado == esperado


# --- COUNT_REL_GTE end-to-end: BEN-017 (hijos_activos >= 1) ------------------

def test_count_rel_gte_cuenta_hijos_ben017(ev):
    """BEN-017 cuenta relaciones PROGENITOR_DE (hijos_activos >= 1).

    Una persona de referencia con al menos un hijo (PROGENITOR_DE) debe hacer
    que la regla COUNT_REL_GTE se resuelva (SI o NO según el resto), nunca
    quedando la cuenta en None para quien sí tiene hijos.
    """
    row = ev.conn.execute(
        """SELECT i.id_familia, i.id_integrante
           FROM relaciones_integrantes rel
           JOIN integrantes i ON i.id_integrante = rel.id_integrante_origen
           WHERE rel.tipo_relacion = 'PROGENITOR_DE'
           ORDER BY i.id_familia LIMIT 1"""
    ).fetchone()
    assert row is not None
    r = ev.evaluar(row["id_familia"], "BEN-017")
    # Debe existir traza del COUNT_REL_GTE y no quedar INDETERMINADO por "cuenta
    # desconocida" (la familia tiene al menos un hijo).
    cnt_trz = [t for t in r.traza if t.operador == "COUNT_REL_GTE"]
    assert cnt_trz, "falta traza COUNT_REL_GTE en BEN-017"
    assert all(t.resultado in (Tri.SI, Tri.NO) for t in cnt_trz), (
        f"COUNT_REL_GTE no debería ser IND con hijos presentes: "
        f"{[t.resultado for t in cnt_trz]}")
