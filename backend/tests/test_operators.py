"""Tests unitarios de los operadores atómicos (M2) — sin DB."""
from __future__ import annotations

from app.engine import operators as ops
from app.engine.model import Hecho, Tri


def test_eq_booleano_y_texto():
    assert ops.op_eq("false", "false") == Tri.SI
    assert ops.op_eq(False, "false") == Tri.SI
    assert ops.op_eq("ACTIVA", "ACTIVA") == Tri.SI
    assert ops.op_eq("ACTIVA", "INACTIVA") == Tri.NO
    assert ops.op_eq(None, "x") == Tri.INDETERMINADO


def test_comparadores_numericos():
    assert ops.op_lte(50, 60) == Tri.SI
    assert ops.op_lte(60, 60) == Tri.SI          # borde inclusivo
    assert ops.op_lt(60, 60) == Tri.NO           # borde exclusivo
    assert ops.op_gte(20, 20) == Tri.SI
    assert ops.op_gt(20, 20) == Tri.NO
    assert ops.op_lte(None, 60) == Tri.INDETERMINADO


def test_in_lista_json_y_escalar():
    assert ops.op_in("SEVERA", '["SEVERA"]') == Tri.SI
    assert ops.op_in("LEVE", '["SEVERA"]') == Tri.NO
    assert ops.op_in("COM-001", '["COM-001","COM-002"]') == Tri.SI
    assert ops.op_in(None, '["SEVERA"]') == Tri.INDETERMINADO


def test_between_intervalos_abiertos_cerrados():
    # [4,19): 4 incluido, 19 excluido
    assert ops.op_between(4, "[4,19)") == Tri.SI
    assert ops.op_between(18, "[4,19)") == Tri.SI
    assert ops.op_between(19, "[4,19)") == Tri.NO
    assert ops.op_between(3, "[4,19)") == Tri.NO
    assert ops.op_between(None, "[4,19)") == Tri.INDETERMINADO


def test_range_lookup_devuelve_monto():
    rl = "(0,300000]:22000;(300000,450000]:14000;(450000,600000]:5000"
    tri, monto = ops.op_range_lookup(250000, rl)
    assert tri == Tri.SI and monto == 22000
    tri, monto = ops.op_range_lookup(400000, rl)
    assert tri == Tri.SI and monto == 14000
    tri, monto = ops.op_range_lookup(700000, rl)
    assert tri == Tri.NO and monto is None
    tri, monto = ops.op_range_lookup(None, rl)
    assert tri == Tri.INDETERMINADO


def test_active_on_date():
    assert ops.op_active_on_date(Hecho("x", "ACTIVA", presente=True)) == Tri.SI
    assert ops.op_active_on_date(Hecho("x", "EN_CURSO", presente=True)) == Tri.SI
    assert ops.op_active_on_date(Hecho("x", True, presente=True)) == Tri.SI
    assert ops.op_active_on_date(Hecho("x", False, presente=True)) == Tri.NO
    assert ops.op_active_on_date(Hecho("x", presente=False)) == Tri.INDETERMINADO


def test_count_rel_y_not_exists():
    assert ops.op_count_rel_gte(1, 1) == Tri.SI
    assert ops.op_count_rel_gte(0, 1) == Tri.NO
    assert ops.op_count_rel_gte(None, 1) == Tri.INDETERMINADO
    assert ops.op_not_exists_within(False) == Tri.SI   # no hay pago -> cumple
    assert ops.op_not_exists_within(True) == Tri.NO
    assert ops.op_not_exists_within(None) == Tri.INDETERMINADO
