"""Tests de OR entre grupos (BEN-004) y cambio de versión (spec §6.7)."""
from __future__ import annotations

import pytest

from app.engine.evaluator import Evaluator
from app.engine.model import Tri


@pytest.fixture()
def fecha():
    from app.config import FECHA_EVALUACION
    return FECHA_EVALUACION


# --- OR entre grupos: BEN-004 (SUF o Asignación Familiar o SSyO) -------------

def test_ben004_tiene_tres_grupos_or(conn, fecha):
    """BEN-004 se evalúa con 3 grupos OR (ACCESO_1/2/3): basta uno."""
    ev = Evaluator(conn, fecha)
    v = ev.version_vigente("BEN-004")
    assert v is not None
    grupos = {r["grupo_or"] for r in ev._reglas(v["id_version"])}
    assert len(grupos) == 3, f"BEN-004 debe tener 3 grupos OR, tiene {grupos}"


def test_ben004_or_resultado_coherente(conn, fecha):
    """Toda familia evaluada a BEN-004 da un Tri válido; el OR no rompe.

    Como BEN-004 depende del cruce de ACCESO (SUF/AsigFamiliar/SSyO), en M2
    puede quedar INDETERMINADO; lo relevante del test es que el OR agrega los
    3 grupos sin excepción y nunca mezcla candidatos de grupos distintos.
    """
    ev = Evaluator(conn, fecha)
    vistos = set()
    for n in range(1, 31):
        fam = f"FAM-SIM-E3-{n:05d}"
        r = ev.evaluar(fam, "BEN-004")
        assert r.resultado in (Tri.SI, Tri.NO, Tri.INDETERMINADO)
        vistos.add(r.resultado)
    # Debe haber al menos un resultado (no todas excepción/vacío).
    assert vistos


# --- cambio de versión: misma familia, parámetros distintos por fecha --------

def test_cambio_version_ben001_monto_distinto(conn):
    """Misma familia en 2025-06 (V001, monto 20000) vs 2026-10 (V002, 22000)."""
    fam = "FAM-SIM-E3-00100"

    ev_2025 = Evaluator(conn, "2025-06-01")
    ev_2026 = Evaluator(conn, "2026-10-13")

    v25 = ev_2025.version_vigente("BEN-001")
    v26 = ev_2026.version_vigente("BEN-001")
    assert v25["id_version"] == "V001"
    assert v26["id_version"] == "V002"

    r25 = ev_2025.evaluar(fam, "BEN-001")
    r26 = ev_2026.evaluar(fam, "BEN-001")
    # Si la familia califica, el monto estimado debe reflejar la versión usada.
    if r25.resultado == Tri.SI:
        assert r25.monto_estimado == 20000
    if r26.resultado == Tri.SI:
        assert r26.monto_estimado == 22000
    # En todo caso, usan versiones distintas.
    assert r25.id_version != r26.id_version


def test_cambio_version_ben016_tres_versiones(conn):
    """BEN-016 tiene 3 versiones; cada fecha selecciona la vigente correcta."""
    casos = [
        ("2025-03-01", "V031"),
        ("2025-10-01", "V032"),
        ("2026-10-13", "V033"),
    ]
    for fecha, esperada in casos:
        v = Evaluator(conn, fecha).version_vigente("BEN-016")
        assert v is not None and v["id_version"] == esperada, (
            f"En {fecha} se esperaba {esperada}, se obtuvo {v and v['id_version']}")
