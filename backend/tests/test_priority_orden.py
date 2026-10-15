"""Tests del orden por grupo de acción (propuesta DEC-053).

Las oportunidades se construyen a mano (``OpportunityScore``) para fijar scores
arbitrarios: el orden por grupo debe imponerse aunque el score diga otra cosa.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.access.model import EstadoAcceso  # noqa: E402
from app.engine.model import Nivel, Tri  # noqa: E402
from app.priority.orden import (  # noqa: E402
    GrupoAccion,
    grupo_accion,
    ordenar_por_grupo_accion,
    ordenar_vista,
)
from app.priority.scoring import OpportunityScore  # noqa: E402


def _op(bid: str, estado: EstadoAcceso, score: float, u: float = 0.2, b: float = 0.0,
        position: int = 0) -> OpportunityScore:
    indeterminado = estado == EstadoAcceso.INDETERMINADO
    return OpportunityScore(
        benefit_id=bid,
        result=Tri.INDETERMINADO if indeterminado else Tri.SI,
        level=None if indeterminado else Nivel.CONFIRMADO,
        access_state=estado,
        urgency=u,
        benefit=b,
        vulnerability=0.5,
        score=score,
        position=position,
        estimated_annual_amount=None,
        benefit_estimated=False,
    )


def test_mapeo_estado_a_grupo():
    g = GrupoAccion
    assert grupo_accion(EstadoAcceso.ELEGIBLE_SIN_ASIGNACION) == g.PUEDE_POSTULAR_O_FALTA_ALGO
    assert grupo_accion(EstadoAcceso.PENDIENTE_ANTECEDENTES) == g.PUEDE_POSTULAR_O_FALTA_ALGO
    assert grupo_accion(EstadoAcceso.INDETERMINADO) == g.PUEDE_POSTULAR_O_FALTA_ALGO
    assert grupo_accion(EstadoAcceso.SIN_CUPO) == g.SIN_CUPO
    assert grupo_accion(EstadoAcceso.GESTION_EN_CURSO) == g.YA_TIENE_O_YA_POSTULO
    assert grupo_accion(EstadoAcceso.GESTION_RECHAZADA) == g.YA_TIENE_O_YA_POSTULO
    assert grupo_accion(EstadoAcceso.ASIGNADO) == g.YA_TIENE_O_YA_POSTULO
    with pytest.raises(ValueError):
        grupo_accion(EstadoAcceso.NO_APLICA)


def test_asignado_de_score_alto_va_despues_de_elegible_de_score_bajo():
    ops = [
        _op("BEN-001", EstadoAcceso.ASIGNADO, score=9.0),
        _op("BEN-002", EstadoAcceso.ELEGIBLE_SIN_ASIGNACION, score=0.1),
        _op("BEN-003", EstadoAcceso.SIN_CUPO, score=5.0),
    ]
    ordenadas = ordenar_por_grupo_accion(ops)
    assert [o.benefit_id for o in ordenadas] == ["BEN-002", "BEN-003", "BEN-001"]
    assert [o.position for o in ordenadas] == [1, 2, 3]
    # No muta la entrada ni toca U/B/V/score/estado.
    assert [o.position for o in ops] == [0, 0, 0]
    assert {(o.benefit_id, o.score, o.access_state) for o in ordenadas} == {
        (o.benefit_id, o.score, o.access_state) for o in ops
    }


def test_sin_cupo_queda_entre_ambos_grupos():
    ops = [
        _op("BEN-010", EstadoAcceso.GESTION_EN_CURSO, score=8.0),
        _op("BEN-011", EstadoAcceso.SIN_CUPO, score=0.0),
        _op("BEN-012", EstadoAcceso.INDETERMINADO, score=0.0),
        _op("BEN-013", EstadoAcceso.GESTION_RECHAZADA, score=7.0),
        _op("BEN-014", EstadoAcceso.PENDIENTE_ANTECEDENTES, score=3.0),
    ]
    ordenadas = ordenar_por_grupo_accion(ops)
    grupos = [grupo_accion(o.access_state) for o in ordenadas]
    assert grupos == sorted(grupos)
    ids = [o.benefit_id for o in ordenadas]
    assert ids.index("BEN-011") > max(ids.index("BEN-012"), ids.index("BEN-014"))
    assert ids.index("BEN-011") < min(ids.index("BEN-010"), ids.index("BEN-013"))


def test_dentro_del_grupo_se_conserva_el_desempate():
    ops = [
        _op("BEN-004", EstadoAcceso.ELEGIBLE_SIN_ASIGNACION, score=1.0, u=0.2, b=0.1),
        _op("BEN-003", EstadoAcceso.ELEGIBLE_SIN_ASIGNACION, score=1.0, u=0.2, b=0.1),
        _op("BEN-002", EstadoAcceso.PENDIENTE_ANTECEDENTES, score=1.0, u=0.2, b=0.5),
        _op("BEN-001", EstadoAcceso.INDETERMINADO, score=2.0, u=0.1, b=0.0),
    ]
    ordenadas = ordenar_por_grupo_accion(ops)
    # score desc; a igual score, B desc; a igual todo, benefit_id asc.
    assert [o.benefit_id for o in ordenadas] == ["BEN-001", "BEN-002", "BEN-003", "BEN-004"]


def test_ordenar_vista_grupo_primero_y_luego_eje():
    ops = ordenar_por_grupo_accion([
        _op("BEN-001", EstadoAcceso.ASIGNADO, score=9.0, u=0.9, b=0.9),
        _op("BEN-002", EstadoAcceso.ELEGIBLE_SIN_ASIGNACION, score=2.0, u=0.2, b=0.1),
        _op("BEN-003", EstadoAcceso.INDETERMINADO, score=1.0, u=0.2, b=0.8),
        _op("BEN-004", EstadoAcceso.SIN_CUPO, score=1.0, u=0.2, b=0.95),
    ])
    assert [o.benefit_id for o in ordenar_vista(ops, "prioridad")] == [
        "BEN-002", "BEN-003", "BEN-004", "BEN-001"]
    assert [o.benefit_id for o in ordenar_vista(ops, "beneficio")] == [
        "BEN-003", "BEN-002", "BEN-004", "BEN-001"]
    # U empatada en el grupo 1: decide position.
    assert [o.benefit_id for o in ordenar_vista(ops, "urgencia")] == [
        "BEN-002", "BEN-003", "BEN-004", "BEN-001"]
    # La vista nunca cambia position.
    assert {o.benefit_id: o.position for o in ordenar_vista(ops, "beneficio")} == {
        o.benefit_id: o.position for o in ops}
    with pytest.raises(ValueError):
        ordenar_vista(ops, "otro")
