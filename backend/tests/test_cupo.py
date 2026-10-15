"""Test del cupo contingente de BEN-018 (spec §7).

BEN-018 (Canasta Familiar) tiene cupo 75 en la versión vigente. Los elegibles
se ordenan por inseguridad alimentaria desc, ingreso per cápita asc, id; los
primeros 75 quedan dentro, el resto SIN_CUPO.
"""
from __future__ import annotations

import pytest

from app.access.service import AccesoService, CUPO_BEN018_DEFAULT
from app.access.model import EstadoAcceso


@pytest.fixture()
def svc(conn):
    from app.config import FECHA_EVALUACION
    return AccesoService(conn, FECHA_EVALUACION)


def test_cupo_lee_version_vigente(svc):
    assert svc._cupo_ben018() == 75  # V037


def test_dentro_de_cupo_son_exactamente_el_cupo(svc):
    dentro = svc._familias_dentro_cupo()
    cupo = svc._cupo_ben018()
    assert len(dentro) == cupo


def test_existe_al_menos_un_sin_cupo(svc):
    """Debe haber elegibles sobre el cupo marcados SIN_CUPO."""
    fams = [r[0] for r in svc.conn.execute(
        "SELECT id_familia FROM familias ORDER BY id_familia").fetchall()]
    estados = [svc.evaluar(f, "BEN-018").estado for f in fams]
    assert EstadoAcceso.SIN_CUPO in estados


def test_familia_dentro_de_cupo_no_es_sin_cupo(svc):
    """Una familia dentro del cupo, sin gestión, no debe ser SIN_CUPO."""
    dentro = svc._familias_dentro_cupo()
    assert dentro
    fam = sorted(dentro)[0]
    r = svc.evaluar(fam, "BEN-018")
    assert r.estado != EstadoAcceso.SIN_CUPO


def test_default_cupo_constante():
    assert CUPO_BEN018_DEFAULT == 75
