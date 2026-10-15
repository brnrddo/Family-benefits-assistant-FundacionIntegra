"""Tests del perfil consolidado de familia."""
from __future__ import annotations

import pytest

from app.profile.builder import ProfileBuilder


@pytest.fixture()
def builder(conn):
    from app.config import FECHA_EVALUACION
    return ProfileBuilder(conn, FECHA_EVALUACION)


def test_perfil_tiene_las_seis_secciones(builder):
    p = builder.build("FAM-SIM-E3-00100")
    assert p is not None
    for sec in ("identidad", "rsh", "composicion", "antecedentes",
                "historial", "contexto_recomendacion"):
        assert sec in p, f"Falta la sección {sec}"


def test_identidad_tiene_comuna_region_zona(builder):
    ident = builder.build("FAM-SIM-E3-00100")["identidad"]
    assert ident["id_familia"] == "FAM-SIM-E3-00100"
    assert ident["comuna"] and ident["region"]
    assert ident["id_jardin"] and ident["tipo_zona"] in ("URBANA", "RURAL")


def test_rsh_conocido_flag(builder):
    rsh = builder.build("FAM-SIM-E3-00100")["rsh"]
    assert rsh["rsh_conocido"] is True
    assert isinstance(rsh["tramo_rsh"], int)


def test_composicion_identifica_nino_jardin_y_referencia(builder):
    comp = builder.build("FAM-SIM-E3-00100")["composicion"]
    assert comp["integrantes"]
    assert comp["persona_referencia"] is not None
    assert comp["persona_referencia"]["parentesco"] == "PERSONA_REFERENCIA"
    # Debe haber al menos un niño de jardín con nivel/matrícula
    assert comp["ninos_jardin"]
    assert "nivel" in comp["ninos_jardin"][0]


def test_contexto_recomendacion_clasifica_en_cuatro_grupos(builder):
    ctx = builder.build("FAM-SIM-E3-00100")["contexto_recomendacion"]
    for k in ("beneficios_elegibles_determinables", "beneficios_candidatos",
              "beneficios_no_evaluables", "datos_faltantes"):
        assert k in ctx
    # SUF debe estar entre los elegibles determinables
    bens_elegibles = {b["beneficio"] for b in ctx["beneficios_elegibles_determinables"]}
    assert "BEN-001" in bens_elegibles


def test_familia_inexistente_devuelve_none(builder):
    assert builder.build("FAM-SIM-E3-99999") is None
