"""Tests del estado de acceso + checklist (M3)."""
from __future__ import annotations

import pytest

from app.access.model import EstadoAcceso
from app.access.service import AccesoService


@pytest.fixture()
def svc(conn):
    from app.config import FECHA_EVALUACION
    return AccesoService(conn, FECHA_EVALUACION)


def test_suf_preliminar_sin_gestion_es_pendiente(svc):
    """Decisión [3]: SI preliminar sin gestión -> PENDIENTE_ANTECEDENTES."""
    r = svc.evaluar("FAM-SIM-E3-00100", "BEN-001")
    assert r.estado == EstadoAcceso.PENDIENTE_ANTECEDENTES
    assert r.preliminar is True
    assert r.semaforo == "amarillo"


def test_discapacidad_confirmada_sin_gestion_es_brecha(svc):
    """SI confirmado sin gestión -> ELEGIBLE_SIN_ASIGNACION (la brecha)."""
    fam = svc.conn.execute(
        """SELECT i.id_familia FROM condiciones_integrante ci
           JOIN integrantes i ON i.id_integrante = ci.id_integrante
           WHERE ci.tipo_condicion='DISCAPACIDAD' AND ci.valor_texto='SEVERA'
           AND i.id_familia NOT IN (SELECT id_familia FROM postulaciones WHERE id_beneficio='BEN-006')
           LIMIT 1"""
    ).fetchone()
    assert fam is not None
    r = svc.evaluar(fam[0], "BEN-006")
    assert r.estado == EstadoAcceso.ELEGIBLE_SIN_ASIGNACION
    assert r.semaforo == "verde"
    assert r.preliminar is False


def test_no_aplica_para_tramo_alto(svc):
    fam = svc.conn.execute(
        "SELECT id_familia FROM familias WHERE CAST(tramo_rsh_corte AS INTEGER) > 60 LIMIT 1"
    ).fetchone()
    r = svc.evaluar(fam[0], "BEN-001")
    assert r.estado == EstadoAcceso.NO_APLICA
    assert r.semaforo == "gris"


def test_indeterminado_sin_rsh(svc):
    fam = svc.conn.execute(
        "SELECT id_familia FROM familias WHERE tramo_rsh_corte IS NULL LIMIT 1"
    ).fetchone()
    r = svc.evaluar(fam[0], "BEN-001")
    assert r.estado == EstadoAcceso.INDETERMINADO


def test_asignado_cuando_gestion_vigente(svc):
    """Una familia con postulación VIGENTE a un beneficio elegible -> ASIGNADO."""
    row = svc.conn.execute(
        """SELECT p.id_familia, p.id_beneficio FROM postulaciones p
           JOIN postulaciones_estados e ON e.id_postulacion = p.id_postulacion
           WHERE e.estado='VIGENTE' AND p.id_beneficio IN ('BEN-005','BEN-010','BEN-015')
           LIMIT 1"""
    ).fetchone()
    assert row is not None
    r = svc.evaluar(row[0], row[1])
    assert r.estado == EstadoAcceso.ASIGNADO
    assert r.semaforo == "azul"
    assert r.tiene_gestion is True


def test_checklist_tiene_canal_y_documentos(svc):
    r = svc.evaluar("FAM-SIM-E3-00100", "BEN-001")
    assert r.checklist is not None
    assert r.checklist.canal  # dónde ir
    assert r.checklist.modalidad_acceso == "POSTULACION"
    assert r.checklist.fuente_url and r.checklist.fuente_url.startswith("http")
    # Al menos el documento del RSH
    campos = {d.campo for d in r.checklist.documentos}
    assert "tramo_rsh" in campos
